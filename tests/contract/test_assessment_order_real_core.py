"""Revision-bound assessment ordering on a real Core and isolated workspace."""

import hashlib
import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.skipif(not os.environ.get("AAOS_TEST_CORE_EXE"), reason="explicit real Core binary required")
def test_assessment_order_and_old_review_survive_restart_and_restore(tmp_path):
    from scripts.ci.real_core_grading_journey import Core

    core_exe = Path(os.environ["AAOS_TEST_CORE_EXE"]).resolve(strict=True)
    core_hash = hashlib.sha256(core_exe.read_bytes()).hexdigest()
    core = Core(core_exe, tmp_path, Path(sys.executable))
    item = "assessment-tie-1"

    def call(method, path, body=None, expected=200):
        status, result = core.request(method, path, body)
        assert status == expected, (method, path, status, result)
        return result

    item_path = f"/api/v1/learning/items/{item}"
    assessment_path = item_path + "/assessment"
    state_path = item_path + "/state"
    history_path = f"/api/v1/learning/events/{item}"
    try:
        core.start()
        original = call("POST", "/api/v1/knowledge-items", {"knowledge_type": "FACTUAL_CLAIM",
            "body": "Synthetic original fact", "status": "accepted", "created_by": "fixture"}, expected=201)
        old_id = original["knowledge_id"]
        call("POST", item_path + "/references", {"knowledge_id": old_id}, expected=201)
        old = call("POST", assessment_path, {"knowledge_id": old_id}, expected=201)
        review = call("POST", "/api/v1/learning/reviews", {"item_key": item,
            "client_event_id": "synthetic-assessment-review", "correct": False, "rating": 1,
            "now": "2026-10-01T00:00:00+00:00", "answer": "synthetic answer",
            "assessment_id": old["assessment_id"], "knowledge_version": old_id}, expected=201)
        history = call("GET", history_path)
        new_id = call("POST", f"/api/v1/knowledge-items/{old_id}/review-decisions", {
            "action": "modified", "reviewer": "fixture", "new_body": "Synthetic revised fact"})["knowledge_id"]
        call("POST", f"/api/v1/knowledge-items/{new_id}/review-decisions", {
            "action": "accepted", "reviewer": "fixture"})
        call("POST", item_path + "/references", {"knowledge_id": new_id}, expected=201)
        revised = call("POST", assessment_path, {"knowledge_id": new_id}, expected=201)
        assert old["assessment_id"] > revised["assessment_id"]
        assert old["assessment_id"] != revised["assessment_id"]
        core.stop()

        # Deterministically reproduce two legal same-second creation timestamps.
        # This is an isolated synthetic fixture and the Core is stopped.
        with sqlite3.connect(tmp_path / "workspace.sqlite") as fixture:
            fixture.execute("UPDATE learning_assessments SET created_at=? WHERE item_key=?",
                ("2026-11-09 00:00:00", item))
        core.start()

        def check():
            assessment = call("GET", assessment_path)
            assert assessment["assessment_id"] == revised["assessment_id"]
            assert assessment["knowledge_id"] == new_id
            assert assessment["knowledge_state"]["currentness"] == "current"
            state = call("GET", state_path)
            assert state["learner"]["assessment"] == assessment
            assert state["learner"]["latest_review"]["assessment_id"] == old["assessment_id"]
            assert state["learner"]["latest_review"]["event_id"] == review["event_id"]
            assert state["learner"]["event_count"] == 1
            current_history = call("GET", history_path)
            assert current_history["events"] == history["events"]
            references = {row["knowledge_id"]: row["currentness"] for row in current_history["references"]}
            assert references == {old_id: "superseded", new_id: "current"}
            items = call("GET", "/api/v1/learning/items")["items"]
            assert next(row for row in items if row["item_key"] == item)["display_title"] == "Synthetic revised fact"
            return assessment, state

        expected = check()
        core.stop()
        core.start()
        assert check() == expected
        backup = call("POST", "/api/v1/workspace/backups", {}, expected=201)
        assert backup["verified"] is True
        core.stop()
        assert Path(backup["filename"]).name == backup["filename"]
        artifact = tmp_path / "backups" / backup["filename"]
        assert hashlib.sha256(artifact.read_bytes()).hexdigest() == backup["sha256"]
        restored_dir = tmp_path / "independent-restore"
        restored_dir.mkdir()
        restored = subprocess.run([str(core_exe), "--maintenance-restore", str(restored_dir / "workspace.sqlite"),
            str(artifact)], capture_output=True, text=True, timeout=120, check=False)
        receipt = json.loads(restored.stdout) if restored.stdout else {}
        assert restored.returncode == 0 and receipt.get("ok") is True
        assert receipt.get("authorization_requires_new_grants") is True
        core = Core(core_exe, restored_dir, Path(sys.executable))
        core.start()
        assert check() == expected
        assert hashlib.sha256(core_exe.read_bytes()).hexdigest() == core_hash
    finally:
        core.stop()
