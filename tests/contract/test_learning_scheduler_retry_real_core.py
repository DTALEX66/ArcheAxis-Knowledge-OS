"""Synthetic retry checks against the real Core and local FSRS worker."""

import hashlib
import json
import os
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
