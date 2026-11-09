"""Synthetic review isolation through a real Core and the local FSRS worker."""

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator


@pytest.mark.skipif(not os.environ.get("AAOS_TEST_CORE_EXE"), reason="explicit real Core binary required")
def test_revision_starts_fresh_schedule_and_survives_restore(tmp_path):
    from scripts.ci.real_core_grading_journey import Core

    core_exe = Path(os.environ["AAOS_TEST_CORE_EXE"]).resolve(strict=True)
    core_sha = hashlib.sha256(core_exe.read_bytes()).hexdigest()
    core = Core(core_exe, tmp_path, Path(sys.executable))
    schema_path = Path(__file__).resolve().parents[2] / "packages/contracts/v1/core-document.schema.json"
    definitions = json.loads(schema_path.read_text(encoding="utf-8"))["$defs"]
    check_state = Draft202012Validator({"$defs": definitions, "$ref": "#/$defs/LearningStateDto"})
    item = "synthetic-revision-card"
    base = f"/api/v1/learning/items/{item}"

    def call(method, path, body=None, expected=200):
        status, result = core.request(method, path, body)
        assert status == expected, (method, path, status, result)
        return result

    def review(assessment, request_id, now):
        return {"item_key": item, "client_event_id": request_id, "correct": True, "rating": 3,
            "now": now, "answer": "synthetic learner answer", "assessment_id": assessment["assessment_id"],
            "knowledge_version": assessment["knowledge_version"]}

    try:
        core.start()
        original = call("POST", "/api/v1/knowledge-items", {"knowledge_type": "FACTUAL_CLAIM",
            "body": "Synthetic old lesson", "status": "accepted", "created_by": "fixture"}, expected=201)
        old_id = original["knowledge_id"]
        call("POST", base + "/references", {"knowledge_id": old_id}, expected=201)
        old = call("POST", base + "/assessment", {"knowledge_id": old_id}, expected=201)
        old_review = call("POST", "/api/v1/learning/reviews", review(old, "old-review", "2026-10-01T00:00:00+00:00"), expected=201)
        assert old_review["schedule_authority"] == "fsrs"
        assert old_review["next_review"] == "2026-10-01T00:10:00+00:00"
        successor = call("POST", f"/api/v1/knowledge-items/{old_id}/review-decisions", {
            "action": "modified", "reviewer": "fixture", "new_body": "Synthetic revised lesson"})["knowledge_id"]
        call("POST", f"/api/v1/knowledge-items/{successor}/review-decisions", {"action": "accepted", "reviewer": "fixture"})
        call("POST", base + "/references", {"knowledge_id": successor}, expected=201)
        revised = call("POST", base + "/assessment", {"knowledge_id": successor}, expected=201)
        before = call("GET", base + "/state")
        assert not list(check_state.iter_errors(before))
        assert before["learner"]["assessment"]["assessment_id"] == revised["assessment_id"]
        assert before["learner"]["correct_streak"] == 0 and before["learner"]["next_review"] is None
        assert before["learner"]["latest_review"]["assessment_id"] == old["assessment_id"]
        assert before["learner"]["assessment_progress"]["event_count"] == 0
        request = review(revised, "new-review", "2026-10-01T00:10:00+00:00")
        result = call("POST", "/api/v1/learning/reviews", request, expected=201)
        assert result["schedule_authority"] == "fsrs" and result["schedule_state"]["state"] == "learning"
        assert result["schedule_state"]["step"] == 1 and result["next_review"] == "2026-10-01T00:20:00+00:00"
        assert result["streak_after"] == result["mastery_projection"]["attempts"] == 1
        history = call("GET", f"/api/v1/learning/events/{item}")
        assert history["count"] == 2
        outcomes = [json.loads(row["outcome"]) for row in history["events"]]
        assert [row["assessment_id"] for row in outcomes] == [old["assessment_id"], revised["assessment_id"]]
        state = call("GET", base + "/state")
        assert not list(check_state.iter_errors(state))
        assert state["learner"]["assessment_progress"]["event_count"] == 1
        assert state["learner"]["next_review"] == result["next_review"]
        assert next(row for row in call("GET", "/api/v1/learning/items")["items"] if row["item_key"] == item)["next_review"] == result["next_review"]
        core.stop()
        core.start()
        assert call("GET", base + "/state") == state
        replay = call("POST", "/api/v1/learning/reviews", request)
        assert replay["duplicate"] is True and replay["event_id"] == result["event_id"]
        assert call("GET", f"/api/v1/learning/events/{item}") == history
        backup = call("POST", "/api/v1/workspace/backups", {}, expected=201)
        assert backup["verified"] is True
        core.stop()
        assert Path(backup["filename"]).name == backup["filename"]
        artifact = tmp_path / "backups" / backup["filename"]
        assert hashlib.sha256(artifact.read_bytes()).hexdigest() == backup["sha256"]
        destination = tmp_path / "independent-restore"
        destination.mkdir()
        completed = subprocess.run([str(core_exe), "--maintenance-restore", str(destination / "workspace.sqlite"),
            str(artifact)], capture_output=True, text=True, timeout=120, check=False)
        receipt = json.loads(completed.stdout) if completed.stdout else {}
        assert completed.returncode == 0 and receipt.get("ok") is True
        assert receipt.get("authorization_requires_new_grants") is True
        core = Core(core_exe, destination, Path(sys.executable))
        core.start()
        assert call("GET", base + "/state") == state
        assert call("GET", f"/api/v1/learning/events/{item}") == history
        assert hashlib.sha256(core_exe.read_bytes()).hexdigest() == core_sha
    finally:
        core.stop()
