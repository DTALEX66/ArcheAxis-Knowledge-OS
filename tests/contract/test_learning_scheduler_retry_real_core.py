"""Synthetic retry checks against the real Core and local FSRS worker."""

import hashlib
import importlib.util
import json
import os
import sqlite3
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
pytestmark = pytest.mark.skipif(not os.environ.get("AAOS_TEST_CORE_EXE"), reason="explicit real Core required")


def request(item, event):
    return {"item_key": item, "client_event_id": event, "correct": True,
            "now": "2026-09-02T00:00:00+00:00"}


def legacy_request():
    return {**request("synthetic-legacy-retry", "legacy-key"), "schedule_state": {
        "state": "review", "stability": 42.0, "difficulty": 5.0,
        "due": "2026-09-01T00:00:00+00:00", "last_review": "2026-08-03T00:00:00+00:00", "step": 0}}


def core_for(tmp_path):
    from scripts.ci.real_core_grading_journey import Core
    return Core(Path(os.environ["AAOS_TEST_CORE_EXE"]).resolve(strict=True), tmp_path, Path(sys.executable))


@pytest.mark.parametrize("first_available", [True, False])
def test_legacy_retry_preserves_receipt_across_scheduler_availability(tmp_path, monkeypatch, first_available):
    core = core_for(tmp_path)
    good_python = str(Path(sys.executable).resolve())
    missing_python = str(tmp_path / "missing-scheduler-python")
    body = legacy_request()
    stateful = {**request("synthetic-stateful-outage", "stateful-outage-key"), "rating": 3}
    try:
        monkeypatch.setenv("ARCHEAXIS_PYTHON", good_python if first_available else missing_python)
        core.start()
        status, first = core.request("POST", "/api/v1/learning/events", body)
        assert status == 201, first
        assert first["schedule_authority"] == ("fsrs" if first_available else "unavailable")
        status, state_first = core.request("POST", "/api/v1/learning/reviews", stateful)
        assert status == 201 and state_first["schedule_authority"] == first["schedule_authority"]
        core.stop()
        monkeypatch.setenv("ARCHEAXIS_PYTHON", missing_python if first_available else good_python)
        core.start()
        status, replay = core.request("POST", "/api/v1/learning/events", body)
        assert status == 200, replay
        assert replay["duplicate"] is True and replay["event_id"] == first["event_id"]
        assert replay["schedule_authority"] == first["schedule_authority"]
        assert replay["next_review_days"] == first["next_review_days"]
        assert replay["idempotency_scope"] == "full_request"
        status, state_replay = core.request("POST", "/api/v1/learning/reviews", stateful)
        assert status == 200 and state_replay["duplicate"] is True
        for field in ("event_id", "schedule_authority", "next_review", "next_review_days", "schedule_state"):
            assert state_replay[field] == state_first[field]
        status, history = core.request("GET", "/api/v1/learning/events/synthetic-legacy-retry")
        assert status == 200 and history["count"] == 1
        status, backup = core.request("POST", "/api/v1/workspace/backups", {})
        assert status == 201 and backup["verified"] is True
        assert Path(backup["filename"]).name == backup["filename"]
        artifact = tmp_path / "backups" / backup["filename"]
        assert hashlib.sha256(artifact.read_bytes()).hexdigest() == backup["sha256"]
        exe = core.exe
        core.stop()
        destination = tmp_path / "independent-restore"
        destination.mkdir()
        result = subprocess.run([str(exe), "--maintenance-restore", str(destination / "workspace.sqlite"),
            str(artifact)], capture_output=True, text=True, timeout=120, check=False)
        restored = json.loads(result.stdout) if result.stdout else {}
        assert result.returncode == 0 and restored.get("ok") is True
        assert restored.get("authorization_requires_new_grants") is True
        from scripts.ci.real_core_grading_journey import Core
        core = Core(exe, destination, Path(sys.executable))
        core.start()
        status, after_restore = core.request("POST", "/api/v1/learning/events", body)
        assert status == 200 and after_restore == replay
        status, state_after_restore = core.request("POST", "/api/v1/learning/reviews", stateful)
        assert status == 200 and state_after_restore == state_replay
        assert core.request("GET", "/api/v1/learning/events/synthetic-legacy-retry")[1] == history
        assert core.request("POST", "/api/v1/learning/events", {**body, "now": "2026-09-03T00:00:00+00:00"})[0] == 409
    finally:
        core.stop()


def test_new_legacy_event_key_rejects_changed_scheduling_request(tmp_path, monkeypatch):
    core = core_for(tmp_path)
    monkeypatch.setenv("ARCHEAXIS_PYTHON", str(Path(sys.executable).resolve()))
    body = legacy_request()
    try:
        core.start()
        status, first = core.request("POST", "/api/v1/learning/events", body)
        assert status == 201 and first["schedule_authority"] == "fsrs"
        status, changed = core.request("POST", "/api/v1/learning/events", {**body, "now": "2026-09-03T00:00:00+00:00"})
        assert status == 409, changed
        changed_state = {**body, "schedule_state": {**body["schedule_state"], "stability": 43.0}}
        assert core.request("POST", "/api/v1/learning/events", changed_state)[0] == 409
    finally:
        core.stop()


def test_negative_worker_interval_is_unavailable_and_replayable(tmp_path, monkeypatch):
    core = core_for(tmp_path)
    worker = tmp_path / "bad_interval_worker.py"
    worker.write_text(
        "import json\n"
        "print(json.dumps({'authority':'fsrs','next_review_days':-2,'due':'2026-09-03T00:00:00Z',"
        "'state':'review','step':None,'stability':1.0,'difficulty':5.0,'last_review':'2026-09-02T00:00:00Z'}))\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("ARCHEAXIS_PYTHON", str(Path(sys.executable).resolve()))
    monkeypatch.setenv("ARCHEAXIS_SCHEDULER_WORKER", str(worker))
    body = legacy_request()
    try:
        core.start()
        status, first = core.request("POST", "/api/v1/learning/events", body)
        assert status == 201 and first["schedule_authority"] == "unavailable", first
        assert first["next_review_days"] == -2
        status, replay = core.request("POST", "/api/v1/learning/events", body)
        assert status == 200 and replay["duplicate"] is True
        assert replay["schedule_authority"] == "unavailable" and replay["next_review_days"] == -2
    finally:
        core.stop()


@pytest.mark.parametrize("legacy", [False, True])
def test_simultaneous_identical_requests_commit_only_one_event(tmp_path, monkeypatch, legacy):
    core = core_for(tmp_path)
    # Force enough Core runtime threads for both workers to reach the barrier.
    monkeypatch.setenv("TOKIO_WORKER_THREADS", "4")
    marker = tmp_path / "concurrent-scheduler-calls"
    marker.mkdir()
    worker = tmp_path / "synchronized_scheduler.py"
    worker.write_text(
        "import os, runpy, time, uuid\n"
        "marker=os.environ['AAOS_TEST_SCHEDULER_MARKER']\n"
        "with open(os.path.join(marker, str(os.getpid())+'-'+uuid.uuid4().hex+'.call'), 'x', encoding='utf-8') as out: out.write('call')\n"
        "deadline=time.monotonic()+8\n"
        "while time.monotonic()<deadline:\n"
        "    count=len([name for name in os.listdir(marker) if name.endswith('.call')])\n"
        "    if count>=2: break\n"
        "    time.sleep(0.02)\n"
        "runpy.run_path(os.environ['AAOS_TEST_SCHEDULER_TARGET'], run_name='__main__')\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("ARCHEAXIS_PYTHON", str(Path(sys.executable).resolve()))
    monkeypatch.setenv("ARCHEAXIS_SCHEDULER_WORKER", str(worker))
    monkeypatch.setenv("AAOS_TEST_SCHEDULER_MARKER", str(marker))
    monkeypatch.setenv("AAOS_TEST_SCHEDULER_TARGET", str(ROOT / "services/python-workers/learning/worker_schedule.py"))
    body = legacy_request() if legacy else {**request("synthetic-concurrent", "concurrent-key"), "rating": 3}
    path = "/api/v1/learning/events" if legacy else "/api/v1/learning/reviews"
    gate = threading.Barrier(2)

    def submit():
        gate.wait(timeout=10)
        return core.request("POST", path, body)

    try:
        core.start()
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(submit) for _ in range(2)]
            results = [future.result(timeout=30) for future in futures]
        assert sorted(status for status, _ in results) == [200, 201], results
        assert results[0][1]["event_id"] == results[1][1]["event_id"]
        assert sorted(result["duplicate"] for _, result in results) == [False, True]
        assert len(list(marker.glob("*.call"))) == 2
        status, history = core.request("GET", f"/api/v1/learning/events/{body['item_key']}")
        assert status == 200 and history["count"] == 1
    finally:
        core.stop()


def test_stateful_replay_does_not_rerun_scheduler(tmp_path, monkeypatch):
    core = core_for(tmp_path)
    worker = tmp_path / "counting_scheduler.py"
    marker = tmp_path / "scheduler-calls.txt"
    worker.write_text(
        "import os, runpy\n"
        "with open(os.environ['AAOS_TEST_SCHEDULER_MARKER'], 'a', encoding='utf-8') as out: out.write('call\\n')\n"
        "runpy.run_path(os.environ['AAOS_TEST_SCHEDULER_TARGET'], run_name='__main__')\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("ARCHEAXIS_PYTHON", str(Path(sys.executable).resolve()))
    monkeypatch.setenv("ARCHEAXIS_SCHEDULER_WORKER", str(worker))
    monkeypatch.setenv("AAOS_TEST_SCHEDULER_MARKER", str(marker))
    monkeypatch.setenv("AAOS_TEST_SCHEDULER_TARGET", str(ROOT / "services/python-workers/learning/worker_schedule.py"))
    body = {**request("synthetic-stateful-retry", "stateful-key"), "rating": 3}
    try:
        core.start()
        status, first = core.request("POST", "/api/v1/learning/reviews", body)
        assert status == 201 and first["schedule_authority"] == "fsrs"
        assert marker.read_text(encoding="utf-8").splitlines() == ["call"]
        status, replay = core.request("POST", "/api/v1/learning/reviews", body)
        assert status == 200 and replay["duplicate"] is True and replay["event_id"] == first["event_id"]
        assert marker.read_text(encoding="utf-8").splitlines() == ["call"]
        assert core.request("POST", "/api/v1/learning/reviews", {**body, "now": "2026-09-03T00:00:00+00:00"})[0] == 409
        assert marker.read_text(encoding="utf-8").splitlines() == ["call"]
        legacy = legacy_request()
        status, legacy_first = core.request("POST", "/api/v1/learning/events", legacy)
        assert status == 201 and legacy_first["schedule_authority"] == "fsrs"
        assert marker.read_text(encoding="utf-8").splitlines() == ["call", "call"]
        status, legacy_replay = core.request("POST", "/api/v1/learning/events", legacy)
        assert status == 200 and legacy_replay["duplicate"] is True
        assert core.request("POST", "/api/v1/learning/events", {**legacy, "now": "2026-09-03T00:00:00+00:00"})[0] == 409
        assert marker.read_text(encoding="utf-8").splitlines() == ["call", "call"]
        status, knowledge = core.request("POST", "/api/v1/knowledge-items", {"knowledge_type": "FACTUAL_CLAIM",
            "body": "Synthetic assessment", "status": "accepted", "created_by": "fixture"})
        assert status == 201
        base = "/api/v1/learning/items/synthetic-guarded"
        assert core.request("POST", base + "/references", {"knowledge_id": knowledge["knowledge_id"]})[0] == 201
        assert core.request("POST", base + "/assessment", {"knowledge_id": knowledge["knowledge_id"]})[0] == 201
        assert core.request("POST", "/api/v1/learning/reviews", {**body, "item_key": "synthetic-guarded",
            "client_event_id": "unbound-stateful"})[0] == 409
        assert core.request("POST", "/api/v1/learning/events", {**legacy, "item_key": "synthetic-guarded",
            "client_event_id": "unbound-legacy"})[0] == 409
        assert marker.read_text(encoding="utf-8").splitlines() == ["call", "call"]
        if output := os.environ.get("AAOS_TEST_RETRY_OUTPUT"):
            with Path(output).open("x", encoding="utf-8") as stream:
                json.dump({"synthetic": True, "core_sha256": hashlib.sha256(core.exe.read_bytes()).hexdigest(),
                    "stateful_replay_scheduler_calls": 0, "legacy_replay_scheduler_calls": 0,
                    "changed_request_scheduler_calls": 0, "unbound_refusal_scheduler_calls": 0,
                    "first_requests_scheduler_calls": 2}, stream)
    finally:
        core.stop()


def test_invalid_stateful_review_does_not_start_scheduler(tmp_path, monkeypatch):
    core = core_for(tmp_path)
    worker = tmp_path / "counting_scheduler.py"
    marker = tmp_path / "scheduler-calls.txt"
    worker.write_text(
        "import os, runpy\n"
        "with open(os.environ['AAOS_TEST_SCHEDULER_MARKER'], 'a', encoding='utf-8') as out: out.write('call\\n')\n"
        "runpy.run_path(os.environ['AAOS_TEST_SCHEDULER_TARGET'], run_name='__main__')\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("ARCHEAXIS_PYTHON", str(Path(sys.executable).resolve()))
    monkeypatch.setenv("ARCHEAXIS_SCHEDULER_WORKER", str(worker))
    monkeypatch.setenv("AAOS_TEST_SCHEDULER_MARKER", str(marker))
    monkeypatch.setenv("AAOS_TEST_SCHEDULER_TARGET", str(ROOT / "services/python-workers/learning/worker_schedule.py"))
    try:
        core.start()
        status, knowledge = core.request("POST", "/api/v1/knowledge-items", {"knowledge_type": "FACTUAL_CLAIM",
            "body": "Synthetic assessment", "status": "accepted", "created_by": "fixture"})
        assert status == 201
        item = "synthetic-invalid-review"
        base = f"/api/v1/learning/items/{item}"
        assert core.request("POST", base + "/references", {"knowledge_id": knowledge["knowledge_id"]})[0] == 201
        status, assessment = core.request("POST", base + "/assessment", {"knowledge_id": knowledge["knowledge_id"]})
        assert status == 201
        body = {**request(item, "invalid-time-key"), "rating": 3,
                "assessment_id": assessment["assessment_id"], "knowledge_version": assessment["knowledge_version"]}
        cases = [
            {**body, "now": "not-a-timestamp"},
            {**body, "client_event_id": "invalid-assessment-key", "assessment_id": "missing-assessment"},
            {**body, "client_event_id": "invalid-version-key", "knowledge_version": "wrong-version"},
        ]
        assert [core.request("POST", "/api/v1/learning/reviews", case)[0] for case in cases] == [400, 400, 400]
        assert not marker.exists() or not marker.read_text(encoding="utf-8").splitlines()
        assert core.request("GET", f"/api/v1/learning/events/{item}")[1]["count"] == 0
        status, first = core.request("POST", "/api/v1/learning/reviews", body)
        assert status == 201 and first["schedule_authority"] == "fsrs"
        assert marker.read_text(encoding="utf-8").splitlines() == ["call"]
        status, replay = core.request("POST", "/api/v1/learning/reviews", body)
        assert status == 200 and replay["event_id"] == first["event_id"] and replay["duplicate"] is True
        assert marker.read_text(encoding="utf-8").splitlines() == ["call"]
    finally:
        core.stop()


def test_recovered_scheduler_accounts_for_unscheduled_review(tmp_path, monkeypatch):
    """A retained outage review must not silently disappear from the next FSRS card."""
    core = core_for(tmp_path)
    good_python = str(Path(sys.executable).resolve())
    missing_python = str(tmp_path / "missing-scheduler-python")
    item = "synthetic-outage-history"
    first_body = {**request(item, "before-outage"), "rating": 3, "now": "2026-09-01T00:00:00+00:00"}
    missed_body = {**request(item, "during-outage"), "correct": False, "rating": 1,
                   "now": "2026-09-03T00:00:00+00:00"}
    last_body = {**request(item, "after-outage"), "rating": 3, "now": "2026-09-04T00:00:00+00:00"}
    spec = importlib.util.spec_from_file_location("test_outage_fsrs", ROOT / "services/python-workers/learning/worker_schedule.py")
    worker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(worker)
    card_fields = ("state", "step", "stability", "difficulty", "due", "last_review")
    try:
        monkeypatch.setenv("ARCHEAXIS_PYTHON", good_python)
        core.start()
        status, first = core.request("POST", "/api/v1/learning/reviews", first_body)
        assert status == 201 and first["schedule_authority"] == "fsrs"
        core.stop()
        monkeypatch.setenv("ARCHEAXIS_PYTHON", missing_python)
        core.start()
        status, missed = core.request("POST", "/api/v1/learning/reviews", missed_body)
        assert status == 201 and missed["schedule_authority"] == "unavailable"
        assert missed["next_review"] is None
        second_missed = {**request(item, "during-outage-2"), "rating": 2, "now": "2026-09-03T12:00:00+00:00"}
        status, another = core.request("POST", "/api/v1/learning/reviews", second_missed)
        assert status == 201 and another["schedule_authority"] == "unavailable"
        core.stop()
        monkeypatch.setenv("ARCHEAXIS_PYTHON", good_python)
        core.start()
        status, last = core.request("POST", "/api/v1/learning/reviews", last_body)
        assert status == 201 and last["schedule_authority"] == "fsrs"
        assert last["schedule_recovery"] == {"state": "replayed", "count": 2,
                                             "through_event_id": another["event_id"]}
        applied = worker.schedule({"item_key": item, "state": first["schedule_state"],
                                   "rating": missed_body["rating"], "now": missed_body["now"]})
        applied = worker.schedule({"item_key": item, "state": {key: applied[key] for key in card_fields},
                                   "rating": second_missed["rating"], "now": second_missed["now"]})
        expected = worker.schedule({"item_key": item, "state": {key: applied[key] for key in card_fields},
                                    "rating": last_body["rating"], "now": last_body["now"]})
        assert last["schedule_state"] == {key: expected[key] for key in card_fields}
        history = core.request("GET", f"/api/v1/learning/events/{item}")[1]
        assert history["count"] == 4
        assert json.loads(history["events"][1]["outcome"])["schedule"]["authority"] == "unavailable"
        assert core.request("POST", "/api/v1/learning/reviews", missed_body)[1]["event_id"] == missed["event_id"]
        status, backup = core.request("POST", "/api/v1/workspace/backups", {})
        assert status == 201 and backup["verified"] is True
        artifact = tmp_path / "backups" / backup["filename"]
        assert hashlib.sha256(artifact.read_bytes()).hexdigest() == backup["sha256"]
        exe = core.exe
        core.stop()
        destination = tmp_path / "recovered-restore"
        destination.mkdir()
        result = subprocess.run([str(exe), "--maintenance-restore", str(destination / "workspace.sqlite"),
                                 str(artifact)], capture_output=True, text=True, timeout=120, check=False)
        assert result.returncode == 0 and json.loads(result.stdout)["ok"] is True
        from scripts.ci.real_core_grading_journey import Core
        core = Core(exe, destination, Path(sys.executable))
        core.start()
        assert core.request("GET", f"/api/v1/learning/events/{item}")[1] == history
        status, replay = core.request("POST", "/api/v1/learning/reviews", last_body)
        assert status == 200 and replay["duplicate"] is True and replay["schedule_state"] == last["schedule_state"]
        assert replay["schedule_recovery"] == last["schedule_recovery"]
    finally:
        core.stop()


def test_recovery_uses_effective_time_when_client_omits_now(tmp_path, monkeypatch):
    core = core_for(tmp_path)
    good_python = str(Path(sys.executable).resolve())
    item = "synthetic-no-client-time"
    missed = {"item_key": item, "client_event_id": "outage-no-time", "correct": False, "rating": 1}
    current = {"item_key": item, "client_event_id": "after-no-time", "correct": True, "rating": 3}
    try:
        monkeypatch.setenv("ARCHEAXIS_PYTHON", str(tmp_path / "missing-python"))
        core.start()
        status, first = core.request("POST", "/api/v1/learning/reviews", missed)
        assert status == 201 and first["schedule_authority"] == "unavailable"
        stored = json.loads(core.request("GET", f"/api/v1/learning/events/{item}")[1]["events"][0]["outcome"])
        assert stored["review_evidence"]["now"] is None and stored["schedule"]["reviewed_at"]
        core.stop()
        monkeypatch.setenv("ARCHEAXIS_PYTHON", good_python)
        core.start()
        status, recovered = core.request("POST", "/api/v1/learning/reviews", current)
        assert status == 201 and recovered["schedule_authority"] == "fsrs"
        assert recovered["schedule_recovery"]["state"] == "replayed"
        assert recovered["schedule_recovery"]["count"] == 1
    finally:
        core.stop()


def test_recovery_accepts_offset_time_without_changing_recorded_input(tmp_path, monkeypatch):
    core = core_for(tmp_path)
    item = "synthetic-offset-outage"
    old_time = "2026-09-02T08:00:00+08:00"
    try:
        monkeypatch.setenv("ARCHEAXIS_PYTHON", str(tmp_path / "missing-python"))
        core.start()
        status, old = core.request("POST", "/api/v1/learning/reviews", {
            "item_key": item, "client_event_id": "offset-outage", "correct": False, "rating": 1, "now": old_time})
        assert status == 201 and old["schedule_authority"] == "unavailable"
        core.stop()
        monkeypatch.setenv("ARCHEAXIS_PYTHON", str(Path(sys.executable).resolve()))
        core.start()
        status, recovered = core.request("POST", "/api/v1/learning/reviews", {
            "item_key": item, "client_event_id": "offset-after", "correct": True, "rating": 3,
            "now": "2026-09-03T08:00:00+08:00"})
        assert status == 201 and recovered["schedule_authority"] == "fsrs"
        assert recovered["schedule_recovery"]["count"] == 1
        assert recovered["schedule_state"]["last_review"] == "2026-09-03T00:00:00+00:00"
        history = core.request("GET", f"/api/v1/learning/events/{item}")[1]
        original = json.loads(history["events"][0]["outcome"])
        assert original["review_evidence"]["now"] == old_time
        assert original["schedule"]["reviewed_at"] == old_time
    finally:
        core.stop()


def test_old_unscheduled_review_without_time_is_not_guessed(tmp_path, monkeypatch):
    core = core_for(tmp_path)
    item = "synthetic-old-missing-time"
    body = {"item_key": item, "client_event_id": "old-no-time", "correct": False, "rating": 1}
    worker = tmp_path / "unexpected_scheduler.py"
    marker = tmp_path / "unexpected-call.txt"
    worker.write_text("import os\nopen(os.environ['AAOS_TEST_SCHEDULER_MARKER'],'w').write('called')\n",
                      encoding="utf-8")
    try:
        monkeypatch.setenv("ARCHEAXIS_PYTHON", str(tmp_path / "missing-python"))
        core.start()
        status, old = core.request("POST", "/api/v1/learning/reviews", body)
        assert status == 201 and old["schedule_authority"] == "unavailable"
        core.stop()
        # Simulate an older Core's synthetic event, which did not save the effective time.
        with sqlite3.connect(tmp_path / "workspace.sqlite") as conn:
            conn.execute("UPDATE learning_events SET outcome=json_remove(outcome,'$.schedule.reviewed_at') WHERE event_id=?",
                         (old["event_id"],))
        monkeypatch.setenv("ARCHEAXIS_PYTHON", str(Path(sys.executable).resolve()))
        monkeypatch.setenv("ARCHEAXIS_SCHEDULER_WORKER", str(worker))
        monkeypatch.setenv("AAOS_TEST_SCHEDULER_MARKER", str(marker))
        core.start()
        status, later = core.request("POST", "/api/v1/learning/reviews", {
            "item_key": item, "client_event_id": "after-old", "correct": True, "rating": 3})
        assert status == 201 and later["schedule_authority"] == "unavailable" and later["next_review"] is None
        assert later["schedule_recovery"]["reason"] == "unscheduled_review_evidence_missing_or_invalid"
        assert not marker.exists()
        assert core.request("GET", f"/api/v1/learning/events/{item}")[1]["count"] == 2
    finally:
        core.stop()


@pytest.mark.parametrize("wrong_time", [False, True])
def test_invalid_recovery_card_remains_unscheduled_and_can_recover_later(tmp_path, monkeypatch, wrong_time):
    core = core_for(tmp_path)
    worker = tmp_path / "invalid_recovery_scheduler.py"
    worker.write_text(
        "import json\n"
        "print(json.dumps({'authority':'fsrs','next_review_days':1,'due':'2026-09-03T00:00:00Z',"
        "'state':'review','step':None,'stability':" + ("3.0" if wrong_time else "None") +
        ",'difficulty':5.0,'last_review':'2026-09-02T00:00:00Z'}))\n",
        encoding="utf-8",
    )
    item = "synthetic-invalid-recovery"
    try:
        monkeypatch.setenv("ARCHEAXIS_PYTHON", str(tmp_path / "missing-python"))
        core.start()
        status, first = core.request("POST", "/api/v1/learning/reviews", {
            "item_key": item, "client_event_id": "outage", "correct": False, "rating": 1,
            "now": "2026-09-01T00:00:00Z"})
        assert status == 201 and first["schedule_authority"] == "unavailable"
        core.stop()
        monkeypatch.setenv("ARCHEAXIS_PYTHON", str(Path(sys.executable).resolve()))
        monkeypatch.setenv("ARCHEAXIS_SCHEDULER_WORKER", str(worker))
        core.start()
        status, second = core.request("POST", "/api/v1/learning/reviews", {
            "item_key": item, "client_event_id": "bad-recovery", "correct": True, "rating": 3,
            "now": "2026-09-02T00:00:00Z"})
        assert status == 201 and second["schedule_authority"] == "unavailable" and second["next_review"] is None
        assert second["schedule_recovery"]["reason"] == ("scheduler_time_mismatch" if wrong_time else "invalid_recovered_card")
        core.stop()
        monkeypatch.delenv("ARCHEAXIS_SCHEDULER_WORKER")
        core.start()
        status, recovered = core.request("POST", "/api/v1/learning/reviews", {
            "item_key": item, "client_event_id": "after-repair", "correct": True, "rating": 3,
            "now": "2026-09-03T00:00:00Z"})
        assert status == 201 and recovered["schedule_authority"] == "fsrs"
        assert recovered["schedule_recovery"]["count"] == 2
        assert core.request("GET", f"/api/v1/learning/events/{item}")[1]["count"] == 3
    finally:
        core.stop()


def test_concurrent_unscheduled_review_invalidates_successful_snapshot(tmp_path, monkeypatch):
    core = core_for(tmp_path)
    monkeypatch.setenv("TOKIO_WORKER_THREADS", "4")
    marker = tmp_path / "recovery-race-calls"
    marker.mkdir()
    worker = tmp_path / "recovery_race_scheduler.py"
    worker.write_text(
        "import io,json,os,runpy,sys,time,uuid\n"
        "raw=sys.stdin.read(); rating=json.loads(raw)['rating']\n"
        "marker=os.environ['AAOS_TEST_SCHEDULER_MARKER']\n"
        "with open(os.path.join(marker,str(os.getpid())+'-'+uuid.uuid4().hex+'.call'),'x',encoding='utf-8') as out: out.write('call')\n"
        "count=len([name for name in os.listdir(marker) if name.endswith('.call')])\n"
        "if count<=2:\n"
        "    deadline=time.monotonic()+8\n"
        "    while time.monotonic()<deadline:\n"
        "        total=len([name for name in os.listdir(marker) if name.endswith('.call')])\n"
        "        if total>=2: break\n"
        "        time.sleep(.02)\n"
        "    if rating==1:\n"
        "        print(json.dumps({'error':'synthetic outage','authority':'fsrs'})); sys.exit(1)\n"
        "    time.sleep(.8)\n"
        "sys.stdin=io.StringIO(raw)\n"
        "runpy.run_path(os.environ['AAOS_TEST_SCHEDULER_TARGET'],run_name='__main__')\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("ARCHEAXIS_PYTHON", str(Path(sys.executable).resolve()))
    monkeypatch.setenv("ARCHEAXIS_SCHEDULER_WORKER", str(worker))
    monkeypatch.setenv("AAOS_TEST_SCHEDULER_MARKER", str(marker))
    monkeypatch.setenv("AAOS_TEST_SCHEDULER_TARGET", str(ROOT / "services/python-workers/learning/worker_schedule.py"))
    item = "synthetic-outage-race"
    outage = {**request(item, "race-outage"), "correct": False, "rating": 1}
    success = {**request(item, "race-success"), "rating": 3}
    gate = threading.Barrier(2)

    def submit(body):
        gate.wait(timeout=10)
        return core.request("POST", "/api/v1/learning/reviews", body)

    try:
        core.start()
        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(submit, outage)
            second = pool.submit(submit, success)
            outage_result, success_result = first.result(timeout=30), second.result(timeout=30)
        assert outage_result[0] == 201 and outage_result[1]["schedule_authority"] == "unavailable"
        assert success_result[0] == 409
        assert core.request("GET", f"/api/v1/learning/events/{item}")[1]["count"] == 1
        status, retried = core.request("POST", "/api/v1/learning/reviews", success)
        assert status == 201 and retried["schedule_authority"] == "fsrs"
        assert retried["schedule_recovery"]["count"] == 1
        assert len(list(marker.glob("*.call"))) == 4
        assert core.request("GET", f"/api/v1/learning/events/{item}")[1]["count"] == 2
    finally:
        core.stop()


@pytest.mark.parametrize("legacy_worker", [False, True])
def test_multiple_outage_reviews_are_batched_or_safely_replayed_by_old_worker(tmp_path, monkeypatch, legacy_worker):
    core = core_for(tmp_path)
    marker = tmp_path / "batch-calls.txt"
    worker = tmp_path / "counted_scheduler.py"
    worker.write_text(
        "import io,json,os,runpy,sys\n"
        "raw=json.loads(sys.stdin.read())\n"
        "with open(os.environ['AAOS_TEST_SCHEDULER_MARKER'],'a',encoding='utf-8') as out: out.write('call\\n')\n"
        "if os.environ.get('AAOS_TEST_OLD_SCHEDULER')=='1': raw.pop('replay',None)\n"
        "sys.stdin=io.StringIO(json.dumps(raw))\n"
        "runpy.run_path(os.environ['AAOS_TEST_SCHEDULER_TARGET'],run_name='__main__')\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("ARCHEAXIS_PYTHON", str(tmp_path / "missing-python"))
    item = "synthetic-batch-recovery"
    try:
        core.start()
        for day, rating in [(1, 1), (2, 3), (3, 2)]:
            status, value = core.request("POST", "/api/v1/learning/reviews", {
                "item_key": item, "client_event_id": f"missed-{day}", "correct": rating != 1,
                "rating": rating, "now": f"2026-09-{day:02}T00:00:00+00:00"})
            assert status == 201 and value["schedule_authority"] == "unavailable"
        core.stop()
        monkeypatch.setenv("ARCHEAXIS_PYTHON", str(Path(sys.executable).resolve()))
        monkeypatch.setenv("ARCHEAXIS_SCHEDULER_WORKER", str(worker))
        monkeypatch.setenv("AAOS_TEST_SCHEDULER_MARKER", str(marker))
        monkeypatch.setenv("AAOS_TEST_SCHEDULER_TARGET", str(ROOT / "services/python-workers/learning/worker_schedule.py"))
        monkeypatch.setenv("AAOS_TEST_OLD_SCHEDULER", "1" if legacy_worker else "0")
        core.start()
        status, recovered = core.request("POST", "/api/v1/learning/reviews", {
            "item_key": item, "client_event_id": "after-outages", "correct": True,
            "rating": 3, "now": "2026-09-04T00:00:00+00:00"})
        assert status == 201 and recovered["schedule_authority"] == "fsrs"
        assert recovered["schedule_recovery"]["count"] == 3
        # The old worker's unproved batch result is discarded before three individual replays.
        assert len(marker.read_text(encoding="utf-8").splitlines()) == (5 if legacy_worker else 2)
        spec = importlib.util.spec_from_file_location("test_batch_fsrs", ROOT / "services/python-workers/learning/worker_schedule.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        fields = ("state", "step", "stability", "difficulty", "due", "last_review")
        card = {}
        for day, rating in [(1, 1), (2, 3), (3, 2), (4, 3)]:
            result = module.schedule({"item_key": item, "state": card, "rating": rating,
                                      "now": f"2026-09-{day:02}T00:00:00+00:00"})
            card = {key: result[key] for key in fields}
        assert recovered["schedule_state"] == card
    finally:
        core.stop()


def test_more_than_64_outage_reviews_recover_in_bounded_batches(tmp_path, monkeypatch):
    core = core_for(tmp_path)
    marker = tmp_path / "many-batch-calls.txt"
    worker = tmp_path / "many_batch_scheduler.py"
    worker.write_text(
        "import os,runpy\n"
        "with open(os.environ['AAOS_TEST_SCHEDULER_MARKER'],'a',encoding='utf-8') as out: out.write('call\\n')\n"
        "runpy.run_path(os.environ['AAOS_TEST_SCHEDULER_TARGET'],run_name='__main__')\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("ARCHEAXIS_PYTHON", str(Path(sys.executable).resolve()))
    monkeypatch.setenv("ARCHEAXIS_SCHEDULER_WORKER", str(worker))
    monkeypatch.setenv("AAOS_TEST_SCHEDULER_MARKER", str(marker))
    monkeypatch.setenv("AAOS_TEST_SCHEDULER_TARGET", str(ROOT / "services/python-workers/learning/worker_schedule.py"))
    item = "synthetic-many-outage-reviews"
    try:
        core.start()
        core.stop()
        # Populate a wholly synthetic historical workspace, not the user's database.
        row = json.dumps({"outcome": "correct", "assessment_id": None, "schedule": {"authority": "unavailable"},
                          "review_evidence": {"rating": 3, "now": "2026-09-01T00:00:00+00:00"}})
        with sqlite3.connect(tmp_path / "workspace.sqlite") as conn:
            conn.executemany("INSERT INTO learning_events(item_key,kind,outcome) VALUES(?,'review',?)",
                             [(item, row)] * 130)
        core.start()
        status, recovered = core.request("POST", "/api/v1/learning/reviews", {
            "item_key": item, "client_event_id": "after-many", "correct": True,
            "rating": 3, "now": "2026-09-03T00:00:00+00:00"})
        assert status == 201 and recovered["schedule_authority"] == "fsrs"
        assert recovered["schedule_recovery"]["count"] == 130
        assert len(marker.read_text(encoding="utf-8").splitlines()) == 3
    finally:
        core.stop()


def test_fsrs_float_state_is_exact_across_core_restart_and_restore(tmp_path, monkeypatch):
    core = core_for(tmp_path)
    worker = tmp_path / "precision_scheduler.py"
    marker = tmp_path / "precision-inputs.jsonl"
    worker.write_text(
        "import json,os,sys\n"
        "from datetime import datetime,timedelta\n"
        "request=json.load(sys.stdin)\n"
        "with open(os.environ['AAOS_TEST_SCHEDULER_MARKER'],'a',encoding='utf-8') as out:\n"
        "    out.write(json.dumps(request['state'])+'\\n')\n"
        "due=(datetime.fromisoformat(request['now'].replace('Z','+00:00'))+timedelta(days=1)).isoformat()\n"
        "print(json.dumps({'authority':'fsrs','next_review_days':1,'due':due,"
        "'state':'review','step':None,'stability':51.248178375505404,'difficulty':7.382336607835277,"
        "'last_review':request['now']}))\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("ARCHEAXIS_PYTHON", str(Path(sys.executable).resolve()))
    monkeypatch.setenv("ARCHEAXIS_SCHEDULER_WORKER", str(worker))
    monkeypatch.setenv("AAOS_TEST_SCHEDULER_MARKER", str(marker))
    item = "synthetic-exact-fsrs-state"
    expected = {"stability": 51.248178375505404, "difficulty": 7.382336607835277}
    first_body = {**request(item, "precise-first"), "rating": 3}
    second_body = {**request(item, "precise-second"), "rating": 3, "now": "2026-09-03T00:00:00+00:00"}
    try:
        core.start()
        status, first = core.request("POST", "/api/v1/learning/reviews", first_body)
        assert status == 201 and first["schedule_authority"] == "fsrs"
        assert all(first["schedule_state"][key] == value for key, value in expected.items())
        assert first["mastery_projection"]["stability"] == expected["stability"]
        core.stop()
        core.start()
        state = core.request("GET", f"/api/v1/learning/items/{item}/state")[1]
        assert all(state["learner"]["latest_review"]["schedule_state"][key] == value
                   for key, value in expected.items())
        assert state["learner"]["latest_review"]["mastery_projection"]["stability"] == expected["stability"]
        status, second = core.request("POST", "/api/v1/learning/reviews", second_body)
        assert status == 201 and second["schedule_authority"] == "fsrs"
        inputs = [json.loads(line) for line in marker.read_text(encoding="utf-8").splitlines()]
        assert all(inputs[1][key] == value for key, value in expected.items())
        status, backup = core.request("POST", "/api/v1/workspace/backups", {})
        assert status == 201 and backup["verified"] is True
        artifact = tmp_path / "backups" / backup["filename"]
        assert hashlib.sha256(artifact.read_bytes()).hexdigest() == backup["sha256"]
        exe = core.exe
        core.stop()
        destination = tmp_path / "precision-restore"
        destination.mkdir()
        restored = subprocess.run([str(exe), "--maintenance-restore", str(destination / "workspace.sqlite"),
                                   str(artifact)], capture_output=True, text=True, timeout=120, check=False)
        assert restored.returncode == 0 and json.loads(restored.stdout)["ok"] is True
        from scripts.ci.real_core_grading_journey import Core
        core = Core(exe, destination, Path(sys.executable))
        core.start()
        state = core.request("GET", f"/api/v1/learning/items/{item}/state")[1]
        assert all(state["learner"]["latest_review"]["schedule_state"][key] == value
                   for key, value in expected.items())
        assert core.request("POST", "/api/v1/learning/reviews", second_body)[1]["schedule_state"] == second["schedule_state"]
    finally:
        core.stop()


@pytest.mark.parametrize("historical", [False, True])
def test_out_of_order_review_time_never_produces_a_schedule(tmp_path, monkeypatch, historical):
    core = core_for(tmp_path)
    marker = tmp_path / "time-order-calls.txt"
    worker = tmp_path / "time_order_scheduler.py"
    worker.write_text(
        "import os,runpy\n"
        "with open(os.environ['AAOS_TEST_SCHEDULER_MARKER'],'a',encoding='utf-8') as out: out.write('call\\n')\n"
        "runpy.run_path(os.environ['AAOS_TEST_SCHEDULER_TARGET'],run_name='__main__')\n",
        encoding="utf-8",
    )
    item = "synthetic-time-order"
    later = "2026-09-03T08:00:00.000002+08:00"
    earlier = "2026-09-03T00:00:00.000001Z"
    try:
        monkeypatch.setenv("ARCHEAXIS_PYTHON", str(tmp_path / "missing-python"))
        core.start()
        status, first = core.request("POST", "/api/v1/learning/reviews", {
            "item_key": item, "client_event_id": "record-later", "correct": False, "rating": 1, "now": later})
        assert status == 201 and first["schedule_authority"] == "unavailable"
        if historical:
            # Simulate previously accepted historical evidence; the production path must not rewrite it.
            core.stop()
            with sqlite3.connect(tmp_path / "workspace.sqlite") as conn:
                row = json.dumps({"outcome": "correct", "assessment_id": None,
                    "schedule": {"authority": "unavailable"}, "review_evidence": {"rating": 3, "now": earlier}})
                conn.execute("INSERT INTO learning_events(item_key,kind,outcome) VALUES(?,'review',?)", (item, row))
        else:
            core.stop()
        monkeypatch.setenv("ARCHEAXIS_PYTHON", str(Path(sys.executable).resolve()))
        monkeypatch.setenv("ARCHEAXIS_SCHEDULER_WORKER", str(worker))
        monkeypatch.setenv("AAOS_TEST_SCHEDULER_MARKER", str(marker))
        monkeypatch.setenv("AAOS_TEST_SCHEDULER_TARGET", str(ROOT / "services/python-workers/learning/worker_schedule.py"))
        core.start()
        body = {"item_key": item, "client_event_id": "new-review", "correct": True, "rating": 3,
                "now": "2026-09-04T00:00:00Z" if historical else earlier}
        status, result = core.request("POST", "/api/v1/learning/reviews", body)
        if historical:
            assert status == 201 and result["schedule_authority"] == "unavailable" and result["next_review"] is None
            assert result["schedule_recovery"]["reason"] == "unscheduled_review_time_order_invalid"
            assert core.request("GET", f"/api/v1/learning/events/{item}")[1]["count"] == 3
        else:
            assert status == 400
            assert core.request("GET", f"/api/v1/learning/events/{item}")[1]["count"] == 1
        assert not marker.exists()
        if not historical:
            status, corrected = core.request("POST", "/api/v1/learning/reviews", {
                **body, "now": "2026-09-04T00:00:00Z"})
            assert status == 201 and corrected["schedule_authority"] == "fsrs"
            assert corrected["schedule_recovery"]["count"] == 1
    finally:
        core.stop()


def test_new_review_cannot_predate_last_successful_card(tmp_path, monkeypatch):
    core = core_for(tmp_path)
    marker = tmp_path / "time-order-success-calls.txt"
    worker = tmp_path / "time_order_success_scheduler.py"
    worker.write_text(
        "import os,runpy\n"
        "with open(os.environ['AAOS_TEST_SCHEDULER_MARKER'],'a',encoding='utf-8') as out: out.write('call\\n')\n"
        "runpy.run_path(os.environ['AAOS_TEST_SCHEDULER_TARGET'],run_name='__main__')\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("ARCHEAXIS_PYTHON", str(Path(sys.executable).resolve()))
    monkeypatch.setenv("ARCHEAXIS_SCHEDULER_WORKER", str(worker))
    monkeypatch.setenv("AAOS_TEST_SCHEDULER_MARKER", str(marker))
    monkeypatch.setenv("AAOS_TEST_SCHEDULER_TARGET", str(ROOT / "services/python-workers/learning/worker_schedule.py"))
    item = "synthetic-time-after-success"
    try:
        core.start()
        status, first = core.request("POST", "/api/v1/learning/reviews", {
            "item_key": item, "client_event_id": "later-first", "correct": True, "rating": 3,
            "now": "2026-09-03T08:00:00.000002+08:00"})
        assert status == 201 and first["schedule_authority"] == "fsrs"
        body = {"item_key": item, "client_event_id": "earlier-next", "correct": False, "rating": 1,
                "now": "2026-09-03T00:00:00.000001Z"}
        assert core.request("POST", "/api/v1/learning/reviews", body)[0] == 400
        assert marker.read_text(encoding="utf-8").splitlines() == ["call"]
        assert core.request("GET", f"/api/v1/learning/events/{item}")[1]["count"] == 1
        status, corrected = core.request("POST", "/api/v1/learning/reviews", {
            **body, "now": "2026-09-04T00:00:00Z"})
        assert status == 201 and corrected["schedule_authority"] == "fsrs"
        assert marker.read_text(encoding="utf-8").splitlines() == ["call", "call"]
    finally:
        core.stop()


@pytest.mark.parametrize("bad_result", ["instant", "past_due", "wrong_interval"])
def test_scheduler_result_must_bind_the_requested_review_instant(tmp_path, monkeypatch, bad_result):
    core = core_for(tmp_path)
    worker = tmp_path / "wrong_time_scheduler.py"
    payload = {"authority": "fsrs", "next_review_days": 17 if bad_result == "wrong_interval" else 1,
        "due": ("2026-09-01T00:00:00Z" if bad_result == "past_due" else
                "2026-09-03T00:00:01Z" if bad_result == "instant" else "2026-09-03T00:00:00Z"),
        "state": "review", "step": None, "stability": 3.0, "difficulty": 5.0,
        "last_review": "2026-09-02T00:00:01Z" if bad_result == "instant" else "2026-09-02T00:00:00Z"}
    worker.write_text("import json\nprint(json.dumps(" + repr(payload) + "))\n", encoding="utf-8")
    monkeypatch.setenv("ARCHEAXIS_PYTHON", str(Path(sys.executable).resolve()))
    monkeypatch.setenv("ARCHEAXIS_SCHEDULER_WORKER", str(worker))
    item = "synthetic-wrong-scheduler-time"
    try:
        core.start()
        status, receipt = core.request("POST", "/api/v1/learning/reviews", {
            "item_key": item, "client_event_id": "wrong-time", "correct": True, "rating": 3,
            "now": "2026-09-02T08:00:00+08:00"})
        assert status == 201 and receipt["schedule_authority"] == "unavailable" and receipt["next_review"] is None
        assert receipt["schedule_recovery"]["reason"] == (
            "scheduler_time_mismatch" if bad_result == "instant" else "invalid_scheduler_card")
        assert core.request("GET", f"/api/v1/learning/events/{item}")[1]["count"] == 1
        core.stop()
        monkeypatch.delenv("ARCHEAXIS_SCHEDULER_WORKER")
        core.start()
        status, recovered = core.request("POST", "/api/v1/learning/reviews", {
            "item_key": item, "client_event_id": "after-wrong-time", "correct": True, "rating": 3,
            "now": "2026-09-03T00:00:00Z"})
        assert status == 201 and recovered["schedule_authority"] == "fsrs"
        assert recovered["schedule_recovery"]["count"] == 1
    finally:
        core.stop()


@pytest.mark.parametrize("bad_state", ["missing", "null", "number", "encoded_object"])
@pytest.mark.parametrize("assessed", [False, True])
def test_damaged_historical_fsrs_card_stays_unscheduled_until_reset(tmp_path, monkeypatch, bad_state, assessed):
    core = core_for(tmp_path)
    item = "synthetic-damaged-fsrs-card"
    monkeypatch.setenv("ARCHEAXIS_PYTHON", str(Path(sys.executable).resolve()))
    binding = {}
    try:
        core.start()
        if assessed:
            status, knowledge = core.request("POST", "/api/v1/knowledge-items", {
                "knowledge_type": "FACTUAL_CLAIM", "body": "Synthetic fact", "status": "accepted",
                "created_by": "fixture"})
            assert status == 201
            base = f"/api/v1/learning/items/{item}"
            assert core.request("POST", base + "/references", {"knowledge_id": knowledge["knowledge_id"]})[0] == 201
            status, assessment = core.request("POST", base + "/assessment", {"knowledge_id": knowledge["knowledge_id"]})
            assert status == 201
            binding = {"assessment_id": assessment["assessment_id"], "knowledge_version": assessment["knowledge_version"]}
        status, old = core.request("POST", "/api/v1/learning/reviews", {
            "item_key": item, "client_event_id": "valid-before-damage", "correct": True, "rating": 3,
            "now": "2026-09-02T00:00:00Z", **binding})
        assert status == 201 and old["schedule_authority"] == "fsrs"
        core.stop()
        # Create damaged historical shapes only in this isolated fixture database.
        with sqlite3.connect(tmp_path / "workspace.sqlite") as conn:
            raw = conn.execute("SELECT outcome FROM learning_events WHERE event_id=?", (old["event_id"],)).fetchone()[0]
            outcome = json.loads(raw)
            card = outcome["schedule"]["state"]
            if bad_state == "missing":
                del outcome["schedule"]["state"]
            else:
                outcome["schedule"]["state"] = {"null": None, "number": 7,
                                                "encoded_object": json.dumps(card)}[bad_state]
            damaged = json.dumps(outcome, ensure_ascii=False)
            conn.execute("UPDATE learning_events SET outcome=? WHERE event_id=?", (damaged, old["event_id"]))
        core.start()
        body = {"item_key": item, "client_event_id": "after-damaged-card", "correct": True, "rating": 3,
                "now": "2026-09-03T00:00:00Z", **binding}
        status, blocked = core.request("POST", "/api/v1/learning/reviews", body)
        assert status == 201 and blocked["schedule_authority"] == "unavailable", (status, blocked)
        assert blocked["next_review"] is None and blocked["schedule_recovery"]["reason"] == "invalid_previous_card"
        reset_body = {**body, "client_event_id": "reset-damaged-card", "schedule_reset": {
            "mode": "start_new", "reason": "Synthetic prior card is damaged",
            "expected_latest_event_id": blocked["event_id"]}}
        status, reset = core.request("POST", "/api/v1/learning/reviews", reset_body)
        assert status == 201 and reset["schedule_authority"] == "fsrs"
        status, after = core.request("POST", "/api/v1/learning/reviews", {
            **body, "client_event_id": "after-damaged-reset", "now": "2026-09-04T00:00:00Z"})
        assert status == 201 and after["schedule_recovery"]["baseline_reset_event_id"] == reset["event_id"]
        history = core.request("GET", f"/api/v1/learning/events/{item}")[1]["events"]
        assert history[0]["outcome"] == damaged
        core.stop()
        core.start()
        assert core.request("GET", f"/api/v1/learning/events/{item}")[1]["events"] == history
        status, replay = core.request("POST", "/api/v1/learning/reviews", reset_body)
        assert status == 200 and replay["duplicate"] is True and replay["event_id"] == reset["event_id"]
    finally:
        core.stop()


@pytest.mark.parametrize("legacy_authority", ["placeholder_ladder", "fsrs", "unavailable"])
@pytest.mark.parametrize("prior_fsrs", [False, True])
def test_legacy_review_gap_requires_explicit_new_baseline(tmp_path, monkeypatch, legacy_authority, prior_fsrs):
    core = core_for(tmp_path)
    item = "synthetic-legacy-review-gap"
    good_python = str(Path(sys.executable).resolve())
    monkeypatch.setenv("ARCHEAXIS_PYTHON", good_python)
    try:
        core.start()
        if prior_fsrs:
            status, first = core.request("POST", "/api/v1/learning/reviews", {
                "item_key": item, "client_event_id": "prior-stateful", "correct": True, "rating": 3,
                "now": "2026-09-01T00:00:00Z"})
            assert status == 201 and first["schedule_authority"] == "fsrs"
        if legacy_authority == "unavailable":
            core.stop()
            monkeypatch.setenv("ARCHEAXIS_PYTHON", str(tmp_path / "missing-python"))
            core.start()
        legacy = {"item_key": item, "kind": "review", "client_event_id": "old-legacy",
                  "correct": True, "now": "2026-09-02T00:00:00Z"}
        if legacy_authority != "placeholder_ladder":
            legacy["schedule_state"] = legacy_request()["schedule_state"]
        status, old = core.request("POST", "/api/v1/learning/events", legacy)
        assert status == 201 and old["schedule_authority"] == legacy_authority
        original = core.request("GET", f"/api/v1/learning/events/{item}")[1]["events"][-1]["outcome"]
        core.stop()
        monkeypatch.setenv("ARCHEAXIS_PYTHON", good_python)
        core.start()
        body = {"item_key": item, "client_event_id": "after-legacy", "correct": True, "rating": 3,
                "now": "2026-09-03T00:00:00Z"}
        status, blocked = core.request("POST", "/api/v1/learning/reviews", body)
        assert status == 201 and blocked["schedule_authority"] == "unavailable", blocked
        assert blocked["next_review"] is None
        assert blocked["schedule_recovery"]["reason"] == "legacy_review_evidence_missing_or_invalid"
        reset_body = {**body, "client_event_id": "explicit-legacy-reset", "schedule_reset": {
            "mode": "start_new", "reason": "Legacy review lacks a recoverable card and time",
            "expected_latest_event_id": blocked["event_id"]}}
        status, reset = core.request("POST", "/api/v1/learning/reviews", reset_body)
        assert status == 201 and reset["schedule_authority"] == "fsrs"
        status, after = core.request("POST", "/api/v1/learning/reviews", {
            **body, "client_event_id": "after-legacy-reset", "now": "2026-09-04T00:00:00Z"})
        assert status == 201 and after["schedule_recovery"]["baseline_reset_event_id"] == reset["event_id"]
        history = core.request("GET", f"/api/v1/learning/events/{item}")[1]["events"]
        assert next(event for event in history if event["event_id"] == old["event_id"])["outcome"] == original
        status, replay = core.request("POST", "/api/v1/learning/events", legacy)
        assert status == 200 and replay["event_id"] == old["event_id"]
        assert replay["schedule_authority"] == legacy_authority
    finally:
        core.stop()


def assert_unverified_schedule_projection(core, item, reason):
    status, state = core.request("GET", f"/api/v1/learning/items/{item}/state")
    assert status == 200 and state["learner"]["next_review"] is None
    assert state["learner"]["latest_review"]["next_review"] is None
    assert state["learner"]["schedule_integrity"] == {"state": "unverified", "reason": reason}
    status, queue = core.request("GET", "/api/v1/learning/items")
    row = next(value for value in queue["items"] if value["item_key"] == item)
    assert status == 200 and row["next_review"] is None
    assert row["schedule_integrity"] == {"state": "unverified", "reason": reason}


def test_legacy_gap_before_an_existing_fsrs_card_remains_visible(tmp_path, monkeypatch):
    core = core_for(tmp_path)
    item = "synthetic-legacy-before-card"
    monkeypatch.setenv("ARCHEAXIS_PYTHON", str(Path(sys.executable).resolve()))
    try:
        core.start()
        status, old = core.request("POST", "/api/v1/learning/events", {
            "item_key": item, "client_event_id": "legacy-first", "correct": True})
        assert status == 201
        status, card = core.request("POST", "/api/v1/learning/reviews", {
            "item_key": "synthetic-card-donor", "client_event_id": "separate-card", "correct": True,
            "rating": 3, "now": "2026-09-02T00:00:00Z"})
        assert status == 201 and card["schedule_authority"] == "fsrs"
        core.stop()
        # Build the historical shape in an isolated test database: a prior
        # Core had saved an FSRS card after silently skipping a legacy review.
        with sqlite3.connect(tmp_path / "workspace.sqlite") as conn:
            conn.execute("INSERT INTO learning_events(item_key,kind,outcome,next_review) "
                         "SELECT ?,kind,outcome,next_review FROM learning_events WHERE event_id=?",
                         (item, card["event_id"]))
        core.start()
        before = core.request("GET", f"/api/v1/learning/events/{item}")[1]
        assert before["count"] == 2 and before["events"][0]["event_id"] == old["event_id"]
        assert_unverified_schedule_projection(core, item, "legacy_review_evidence_missing_or_invalid")
        assert before["events"][-1]["next_review"] == card["next_review"]
        body = {
            "item_key": item, "client_event_id": "after-existing-card", "correct": True, "rating": 3,
            "now": "2026-09-03T00:00:00Z"}
        status, result = core.request("POST", "/api/v1/learning/reviews", body)
        assert status == 201 and result["schedule_authority"] == "unavailable"
        assert result["schedule_recovery"]["reason"] == "legacy_review_evidence_missing_or_invalid"
        after = core.request("GET", f"/api/v1/learning/events/{item}")[1]
        assert after["events"][:2] == before["events"]
        status, backup = core.request("POST", "/api/v1/workspace/backups", {})
        assert status == 201 and backup["verified"] is True
        artifact = tmp_path / "backups" / backup["filename"]
        assert hashlib.sha256(artifact.read_bytes()).hexdigest() == backup["sha256"]
        exe = core.exe
        core.stop()
        destination = tmp_path / "legacy-gap-restore"
        destination.mkdir()
        restored = subprocess.run([str(exe), "--maintenance-restore", str(destination / "workspace.sqlite"),
                                   str(artifact)], capture_output=True, text=True, timeout=120, check=False)
        assert restored.returncode == 0 and json.loads(restored.stdout)["ok"] is True
        from scripts.ci.real_core_grading_journey import Core
        core = Core(exe, destination, Path(sys.executable))
        core.start()
        assert core.request("GET", f"/api/v1/learning/events/{item}")[1] == after
        assert_unverified_schedule_projection(core, item, "legacy_review_evidence_missing_or_invalid")
        status, replay = core.request("POST", "/api/v1/learning/reviews", body)
        assert status == 200 and replay["event_id"] == result["event_id"]
        assert replay["schedule_authority"] == "unavailable"
        status, following = core.request("POST", "/api/v1/learning/reviews", {
            **body, "client_event_id": "after-gap-restore", "now": "2026-09-04T00:00:00Z"})
        assert status == 201 and following["schedule_recovery"]["reason"] == "legacy_review_evidence_missing_or_invalid"
        status, reset = core.request("POST", "/api/v1/learning/reviews", {
            **body, "client_event_id": "explicit-legacy-projection-reset", "now": "2026-09-05T00:00:00Z",
            "schedule_reset": {"mode": "start_new", "reason": "Synthetic human reset",
                               "expected_latest_event_id": following["event_id"]}})
        assert status == 201 and reset["schedule_authority"] == "fsrs"
        core.stop()
        core.start()
        status, state = core.request("GET", f"/api/v1/learning/items/{item}/state")
        assert status == 200 and state["learner"]["next_review"] == reset["next_review"]
        assert "schedule_integrity" not in state["learner"]
        assert core.request("GET", f"/api/v1/learning/events/{item}")[1]["events"][:len(after["events"])] == after["events"]
    finally:
        core.stop()


@pytest.mark.parametrize("old_scheduled", [True, False])
def test_explicit_schedule_reset_starts_before_mistimed_old_card(tmp_path, monkeypatch, old_scheduled):
    core = core_for(tmp_path)
    item = "synthetic-future-review-reset"
    good_python = str(Path(sys.executable).resolve())
    monkeypatch.setenv("ARCHEAXIS_PYTHON", good_python if old_scheduled else str(tmp_path / "missing-python"))
    try:
        core.start()
        status, old = core.request("POST", "/api/v1/learning/reviews", {
            "item_key": item, "client_event_id": "mistimed-old", "correct": True, "rating": 3,
            "now": "2030-09-03T00:00:00Z"})
        assert status == 201 and old["schedule_authority"] == ("fsrs" if old_scheduled else "unavailable")
        if not old_scheduled:
            core.stop()
            monkeypatch.setenv("ARCHEAXIS_PYTHON", good_python)
            core.start()
        original = core.request("GET", f"/api/v1/learning/events/{item}")[1]["events"][0]["outcome"]
        body = {"item_key": item, "client_event_id": "fresh-baseline", "correct": True, "rating": 3,
                "now": "2026-09-03T00:00:00Z"}
        assert core.request("POST", "/api/v1/learning/reviews", body)[0] == 400
        assert core.request("GET", f"/api/v1/learning/events/{item}")[1]["count"] == 1
        reset_body = {**body, "schedule_reset": {"mode": "start_new", "reason": "Old time was mistyped",
                      "expected_latest_event_id": old["event_id"]}}
        status, reset = core.request("POST", "/api/v1/learning/reviews", reset_body)
        assert status == 201 and reset["schedule_authority"] == "fsrs", reset
        assert reset["schedule_recovery"]["excluded_through_event_id"] == old["event_id"]
        assert reset["schedule_state"]["last_review"].startswith("2026-09-03T00:00:00")
        core.stop()
        core.start()
        assert core.request("POST", "/api/v1/learning/reviews", reset_body)[1]["event_id"] == reset["event_id"]
        before = {"item_key": item, "client_event_id": "before-fresh-baseline", "correct": True,
                  "rating": 3, "now": "2026-09-02T23:59:59Z"}
        assert core.request("POST", "/api/v1/learning/reviews", before)[0] == 400
        status, after = core.request("POST", "/api/v1/learning/reviews", {
            **before, "client_event_id": "after-fresh-baseline", "now": "2026-09-04T00:00:00Z"})
        assert status == 201 and after["schedule_authority"] == "fsrs"
        assert after["schedule_recovery"]["baseline_reset_event_id"] == reset["event_id"]
        history = core.request("GET", f"/api/v1/learning/events/{item}")[1]
        assert history["count"] == 3 and history["events"][0]["outcome"] == original
    finally:
        core.stop()


@pytest.mark.skipif(not os.environ.get("AAOS_TEST_BRIDGE_EXE"), reason="explicit compiled host bridge required")
@pytest.mark.parametrize("assessed", [False, True])
def test_host_bridge_schedule_reset_and_restart(tmp_path, monkeypatch, assessed):
    bridge = Path(os.environ["AAOS_TEST_BRIDGE_EXE"]).resolve(strict=True)
    core = core_for(tmp_path)
    identity = tmp_path / "synthetic-host-reset.json"
    monkeypatch.setenv("ARCHEAXIS_PYTHON", str(Path(sys.executable).resolve()))
    try:
        for phase in ("create", "reopen", "restore"):
            if phase != "create":
                monkeypatch.setenv("ARCHEAXIS_PYTHON", str(tmp_path / "missing-python"))
            if phase == "restore":
                saved = json.loads(identity.read_text(encoding="utf-8"))
                filename = saved["backup_filename"]
                assert isinstance(filename, str) and Path(filename).name == filename
                artifact = tmp_path / "backups" / filename
                assert hashlib.sha256(artifact.read_bytes()).hexdigest() == saved["backup_sha256"]
                destination = tmp_path / "host-reset-restore"
                destination.mkdir()
                restored = subprocess.run([str(core.exe), "--maintenance-restore", str(destination / "workspace.sqlite"),
                                           str(artifact)], capture_output=True, text=True, timeout=120, check=False)
                result = json.loads(restored.stdout) if restored.stdout else {}
                assert restored.returncode == 0 and result.get("ok") is True
                assert result.get("authorization_requires_new_grants") is True
                from scripts.ci.real_core_grading_journey import Core
                core = Core(core.exe, destination, Path(sys.executable))
            core.start()
            env = dict(os.environ, AAOS_SYNTHETIC_CORE_PORT=str(core.port),
                       AAOS_SYNTHETIC_CORE_TOKEN=core.token, AAOS_SYNTHETIC_CORE_PHASE=phase,
                       AAOS_SYNTHETIC_LEARNING_STATE=str(identity), AAOS_SYNTHETIC_ASSESSED="1" if assessed else "0")
            if phase == "create" and assessed:
                for label, key in (("previous", "AAOS_SYNTHETIC_PREVIOUS_KNOWLEDGE_ID"),
                                   ("current", "AAOS_SYNTHETIC_KNOWLEDGE_ID")):
                    status, knowledge = core.request("POST", "/api/v1/knowledge-items", {
                        "knowledge_type": "FACTUAL_CLAIM", "body": f"Synthetic {label} host assessment",
                        "status": "accepted", "created_by": "fixture"})
                    assert status == 201
                    env[key] = knowledge["knowledge_id"]
            result = subprocess.run([str(bridge), "learning_schedule_reset_real_core_transport",
                                     "--ignored", "--test-threads=1"],
                                    env=env, capture_output=True, text=True, timeout=90, check=False)
            assert result.returncode == 0, (phase, result.stdout, result.stderr)
            assert "test tests::learning_schedule_reset_real_core_transport ... ok" in result.stdout
            assert "1 passed; 0 failed" in result.stdout
            core.stop()
    finally:
        core.stop()


def test_explicit_schedule_reset_preserves_unrecoverable_history(tmp_path, monkeypatch):
    core = core_for(tmp_path)
    item = "synthetic-declared-schedule-reset"
    try:
        monkeypatch.setenv("ARCHEAXIS_PYTHON", str(tmp_path / "missing-python"))
        core.start()
        status, old = core.request("POST", "/api/v1/learning/reviews", {
            "item_key": item, "client_event_id": "old-unknown-time", "correct": False, "rating": 1})
        assert status == 201 and old["schedule_authority"] == "unavailable"
        core.stop()
        # Reproduce a legacy event in an isolated synthetic database.
        with sqlite3.connect(tmp_path / "workspace.sqlite") as conn:
            conn.execute("UPDATE learning_events SET outcome=json_remove(outcome,'$.schedule.reviewed_at') WHERE event_id=?",
                         (old["event_id"],))
        monkeypatch.setenv("ARCHEAXIS_PYTHON", str(Path(sys.executable).resolve()))
        core.start()
        original = core.request("GET", f"/api/v1/learning/events/{item}")[1]["events"][0]["outcome"]
        status, blocked = core.request("POST", "/api/v1/learning/reviews", {
            "item_key": item, "client_event_id": "no-reset", "correct": True, "rating": 3,
            "now": "2026-11-11T00:00:00Z"})
        assert status == 201 and blocked["schedule_authority"] == "unavailable"
        body = {"item_key": item, "client_event_id": "declared-reset", "correct": True, "rating": 3,
            "now": "2026-11-12T00:00:00Z",
            "schedule_reset": {"mode": "start_new", "reason": "Synthetic historical time is unknown",
                               "expected_latest_event_id": blocked["event_id"]}}
        stale = {**body, "schedule_reset": {**body["schedule_reset"], "expected_latest_event_id": old["event_id"]}}
        assert core.request("POST", "/api/v1/learning/reviews", stale)[0] == 409
        for invalid in ({**body["schedule_reset"], "reason": " "},
                        {**body["schedule_reset"], "reason": "x" * 513},
                        {**body["schedule_reset"], "mode": "automatic"},
                        {**body["schedule_reset"], "expected_latest_event_id": 0}):
            assert core.request("POST", "/api/v1/learning/reviews", {**body, "schedule_reset": invalid})[0] == 400
        assert core.request("POST", "/api/v1/learning/reviews", {
            **body, "schedule_reset": {**body["schedule_reset"], "unexpected": True}})[0] == 422
        assert core.request("GET", f"/api/v1/learning/events/{item}")[1]["count"] == 2
        status, reset = core.request("POST", "/api/v1/learning/reviews", body)
        assert status == 201 and reset["schedule_authority"] == "fsrs"
        assert core.request("POST", "/api/v1/learning/reviews", body, token=core.machine_token)[0] == 403
        assert reset["schedule_recovery"]["state"] == "reset"
        assert reset["schedule_recovery"]["excluded_through_event_id"] == blocked["event_id"]
        assert reset["schedule_recovery"]["reason"] == body["schedule_reset"]["reason"]
        assert reset["review_evidence"]["schedule_reset"] == body["schedule_reset"]
        status, replay = core.request("POST", "/api/v1/learning/reviews", body)
        assert status == 200 and replay["duplicate"] is True and replay["event_id"] == reset["event_id"]
        changed = {**body, "schedule_reset": {**body["schedule_reset"], "reason": "changed reason"}}
        assert core.request("POST", "/api/v1/learning/reviews", changed)[0] == 409
        status, later = core.request("POST", "/api/v1/learning/reviews", {
            "item_key": item, "client_event_id": "after-declared-reset", "correct": True, "rating": 3,
            "now": "2026-11-13T00:00:00Z"})
        assert status == 201 and later["schedule_authority"] == "fsrs"
        assert later["schedule_recovery"]["baseline_reset_event_id"] == reset["event_id"]
        history = core.request("GET", f"/api/v1/learning/events/{item}")[1]
        assert history["count"] == 4 and history["events"][0]["outcome"] == original
        assert reset["mastery_projection"]["closed"] is False
        state = core.request("GET", f"/api/v1/learning/items/{item}/state")[1]
        assert state["learner"]["latest_review"]["schedule_recovery"]["baseline_reset_event_id"] == reset["event_id"]
        from jsonschema import Draft202012Validator
        schema = json.loads((ROOT / "packages/contracts/v1/core-document.schema.json").read_text(encoding="utf-8"))
        assert not list(Draft202012Validator({"$defs": schema["$defs"], "$ref": "#/$defs/LearningStateDto"}).iter_errors(state))
        core.stop()
        core.start()
        assert core.request("GET", f"/api/v1/learning/events/{item}")[1] == history
        status, backup = core.request("POST", "/api/v1/workspace/backups", {})
        assert status == 201 and backup["verified"] is True
        artifact = tmp_path / "backups" / backup["filename"]
        assert hashlib.sha256(artifact.read_bytes()).hexdigest() == backup["sha256"]
        exe = core.exe
        core.stop()
        destination = tmp_path / "reset-restore"
        destination.mkdir()
        restored = subprocess.run([str(exe), "--maintenance-restore", str(destination / "workspace.sqlite"),
                                   str(artifact)], capture_output=True, text=True, timeout=120, check=False)
        assert restored.returncode == 0 and json.loads(restored.stdout)["ok"] is True
        from scripts.ci.real_core_grading_journey import Core
        core = Core(exe, destination, Path(sys.executable))
        core.start()
        assert core.request("GET", f"/api/v1/learning/events/{item}")[1] == history
        status, restored_replay = core.request("POST", "/api/v1/learning/reviews", body)
        assert status == 200 and restored_replay["event_id"] == reset["event_id"]
        status, after_restore = core.request("POST", "/api/v1/learning/reviews", {
            "item_key": item, "client_event_id": "reset-after-restore", "correct": True, "rating": 3,
            "now": "2026-11-14T00:00:00Z"})
        assert status == 201 and after_restore["schedule_recovery"]["baseline_reset_event_id"] == reset["event_id"]
    finally:
        core.stop()


@pytest.mark.parametrize("bad_worker", [False, True])
def test_failed_schedule_reset_does_not_write_and_same_key_can_retry(tmp_path, monkeypatch, bad_worker):
    core = core_for(tmp_path)
    item = "synthetic-reset-failure"
    missing = str(tmp_path / "missing-python")
    bad = tmp_path / "bad_reset_scheduler.py"
    bad.write_text("import json\nprint(json.dumps({'authority':'fsrs','next_review_days':-2}))\n", encoding="utf-8")
    try:
        monkeypatch.setenv("ARCHEAXIS_PYTHON", missing)
        core.start()
        status, first = core.request("POST", "/api/v1/learning/reviews", {
            "item_key": item, "client_event_id": "before-reset", "correct": False, "rating": 1,
            "now": "2026-09-01T00:00:00Z"})
        assert status == 201 and first["schedule_authority"] == "unavailable"
        core.stop()
        if bad_worker:
            monkeypatch.setenv("ARCHEAXIS_PYTHON", str(Path(sys.executable).resolve()))
            monkeypatch.setenv("ARCHEAXIS_SCHEDULER_WORKER", str(bad))
        core.start()
        body = {"item_key": item, "client_event_id": "retry-reset", "correct": True, "rating": 3,
            "now": "2026-09-02T00:00:00Z", "schedule_reset": {"mode": "start_new", "reason": "Synthetic reset",
                "expected_latest_event_id": first["event_id"]}}
        assert core.request("POST", "/api/v1/learning/reviews", body)[0] == 503
        assert core.request("GET", f"/api/v1/learning/events/{item}")[1]["count"] == 1
        core.stop()
        monkeypatch.setenv("ARCHEAXIS_PYTHON", str(Path(sys.executable).resolve()))
        monkeypatch.delenv("ARCHEAXIS_SCHEDULER_WORKER", raising=False)
        core.start()
        status, reset = core.request("POST", "/api/v1/learning/reviews", body)
        assert status == 201 and reset["schedule_authority"] == "fsrs"
        assert reset["schedule_recovery"]["state"] == "reset"
        assert core.request("GET", f"/api/v1/learning/events/{item}")[1]["count"] == 2
    finally:
        core.stop()


def test_explicit_schedule_reset_can_leave_oversized_history_intact(tmp_path, monkeypatch):
    core = core_for(tmp_path)
    monkeypatch.setenv("ARCHEAXIS_PYTHON", str(Path(sys.executable).resolve()))
    item = "synthetic-reset-oversized"
    try:
        core.start()
        core.stop()
        row = json.dumps({"outcome": "correct", "assessment_id": None, "schedule": {"authority": "unavailable"},
                          "review_evidence": {"rating": 3, "now": "2026-09-01T00:00:00Z"}})
        # The historical rows exist only in this synthetic workspace.
        with sqlite3.connect(tmp_path / "workspace.sqlite") as conn:
            conn.executemany("INSERT INTO learning_events(item_key,kind,outcome) VALUES(?,'review',?)",
                             [(item, row)] * 4097)
        core.start()
        status, blocked = core.request("POST", "/api/v1/learning/reviews", {
            "item_key": item, "client_event_id": "oversized-default", "correct": True, "rating": 3,
            "now": "2026-09-02T00:00:00Z"})
        assert status == 201 and blocked["schedule_authority"] == "unavailable"
        assert blocked["schedule_recovery"]["reason"] == "too_many_unscheduled_reviews"
        status, reset = core.request("POST", "/api/v1/learning/reviews", {
            "item_key": item, "client_event_id": "oversized-reset", "correct": True, "rating": 3,
            "now": "2026-09-03T00:00:00Z", "schedule_reset": {"mode": "start_new",
                "reason": "Synthetic history exceeds the replay bound", "expected_latest_event_id": blocked["event_id"]}})
        assert status == 201 and reset["schedule_authority"] == "fsrs"
        assert reset["schedule_recovery"]["excluded_through_event_id"] == blocked["event_id"]
        state = core.request("GET", f"/api/v1/learning/items/{item}/state")[1]["learner"]
        assert state["event_count"] == 4099
        assert state["latest_review"]["schedule_recovery"]["state"] == "reset"
    finally:
        core.stop()


def test_schedule_reset_rechecks_history_after_slow_worker(tmp_path, monkeypatch):
    core = core_for(tmp_path)
    started, release = tmp_path / "reset-started", tmp_path / "reset-release"
    worker = tmp_path / "reset_race_worker.py"
    worker.write_text(
        "import io,json,os,runpy,sys,time\n"
        "raw=sys.stdin.read(); request=json.loads(raw)\n"
        "if request['rating']==3:\n"
        "    open(os.environ['AAOS_TEST_RESET_STARTED'],'w').write('started')\n"
        "    deadline=time.monotonic()+12\n"
        "    while not os.path.exists(os.environ['AAOS_TEST_RESET_RELEASE']) and time.monotonic()<deadline: time.sleep(.02)\n"
        "sys.stdin=io.StringIO(raw)\n"
        "runpy.run_path(os.environ['AAOS_TEST_SCHEDULER_TARGET'],run_name='__main__')\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("TOKIO_WORKER_THREADS", "4")
    monkeypatch.setenv("ARCHEAXIS_PYTHON", str(Path(sys.executable).resolve()))
    monkeypatch.setenv("ARCHEAXIS_SCHEDULER_WORKER", str(worker))
    monkeypatch.setenv("AAOS_TEST_RESET_STARTED", str(started))
    monkeypatch.setenv("AAOS_TEST_RESET_RELEASE", str(release))
    monkeypatch.setenv("AAOS_TEST_SCHEDULER_TARGET", str(ROOT / "services/python-workers/learning/worker_schedule.py"))
    item = "synthetic-reset-race"
    try:
        core.start()
        status, first = core.request("POST", "/api/v1/learning/reviews", {
            "item_key": item, "client_event_id": "race-first", "correct": True, "rating": 2,
            "now": "2026-09-01T00:00:00Z"})
        assert status == 201 and first["schedule_authority"] == "fsrs"
        reset = {"item_key": item, "client_event_id": "race-reset", "correct": True, "rating": 3,
            "now": "2026-09-03T00:00:00Z", "schedule_reset": {"mode": "start_new", "reason": "Synthetic race",
                "expected_latest_event_id": first["event_id"]}}
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(core.request, "POST", "/api/v1/learning/reviews", reset)
            try:
                deadline = time.monotonic() + 10
                while not started.exists() and time.monotonic() < deadline:
                    time.sleep(.02)
                assert started.exists()
                status, intervening = core.request("POST", "/api/v1/learning/reviews", {
                    "item_key": item, "client_event_id": "race-intervening", "correct": False, "rating": 1,
                    "now": "2026-09-02T00:00:00Z"})
                assert status == 201 and intervening["schedule_authority"] == "fsrs"
            finally:
                release.write_text("release", encoding="utf-8")
            assert future.result(timeout=20)[0] == 409
        assert core.request("GET", f"/api/v1/learning/events/{item}")[1]["count"] == 2
        reset["schedule_reset"]["expected_latest_event_id"] = intervening["event_id"]
        status, accepted = core.request("POST", "/api/v1/learning/reviews", reset)
        assert status == 201 and accepted["schedule_recovery"]["excluded_through_event_id"] == intervening["event_id"]
    finally:
        core.stop()


@pytest.mark.skipif(not os.environ.get("AAOS_TEST_PRE_RESET_BACKUP") or not os.environ.get("AAOS_TEST_PRE_RESET_BACKUP_SHA256"),
                    reason="explicit pre-reset synthetic backup required")
def test_pre_reset_review_receipt_replays_on_reset_capable_core(tmp_path, monkeypatch):
    backup = Path(os.environ["AAOS_TEST_PRE_RESET_BACKUP"]).resolve(strict=True)
    expected = os.environ["AAOS_TEST_PRE_RESET_BACKUP_SHA256"]
    assert hashlib.sha256(backup.read_bytes()).hexdigest() == expected
    core = core_for(tmp_path)
    restored = subprocess.run([str(core.exe), "--maintenance-restore", str(tmp_path / "workspace.sqlite"), str(backup)],
                              capture_output=True, text=True, timeout=120, check=False)
    assert restored.returncode == 0 and json.loads(restored.stdout)["ok"] is True
    monkeypatch.setenv("ARCHEAXIS_PYTHON", str(tmp_path / "missing-scheduler-python"))
    body = {**request("synthetic-stateful-outage", "stateful-outage-key"), "rating": 3}
    try:
        core.start()
        status, receipt = core.request("POST", "/api/v1/learning/reviews", body)
        assert status == 200 and receipt["duplicate"] is True and receipt["schedule_authority"] == "fsrs"
        assert "schedule_reset" not in receipt["review_evidence"]
        assert core.request("POST", "/api/v1/learning/reviews", {**body, "now": "2026-09-03T00:00:00+00:00"})[0] == 409
        assert core.request("GET", "/api/v1/learning/events/synthetic-stateful-outage")[1]["count"] == 1
        assert hashlib.sha256(backup.read_bytes()).hexdigest() == expected
    finally:
        core.stop()


@pytest.mark.parametrize("damage", ["null", "bad-time", "missing-stability", "negative-stability",
                                    "high-difficulty", "unknown-state", "different-due"])
def test_invalid_card_projection_survives_restart_backup_and_reset(tmp_path, monkeypatch, damage):
    item = "synthetic-invalid-card-projection"
    monkeypatch.setenv("ARCHEAXIS_PYTHON", str(Path(sys.executable).resolve()))
    core = core_for(tmp_path)
    try:
        core.start()
        status, original = core.request("POST", "/api/v1/learning/reviews", {
            "item_key": item, "client_event_id": "original-card", "correct": True,
            "rating": 3, "now": "2026-09-02T00:00:00Z"})
        assert status == 201 and original["schedule_authority"] == "fsrs"
        core.stop()
        # Create the damaged historical shape only in this isolated fixture.
        with sqlite3.connect(tmp_path / "workspace.sqlite") as conn:
            (raw,) = conn.execute("SELECT outcome FROM learning_events WHERE event_id=?",
                                  (original["event_id"],)).fetchone()
            outcome = json.loads(raw)
            state = outcome["schedule"]["state"]
            if damage == "null":
                outcome["schedule"]["state"] = None
            elif damage == "bad-time":
                state["last_review"] = "not-a-time"
            elif damage == "missing-stability":
                state.pop("stability")
            elif damage == "negative-stability":
                state["stability"] = -1.0
            elif damage == "high-difficulty":
                state["difficulty"] = 11.0
            elif damage == "unknown-state":
                state["state"] = "synthetic-invalid"
            else:
                state["due"] = "2026-10-01T00:00:00Z"
            conn.execute("UPDATE learning_events SET outcome=? WHERE event_id=?",
                         (json.dumps(outcome), original["event_id"]))
        core.start()
        history = core.request("GET", f"/api/v1/learning/events/{item}")[1]
        assert history["events"][0]["next_review"] == original["next_review"]
        assert_unverified_schedule_projection(core, item, "invalid_previous_card")
        status, backup = core.request("POST", "/api/v1/workspace/backups", {})
        assert status == 201 and backup["verified"] is True
        artifact = tmp_path / "backups" / backup["filename"]
        assert hashlib.sha256(artifact.read_bytes()).hexdigest() == backup["sha256"]
        exe = core.exe
        core.stop()
        destination = tmp_path / "invalid-card-restore"
        destination.mkdir()
        restored = subprocess.run([str(exe), "--maintenance-restore", str(destination / "workspace.sqlite"),
                                   str(artifact)], capture_output=True, text=True, timeout=120, check=False)
        assert restored.returncode == 0 and json.loads(restored.stdout)["ok"] is True
        from scripts.ci.real_core_grading_journey import Core
        core = Core(exe, destination, Path(sys.executable))
        core.start()
        assert core.request("GET", f"/api/v1/learning/events/{item}")[1] == history
        assert_unverified_schedule_projection(core, item, "invalid_previous_card")
        status, blocked = core.request("POST", "/api/v1/learning/reviews", {
            "item_key": item, "client_event_id": "after-invalid-card", "correct": True,
            "rating": 3, "now": "2026-09-03T00:00:00Z"})
        assert status == 201 and blocked["schedule_authority"] == "unavailable"
        assert blocked["schedule_recovery"]["reason"] == "invalid_previous_card"
        status, reset = core.request("POST", "/api/v1/learning/reviews", {
            "item_key": item, "client_event_id": "explicit-invalid-card-reset", "correct": True,
            "rating": 3, "now": "2026-09-04T00:00:00Z",
            "schedule_reset": {"mode": "start_new", "reason": "Synthetic human reset",
                               "expected_latest_event_id": blocked["event_id"]}})
        assert status == 201 and reset["schedule_authority"] == "fsrs"
        core.stop()
        core.start()
        status, state = core.request("GET", f"/api/v1/learning/items/{item}/state")
        assert status == 200 and state["learner"]["next_review"] == reset["next_review"]
        assert "schedule_integrity" not in state["learner"]
        assert core.request("GET", f"/api/v1/learning/events/{item}")[1]["events"][0] == history["events"][0]
    finally:
        core.stop()


@pytest.mark.parametrize("invalid_reset", [False, True])
def test_earlier_invalid_card_survives_later_card_restart_restore_and_reset(tmp_path, monkeypatch, invalid_reset):
    item = "synthetic-prior-invalid-card"
    monkeypatch.setenv("ARCHEAXIS_PYTHON", str(Path(sys.executable).resolve()))
    core = core_for(tmp_path)
    try:
        core.start()
        status, first = core.request("POST", "/api/v1/learning/reviews", {
            "item_key": item, "client_event_id": "first-card", "correct": True,
            "rating": 3, "now": "2026-09-01T00:00:00Z"})
        assert status == 201 and first["schedule_authority"] == "fsrs"
        second_request = {"item_key": item, "client_event_id": "second-card", "correct": True,
                          "rating": 3, "now": "2026-09-02T00:00:00Z"}
        if invalid_reset:
            second_request["schedule_reset"] = {"mode": "start_new", "reason": "Synthetic earlier reset",
                                                "expected_latest_event_id": first["event_id"]}
        status, second = core.request("POST", "/api/v1/learning/reviews", second_request)
        assert status == 201 and second["schedule_authority"] == "fsrs"
        status, third = core.request("POST", "/api/v1/learning/reviews", {
            "item_key": item, "client_event_id": "later-card", "correct": True,
            "rating": 3, "now": "2026-09-03T00:00:00Z"})
        assert status == 201 and third["schedule_authority"] == "fsrs"
        core.stop()
        # Reproduce a historical state corruption only in this isolated fixture.
        with sqlite3.connect(tmp_path / "workspace.sqlite") as conn:
            (raw,) = conn.execute("SELECT outcome FROM learning_events WHERE event_id=?",
                                  (second["event_id"],)).fetchone()
            damaged = json.loads(raw)
            damaged["schedule"]["state"].pop("stability")
            conn.execute("UPDATE learning_events SET outcome=? WHERE event_id=?",
                         (json.dumps(damaged), second["event_id"]))
        core.start()
        history = core.request("GET", f"/api/v1/learning/events/{item}")[1]
        assert len(history["events"]) == 3 and history["events"][-1]["next_review"] == third["next_review"]
        assert_unverified_schedule_projection(core, item, "invalid_previous_card")
        status, backup = core.request("POST", "/api/v1/workspace/backups", {})
        assert status == 201 and backup["verified"] is True
        artifact = tmp_path / "backups" / backup["filename"]
        assert hashlib.sha256(artifact.read_bytes()).hexdigest() == backup["sha256"]
        exe = core.exe
        core.stop()
        destination = tmp_path / "prior-invalid-restore"
        destination.mkdir()
        restored = subprocess.run([str(exe), "--maintenance-restore", str(destination / "workspace.sqlite"),
                                   str(artifact)], capture_output=True, text=True, timeout=120, check=False)
        assert restored.returncode == 0 and json.loads(restored.stdout)["ok"] is True
        from scripts.ci.real_core_grading_journey import Core
        core = Core(exe, destination, Path(sys.executable))
        core.start()
        assert core.request("GET", f"/api/v1/learning/events/{item}")[1] == history
        assert_unverified_schedule_projection(core, item, "invalid_previous_card")
        status, blocked = core.request("POST", "/api/v1/learning/reviews", {
            "item_key": item, "client_event_id": "after-prior-invalid", "correct": True,
            "rating": 3, "now": "2026-09-04T00:00:00Z"})
        assert status == 201 and blocked["schedule_authority"] == "unavailable"
        assert blocked["schedule_recovery"]["reason"] == "invalid_previous_card"
        status, reset = core.request("POST", "/api/v1/learning/reviews", {
            "item_key": item, "client_event_id": "new-explicit-baseline", "correct": True,
            "rating": 3, "now": "2026-09-05T00:00:00Z",
            "schedule_reset": {"mode": "start_new", "reason": "Synthetic human reset",
                               "expected_latest_event_id": blocked["event_id"]}})
        assert status == 201 and reset["schedule_authority"] == "fsrs"
        core.stop()
        core.start()
        status, state = core.request("GET", f"/api/v1/learning/items/{item}/state")
        assert status == 200 and state["learner"]["next_review"] == reset["next_review"]
        assert "schedule_integrity" not in state["learner"]
        assert core.request("GET", f"/api/v1/learning/events/{item}")[1]["events"][:3] == history["events"]
    finally:
        core.stop()
