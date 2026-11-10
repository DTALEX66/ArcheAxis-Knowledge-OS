"""A synthetic correction journey through an actual Core process and restore.

The worker and the human decisions are fixtures. This checks persistence,
authorization and distinct task identities, not model quality or learning.
"""

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.skipif(not os.environ.get("AAOS_TEST_CORE_EXE"), reason="explicit real Core binary required")
def test_correction_retest_and_independent_task_survive_restore(tmp_path):
    from scripts.ci.real_core_grading_journey import Core

    original_text = "Synthetic laboratory marker is BETA."
    corrected_text = "CORRECTED synthetic rule: laboratory marker is BETA."
    question = "What is the synthetic laboratory marker?"
    independent_question = "Which marker applies to a new synthetic sample?"
    purpose = "synthetic correction and independent task"
    worker = tmp_path / "synthetic_answer.py"
    worker.write_text(
        "import json, sys\n"
        "from pathlib import Path\n"
        "context = Path(sys.argv[1]).read_text(encoding='utf-8')\n"
        "count = Path(__file__).with_suffix('.count')\n"
        "count.write_text(str(int(count.read_text()) + 1) if count.exists() else '1')\n"
        "answer = 'BETA' if context.startswith('CORRECTED ') else 'ALPHA'\n"
        "print(json.dumps({'answer': answer, 'model': 'synthetic-worker', "
        "'loss_receipt': {'params': {'authority': 'candidate'}}}))\n",
        encoding="utf-8",
    )

    class TestCore(Core):
        with_machine = True

        def _launch_document(self):
            launch = super()._launch_document()
            if self.with_machine:
                launch["text_worker"]["routes"].append({"capability": "machine.answer", "script": str(worker)})
            return launch

    core = TestCore(Path(os.environ["AAOS_TEST_CORE_EXE"]), tmp_path, Path(sys.executable))

    def call(method, path, body=None, expected=200, token=None):
        status, value = core.request(method, path, body, token=token)
        assert status == expected, (method, path, status, value)
        return value

    def snapshot(document):
        return {key: document[key] for key in ("document_id", "version", "content_sha256")}

    def grant(knowledge_id, title):
        document = call("POST", "/api/v1/documents", {"title": title, "editor_json": {
            "type": "doc", "content": [], "attrs": {"archeaxis_context_grant": {
                "schema": "archeaxis.context-grant/v1", "purpose": purpose,
                "consumer": "local-machine", "operations": ["answer", "retest"],
                "knowledge_id": knowledge_id, "provenance": [],
                "authorization_basis": "synthetic fixture", "expires_at": None, "state": "granted"}}}},
            expected=201)
        return {**snapshot(document), "purpose": purpose}

    def calls():
        count = worker.with_suffix(".count")
        return int(count.read_text()) if count.exists() else 0

    try:
        core.start()
        original = call("POST", "/api/v1/knowledge-items", {"knowledge_type": "FACTUAL_CLAIM",
            "body": original_text, "status": "accepted", "created_by": "synthetic fixture"}, expected=201)
        old_id = original["knowledge_id"]
        old_grant = grant(old_id, "Synthetic original grant")
        before_request = {"client_request_id": "synthetic-correction-original", "knowledge_id": old_id,
            "question": question, "context_grant": old_grant}
        before = call("POST", "/api/v1/machine/answers", before_request)
        independent_before_request = {**before_request, "client_request_id": "synthetic-independent-before",
            "question": independent_question}
        independent_before = call("POST", "/api/v1/machine/answers", independent_before_request)
        assert before["answer"]["answer"] == independent_before["answer"]["answer"] == "ALPHA"
        assert before["request"]["context_sha256"] == hashlib.sha256(original_text.encode()).hexdigest()
        assert calls() == 2

        correction_request = {"answer_id": before["answer_id"], "knowledge_id": old_id,
            "question": question, "machine_answer": "ALPHA", "corrected_answer": corrected_text,
            "error_note": "synthetic fixture answer differs from the supplied marker", "reviewer": "synthetic fixture"}
        call("POST", "/api/v1/machine/corrections", correction_request, expected=403, token=core.machine_token)
        correction = call("POST", "/api/v1/machine/corrections", correction_request)
        assert call("POST", "/api/v1/machine/corrections", correction_request) == correction
        candidate_id = correction["correction_candidate_id"]
        assert correction["answer_id"] == before["answer_id"] and correction["authority"] == "candidate"
        retest_request = {"retest_of": correction["failed_task_id"], "knowledge_id": candidate_id,
            "question": question}
        call("POST", "/api/v1/machine/retests", {**retest_request, "question": independent_question}, expected=409)
        call("POST", "/api/v1/machine/retests", retest_request, expected=404)
        call("POST", f"/api/v1/knowledge-items/{candidate_id}/review-decisions", {
            "action": "accepted", "reviewer": "synthetic fixture"})
        corrected_grant = grant(candidate_id, "Synthetic corrected grant")
        call("POST", "/api/v1/machine/retests", retest_request, expected=403)
        retest_request["context_grant"] = corrected_grant
        retest = call("POST", "/api/v1/machine/retests", retest_request)
        independent_after_request = {"client_request_id": "synthetic-independent-after", "knowledge_id": candidate_id,
            "question": independent_question, "context_grant": corrected_grant}
        independent_after = call("POST", "/api/v1/machine/answers", independent_after_request)
        assert retest["prior"]["conditions"]["answer_id"] == before["answer_id"]
        assert retest["prior"]["conditions"]["correction"] == correction
        assert retest["retest_of"] == correction["failed_task_id"]
        assert retest["answer"]["answer"] == independent_after["answer"]["answer"] == "BETA"
        expected_hash = hashlib.sha256(corrected_text.encode()).hexdigest()
        assert retest["execution_request"]["context_sha256"] == expected_hash
        assert independent_after["request"]["context_sha256"] == expected_hash
        ids = [before["answer_id"], independent_before["answer_id"], retest["retest_task_id"],
               independent_after["answer_id"]]
        assert len(set(ids)) == 4 and calls() == 4
        assert call("POST", "/api/v1/machine/retests", retest_request) == retest
        assert call("POST", "/api/v1/machine/answers", independent_after_request) == independent_after
        assert calls() == 4
        saved_tasks = [call("GET", f"/api/v1/machine/tasks/{task_id}") for task_id in ids]

        core.stop()
        core.with_machine = False
        core.start()
        assert core.request("GET", "/api/v1/capabilities/machine.answer")[0] == 404
        assert call("POST", "/api/v1/machine/retests", retest_request) == retest
        assert call("POST", "/api/v1/machine/answers", independent_after_request) == independent_after
        assert [call("GET", f"/api/v1/machine/tasks/{task_id}") for task_id in ids] == saved_tasks
        assert calls() == 4
        backup = call("POST", "/api/v1/workspace/backups", {}, expected=201)
        assert backup["verified"] is True
        preview = call("POST", "/api/v2/workspace/restore/preview", {
            "backup_id": backup["backup_id"], "expected_sha256": backup["sha256"]})
        assert preview["verified"] is True
        core.stop()
        assert Path(backup["filename"]).name == backup["filename"]
        artifact = tmp_path / "backups" / backup["filename"]
        assert hashlib.sha256(artifact.read_bytes()).hexdigest() == backup["sha256"]
        restored_dir = tmp_path / "independent-restore"
        restored_dir.mkdir()
        restored = subprocess.run([str(core.exe), "--maintenance-restore", str(restored_dir / "workspace.sqlite"),
            str(artifact)], capture_output=True, text=True, timeout=120, check=False)
        receipt = json.loads(restored.stdout) if restored.stdout else {}
        assert restored.returncode == 0 and receipt.get("ok") is True
        assert receipt.get("authorization_requires_new_grants") is True
        core = TestCore(Path(os.environ["AAOS_TEST_CORE_EXE"]), restored_dir, Path(sys.executable))
        core.with_machine = False
        core.start()
        assert [call("GET", f"/api/v1/machine/tasks/{task_id}") for task_id in ids] == saved_tasks
        call("POST", "/api/v1/machine/retests", retest_request, expected=403)
        call("POST", "/api/v1/machine/answers", independent_after_request, expected=403)
        fresh_grant = grant(candidate_id, "Synthetic post-restore grant")
        core.stop()
        core.with_machine = True
        core.start()
        fresh_retest = call("POST", "/api/v1/machine/retests", {**retest_request, "context_grant": fresh_grant})
        assert fresh_retest["retest_task_id"] != retest["retest_task_id"]
        assert fresh_retest["prior"]["conditions"]["correction"] == correction
        assert fresh_retest["answer"]["answer"] == "BETA" and calls() == 5
    finally:
        core.stop()
