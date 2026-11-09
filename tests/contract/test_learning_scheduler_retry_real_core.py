"""Synthetic retry checks against the real Core and local FSRS worker."""

import hashlib
import importlib.util
import json
import os
import sqlite3
import subprocess
import sys
import threading
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
    marker = tmp_path / "concurrent-scheduler-calls.txt"
    worker = tmp_path / "synchronized_scheduler.py"
    worker.write_text(
        "import os, runpy, time\n"
        "marker=os.environ['AAOS_TEST_SCHEDULER_MARKER']\n"
        "with open(marker, 'a', encoding='utf-8') as out: out.write('call\\n')\n"
        "deadline=time.monotonic()+8\n"
        "while time.monotonic()<deadline:\n"
        "    with open(marker, encoding='utf-8') as source: count=len(source.readlines())\n"
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
        assert marker.read_text(encoding="utf-8").splitlines() == ["call", "call"]
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


def test_invalid_recovery_card_remains_unscheduled_and_can_recover_later(tmp_path, monkeypatch):
    core = core_for(tmp_path)
    worker = tmp_path / "invalid_recovery_scheduler.py"
    worker.write_text(
        "import json\n"
        "print(json.dumps({'authority':'fsrs','next_review_days':1,'due':'2026-10-02T00:00:00Z',"
        "'state':'review','step':None,'stability':None,'difficulty':5.0,'last_review':'2026-09-02T00:00:00Z'}))\n",
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
        assert second["schedule_recovery"]["reason"] == "invalid_recovered_card"
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
    marker = tmp_path / "recovery-race-calls.txt"
    worker = tmp_path / "recovery_race_scheduler.py"
    worker.write_text(
        "import io,json,os,runpy,sys,time\n"
        "raw=sys.stdin.read(); rating=json.loads(raw)['rating']\n"
        "marker=os.environ['AAOS_TEST_SCHEDULER_MARKER']\n"
        "with open(marker,'a',encoding='utf-8') as out: out.write('call\\n')\n"
        "with open(marker,encoding='utf-8') as source: count=len(source.readlines())\n"
        "if count<=2:\n"
        "    deadline=time.monotonic()+8\n"
        "    while time.monotonic()<deadline:\n"
        "        with open(marker,encoding='utf-8') as source: total=len(source.readlines())\n"
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
        assert len(marker.read_text(encoding="utf-8").splitlines()) == 4
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
        "request=json.load(sys.stdin)\n"
        "with open(os.environ['AAOS_TEST_SCHEDULER_MARKER'],'a',encoding='utf-8') as out:\n"
        "    out.write(json.dumps(request['state'])+'\\n')\n"
        "print(json.dumps({'authority':'fsrs','next_review_days':1,'due':'2026-10-02T00:00:00+00:00',"
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
