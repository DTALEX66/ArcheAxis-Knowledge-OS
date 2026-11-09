"""A pinned historical Core and current Core share one synthetic FSRS journey.

The historical executable must be selected explicitly: the 422 expectation
is for a Core predating schedule_reset, not a promise about every old release.
Both processes use the same checked-out worker; this is not an installed test.
"""

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.ci.real_core_grading_journey import Core

ROOT = Path(__file__).resolve().parents[2]
REQUIRED = ("AAOS_TEST_CORE_EXE", "AAOS_TEST_CORE_SHA256", "AAOS_TEST_PREVIOUS_CORE_EXE",
            "AAOS_TEST_PREVIOUS_CORE_SHA256")
pytestmark = pytest.mark.skipif(
    any(not os.environ.get(name) for name in REQUIRED),
    reason="explicit current and historical Core binaries and their SHA-256 are required",
)


def verified_core(path_name, hash_name):
    path = Path(os.environ[path_name]).resolve(strict=True)
    assert hashlib.sha256(path.read_bytes()).hexdigest() == os.environ[hash_name].lower()
    return path


def restore(exe, artifact, destination):
    destination.mkdir()
    result = subprocess.run(
        [str(exe), "--maintenance-restore", str(destination / "workspace.sqlite"), str(artifact)],
        capture_output=True, text=True, timeout=120, check=False,
    )
    assert result.returncode == 0, result.stderr
    result_json = json.loads(result.stdout)
    assert result_json["ok"] is True
    assert result_json["authorization_requires_new_grants"] is True


def events(core, item):
    status, history = core.request("GET", f"/api/v1/learning/events/{item}")
    assert status == 200
    return history["events"]


def test_pinned_core_upgrade_restore_downgrade_and_schedule_control(tmp_path, monkeypatch):
    old = verified_core("AAOS_TEST_PREVIOUS_CORE_EXE", "AAOS_TEST_PREVIOUS_CORE_SHA256")
    new = verified_core("AAOS_TEST_CORE_EXE", "AAOS_TEST_CORE_SHA256")
    assert hashlib.sha256(old.read_bytes()).digest() != hashlib.sha256(new.read_bytes()).digest()
    monkeypatch.setenv("ARCHEAXIS_PYTHON", str(Path(sys.executable).resolve()))
    monkeypatch.setenv("ARCHEAXIS_SCHEDULER_WORKER", str(ROOT / "services/python-workers/learning/worker_schedule.py"))
    original = tmp_path / "source"
    original.mkdir()
    item = "synthetic-x2"
    first_body = {"item_key": item, "client_event_id": "old-review", "correct": True,
                  "rating": 3, "now": "2026-09-01T00:00:00Z"}
    follow_body = {"item_key": item, "client_event_id": "after-reset", "correct": True,
                   "rating": 3, "now": "2026-09-03T00:00:00Z"}
    document_body = {"title": "Synthetic compatibility document", "editor_json": {"type": "doc",
        "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Synthetic material."}]}]}}
    active = Core(old, original, Path(sys.executable))
    try:
        active.start()
        status, document = active.request("POST", "/api/v1/documents", document_body)
        assert status == 201
        status, first = active.request("POST", "/api/v1/learning/reviews", first_body)
        assert status == 201 and first["schedule_authority"] == "fsrs"
        old_history = events(active, item)
        assert len(old_history) == 1
        active.stop()

        active = Core(new, original, Path(sys.executable))
        active.start()
        assert events(active, item) == old_history
        status, retry = active.request("POST", "/api/v1/learning/reviews", first_body)
        assert status == 200 and retry["duplicate"] is True and retry["event_id"] == first["event_id"]
        reset_body = {"item_key": item, "client_event_id": "reset", "correct": True, "rating": 3,
            "now": "2026-09-02T00:00:00Z", "schedule_reset": {"mode": "start_new",
            "reason": "Synthetic baseline", "expected_latest_event_id": first["event_id"]}}
        status, reset = active.request("POST", "/api/v1/learning/reviews", reset_body)
        assert status == 201 and reset["schedule_authority"] == "fsrs"
        before = events(active, item)
        assert len(before) == 2
        status, backup = active.request("POST", "/api/v1/workspace/backups", {})
        assert status == 201 and backup["verified"] is True
        assert Path(backup["filename"]).name == backup["filename"]
        artifact = original / "backups" / backup["filename"]
        assert hashlib.sha256(artifact.read_bytes()).hexdigest() == backup["sha256"]
        active.stop()

        control = tmp_path / "control"
        downgrade = tmp_path / "downgrade"
        restore(new, artifact, control)
        restore(new, artifact, downgrade)
        active = Core(new, control, Path(sys.executable))
        active.start()
        assert events(active, item) == before
        status, control_review = active.request("POST", "/api/v1/learning/reviews", follow_body)
        assert status == 201 and control_review["schedule_authority"] == "fsrs"
        control_history = events(active, item)
        control_schedule = json.loads(control_history[-1]["outcome"])["schedule"]
        assert control_schedule["recovery"]["baseline_reset_event_id"] == reset["event_id"]
        active.stop()

        active = Core(old, downgrade, Path(sys.executable))
        active.start()
        assert events(active, item) == before
        status, old_state = active.request("GET", f"/api/v1/learning/items/{item}/state")
        assert status == 200 and "schedule_recovery" not in old_state["learner"]["latest_review"]
        status, _ = active.request("POST", "/api/v1/learning/reviews", reset_body)
        assert status == 422
        assert events(active, item) == before
        status, older_review = active.request("POST", "/api/v1/learning/reviews", follow_body)
        assert status == 201 and older_review["schedule_authority"] == "fsrs"
        old_after = events(active, item)
        old_schedule = json.loads(old_after[-1]["outcome"])["schedule"]
        assert "recovery" not in old_schedule
        assert older_review["next_review"] == control_review["next_review"]
        assert old_schedule["state"] == control_schedule["state"]
        active.stop()

        active = Core(new, downgrade, Path(sys.executable))
        active.start()
        assert events(active, item) == old_after
        status, replay = active.request("POST", "/api/v1/learning/reviews", reset_body)
        assert status == 200 and replay["duplicate"] is True and replay["event_id"] == reset["event_id"]
        status, last = active.request("POST", "/api/v1/learning/reviews", {
            "item_key": item, "client_event_id": "new-after-downgrade", "correct": True,
            "rating": 3, "now": "2026-09-04T00:00:00Z"})
        assert status == 201 and last["schedule_authority"] == "fsrs"
        assert last["schedule_recovery"]["baseline_reset_event_id"] == reset["event_id"]
        status, saved = active.request("GET", "/api/v1/documents/" + document["document_id"])
        assert status == 200 and saved["content_sha256"] == document["content_sha256"]
    finally:
        active.stop()
