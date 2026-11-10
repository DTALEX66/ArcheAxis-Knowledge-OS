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


@pytest.mark.parametrize("assessed", [False, True])
def test_downgrade_cannot_hide_an_unreplayed_outage_review(tmp_path, monkeypatch, assessed):
    """A later old-Core FSRS card must not make an earlier outage disappear."""
    old = verified_core("AAOS_TEST_PREVIOUS_CORE_EXE", "AAOS_TEST_PREVIOUS_CORE_SHA256")
    new = verified_core("AAOS_TEST_CORE_EXE", "AAOS_TEST_CORE_SHA256")
    assert hashlib.sha256(old.read_bytes()).digest() != hashlib.sha256(new.read_bytes()).digest()
    good_python = str(Path(sys.executable).resolve())
    monkeypatch.setenv("ARCHEAXIS_PYTHON", good_python)
    monkeypatch.setenv("ARCHEAXIS_SCHEDULER_WORKER", str(ROOT / "services/python-workers/learning/worker_schedule.py"))
    original = tmp_path / "source"
    original.mkdir()
    item = "synthetic-x2-gap"
    active = Core(new, original, Path(sys.executable))
    try:
        active.start()
        binding = {}
        if assessed:
            status, knowledge = active.request("POST", "/api/v1/knowledge-items", {
                "knowledge_type": "FACTUAL_CLAIM", "body": "Synthetic assessed fact",
                "status": "accepted", "created_by": "fixture"})
            assert status == 201
            base = f"/api/v1/learning/items/{item}"
            status, _ = active.request("POST", base + "/references", {"knowledge_id": knowledge["knowledge_id"]})
            assert status == 201
            status, assessment = active.request("POST", base + "/assessment", {"knowledge_id": knowledge["knowledge_id"]})
            assert status == 201
            binding = {"assessment_id": assessment["assessment_id"], "knowledge_version": assessment["knowledge_version"]}
        status, initial = active.request("POST", "/api/v1/learning/reviews", {
            "item_key": item, "client_event_id": "initial", "correct": True, **binding,
            "rating": 3, "now": "2026-09-01T00:00:00Z"})
        assert status == 201 and initial["schedule_authority"] == "fsrs"
        active.stop()
        monkeypatch.setenv("ARCHEAXIS_PYTHON", str(tmp_path / "missing-python"))
        active = Core(new, original, Path(sys.executable))
        active.start()
        status, missed = active.request("POST", "/api/v1/learning/reviews", {
            "item_key": item, "client_event_id": "outage", "correct": False, **binding,
            "rating": 1, "now": "2026-09-02T00:00:00Z"})
        assert status == 201 and missed["schedule_authority"] == "unavailable"
        before = events(active, item)
        status, backup = active.request("POST", "/api/v1/workspace/backups", {})
        assert status == 201 and backup["verified"] is True
        artifact = original / "backups" / backup["filename"]
        assert hashlib.sha256(artifact.read_bytes()).hexdigest() == backup["sha256"]
        active.stop()
        control, downgrade = tmp_path / "control", tmp_path / "downgrade"
        restore(new, artifact, control)
        restore(new, artifact, downgrade)
        monkeypatch.setenv("ARCHEAXIS_PYTHON", good_python)
        follow = {"item_key": item, "client_event_id": "follow", "correct": True, **binding,
                  "rating": 3, "now": "2026-09-03T00:00:00Z"}
        active = Core(new, control, Path(sys.executable))
        active.start()
        assert events(active, item) == before
        status, expected = active.request("POST", "/api/v1/learning/reviews", follow)
        assert status == 201 and expected["schedule_authority"] == "fsrs"
        assert expected["schedule_recovery"]["state"] == "replayed"
        assert expected["schedule_recovery"]["through_event_id"] == missed["event_id"]
        active.stop()
        active = Core(old, downgrade, Path(sys.executable))
        active.start()
        assert events(active, item) == before
        status, ignored_gap = active.request("POST", "/api/v1/learning/reviews", follow)
        assert status == 201 and ignored_gap["schedule_authority"] == "fsrs"
        assert ignored_gap["schedule_state"] != expected["schedule_state"]
        old_history = events(active, item)
        assert "recovery" not in json.loads(old_history[-1]["outcome"])["schedule"]
        active.stop()
        active = Core(new, downgrade, Path(sys.executable))
        active.start()
        assert events(active, item) == old_history
        status, state = active.request("GET", f"/api/v1/learning/items/{item}/state")
        assert status == 200 and state["learner"]["next_review"] is None
        assert state["learner"]["latest_review"]["next_review"] is None
        integrity = {"state": "unverified", "reason": "scheduled_gap_replay_unverified"}
        assert state["learner"]["schedule_integrity"] == integrity
        if assessed:
            assert state["learner"]["assessment_progress"]["latest_review"]["next_review"] is None
        status, queue = active.request("GET", "/api/v1/learning/items")
        assert status == 200
        queued = next(row for row in queue["items"] if row["item_key"] == item)
        assert queued["next_review"] is None and queued["schedule_integrity"] == integrity
        assert events(active, item) == old_history
        after_body = {"item_key": item, "client_event_id": "after-upgrade", "correct": True, **binding,
                      "rating": 3, "now": "2026-09-04T00:00:00Z"}
        status, after = active.request("POST", "/api/v1/learning/reviews", after_body)
        assert status == 201
        assert after["schedule_authority"] == "unavailable", after
        assert after["schedule_recovery"]["reason"] == "scheduled_gap_replay_unverified"
        preserved = events(active, item)
        assert len(preserved) == 4 and preserved[:3] == old_history
        status, replay = active.request("POST", "/api/v1/learning/reviews", after_body)
        assert status == 200 and replay["duplicate"] is True
        assert replay["event_id"] == after["event_id"] and replay["schedule_authority"] == "unavailable"
        status, unscheduled_state = active.request("GET", f"/api/v1/learning/items/{item}/state")
        assert status == 200 and unscheduled_state["learner"]["next_review"] is None
        assert unscheduled_state["learner"]["schedule_integrity"] == integrity
        status, unscheduled_queue = active.request("GET", "/api/v1/learning/items")
        assert status == 200
        queued = next(row for row in unscheduled_queue["items"] if row["item_key"] == item)
        assert queued["next_review"] is None and queued["schedule_integrity"] == integrity
        reset_body = {"item_key": item, "client_event_id": "recover-gap", "correct": True, **binding, "rating": 3,
            "now": "2026-09-05T00:00:00Z", "schedule_reset": {"mode": "start_new",
            "reason": "Synthetic explicit reset", "expected_latest_event_id": after["event_id"]}}
        status, reset = active.request("POST", "/api/v1/learning/reviews", reset_body)
        assert status == 201 and reset["schedule_authority"] == "fsrs"
        assert reset["schedule_recovery"]["excluded_through_event_id"] == after["event_id"]
        active.stop()
        active = Core(new, downgrade, Path(sys.executable))
        active.start()
        status, retry_reset = active.request("POST", "/api/v1/learning/reviews", reset_body)
        assert status == 200 and retry_reset["duplicate"] is True and retry_reset["event_id"] == reset["event_id"]
        assert events(active, item)[:4] == preserved
        status, resumed = active.request("POST", "/api/v1/learning/reviews", {
            "item_key": item, "client_event_id": "after-explicit-reset", "correct": True, **binding,
            "rating": 3, "now": "2026-09-06T00:00:00Z"})
        assert status == 201 and resumed["schedule_authority"] == "fsrs"
        assert resumed["schedule_recovery"]["baseline_reset_event_id"] == reset["event_id"]
        status, resumed_state = active.request("GET", f"/api/v1/learning/items/{item}/state")
        assert status == 200 and resumed_state["learner"]["next_review"] == resumed["next_review"]
        assert "schedule_integrity" not in resumed_state["learner"]
        status, resumed_queue = active.request("GET", "/api/v1/learning/items")
        queued = next(row for row in resumed_queue["items"] if row["item_key"] == item)
        assert status == 200 and queued["next_review"] == resumed["next_review"]
        assert "schedule_integrity" not in queued
    finally:
        active.stop()
