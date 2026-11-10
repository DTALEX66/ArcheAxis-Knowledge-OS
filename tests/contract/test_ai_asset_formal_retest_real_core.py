"""Synthetic asset revision and formal AI retest through an actual Core process.

The default worker is a deterministic fixture. Set AAOS_TEST_ASSET_RETEST_REAL_MODEL=1
to use the existing local model route. Neither mode establishes answer quality or
human judgment. The workspace, grants, correction and material are all synthetic.
"""
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.skipif(not os.environ.get("AAOS_TEST_CORE_EXE"), reason="explicit real Core binary required")
def test_asset_correction_formal_retest_and_restore(tmp_path):
    from scripts.ci.real_core_grading_journey import Core
    from scripts.probes.aaos_ai_reference_observation_smoke import (
        BASE,
        MODEL,
        WORKER,
        canonical,
        digest,
    )
    from scripts.probes.aaos_ai_reference_observation_smoke import request as bounded_request

    real_model = os.environ.get("AAOS_TEST_ASSET_RETEST_REAL_MODEL") == "1"
    core_exe = Path(os.environ["AAOS_TEST_CORE_EXE"]).resolve(strict=True)
    core_sha = hashlib.sha256(core_exe.read_bytes()).hexdigest()
    if expected := os.environ.get("AAOS_TEST_CORE_SHA256"):
        assert core_sha == expected.lower()
    worker_path = WORKER
    calls = tmp_path / "synthetic_worker.calls"
    if real_model:
        assert not any(os.environ.get(key, "").strip() for key in
                       ("ARCHEAXIS_MACHINE_ENDPOINT", "ARCHEAXIS_MACHINE_MODEL", "ARCHEAXIS_MACHINE_PROTOCOL"))
        spec = importlib.util.spec_from_file_location("formal_retest_machine_worker", WORKER)
        worker = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(worker)
        lanes = worker._declared_lanes()
        assert len(lanes) == 1 and lanes[0]["base"] == BASE and lanes[0]["model"] == MODEL
        assert lanes[0]["protocol"] == "openai"
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(BASE + "/models", timeout=5) as response:
            inventory = json.load(response)
        assert MODEL in {row.get("id") for row in inventory.get("data", []) if isinstance(row, dict)}
    else:
        worker_path = tmp_path / "synthetic_worker.py"
        worker_path.write_text(
            "import hashlib,json,sys\n"
            "from pathlib import Path\n"
            "context=Path(sys.argv[1]).read_bytes()\n"
            "with Path(__file__).with_suffix('.calls').open('a',encoding='utf-8') as f:\n"
            " f.write(json.dumps({'context_sha256':hashlib.sha256(context).hexdigest()})+'\\n')\n"
            "print(json.dumps({'answer':'SYNTHETIC fixture answer','model':'synthetic/local'}))\n",
            encoding="utf-8",
        )

    class TestCore(Core):
        with_machine = True

        def _launch_document(self):
            launch = super()._launch_document()
            if self.with_machine:
                launch["text_worker"]["routes"].append({"capability": "machine.answer", "script": str(worker_path)})
            return launch

    source_dir = tmp_path / "source"
    source_dir.mkdir()
    core = TestCore(core_exe, source_dir, Path(sys.executable))
    purpose = "synthetic formal asset retest"
    question = "Repeat the synthetic knowledge briefly."
    corrected_text = "Synthetic fixture: the revised example colour is green."

    def snapshot(value):
        return {key: value[key] for key in ("document_id", "version", "content_sha256")}

    def call(method, path, body=None, expected=200, timeout=20):
        status, value = bounded_request(core, method, path, body, timeout=timeout)
        assert status == expected, (method, path, status, value)
        return value

    def document(title, namespace, content):
        return call("POST", "/api/v1/documents", {"title": title, "editor_json": {
            "type": "doc", "content": [], "attrs": {namespace: content}}}, expected=201)

    def asset_grant(asset, consumer, operations):
        return document("Synthetic asset grant", "archeaxis_asset_context_grant", {
            "schema": "archeaxis.asset-context-grant/v1", "asset": snapshot(asset), "purpose": purpose,
            "consumer": consumer, "operations": operations, "authorization_basis": "synthetic fixture",
            "expires_at": None, "state": "granted"})

    def knowledge_grant(knowledge_id, operations):
        return document("Synthetic knowledge grant", "archeaxis_context_grant", {
            "schema": "archeaxis.context-grant/v1", "purpose": purpose, "consumer": "local-machine",
            "operations": operations, "knowledge_id": knowledge_id, "provenance": [],
            "authorization_basis": "synthetic fixture", "expires_at": None, "state": "granted"})

    def asset_request(request_id, asset, grant, consumer, operation):
        return {"request_id": request_id, "asset": snapshot(asset), "grant": snapshot(grant),
                "purpose": purpose, "consumer": consumer, "operation": operation,
                "reference_observation_mode": "document_versions_v1"}

    def adopt(candidate, rubric):
        editor = candidate["editor_json"]
        metadata = editor["attrs"]["archeaxis_ai_asset"]
        metadata["state"] = "adopted"
        metadata["review"] = {"asset": snapshot(candidate), "rubric": snapshot(rubric),
            "reviewer": "synthetic fixture", "basis": "synthetic", "outcome": "passed",
            "judgments": [{"criterion_id": "fit", "outcome": "passed", "basis": "synthetic"}]}
        return call("PUT", f"/api/v1/documents/{candidate['document_id']}/draft", {
            "expected_version": candidate["version"], "editor_json": editor})

    def fake_calls():
        return [json.loads(line) for line in calls.read_text(encoding="utf-8").splitlines()] if calls.exists() else []

    try:
        core.start()
        source = call("POST", "/api/v1/documents", {"title": "Synthetic source", "editor_json": {
            "type": "doc", "content": []}}, expected=201)
        source_ref = {"kind": "document", "document_id": source["document_id"], "version": 1, "block_id": None}
        original = call("POST", "/api/v1/knowledge-items", {"knowledge_type": "FACTUAL_CLAIM",
            "body": "Synthetic fixture: the example colour is blue.", "status": "accepted",
            "created_by": "synthetic fixture"}, expected=201)
        original_ref = {"kind": "knowledge", "knowledge_id": original["knowledge_id"]}
        rubric = call("POST", "/api/v1/machine/rubrics", {"schema": "archeaxis.machine-rubric/v1",
            "request_id": "formal_retest_rubric", "title": "Synthetic rubric", "purpose": purpose,
            "sources": [], "criteria": [{"criterion_id": "fit", "label": "fit", "expectation": "fixture"}]}, expected=201)
        base_metadata = {"schema": "archeaxis.ai-asset/v1", "kind": "rule", "content": "Synthetic old asset",
            "purpose": purpose, "scope": [source_ref], "provenance": [original_ref], "expires_at": None,
            "state": "candidate", "members": [], "conflicts": [], "revises": None, "review": None,
            "source_payload": None}
        candidate = document("Synthetic original asset", "archeaxis_ai_asset", base_metadata)
        old_asset = adopt(candidate, rubric)
        old_machine_grant = asset_grant(old_asset, "local-machine", ["answer"])
        old_knowledge_grant = knowledge_grant(original["knowledge_id"], ["answer"])
        original_request = {"client_request_id": "formal_retest_first_answer", "knowledge_id": original["knowledge_id"],
            "question": question, "max_tokens": 4096, "timeout_s": 120,
            "context_grant": {**snapshot(old_knowledge_grant), "purpose": purpose},
            "asset_context_grant": asset_request("formal_retest_old_asset", old_asset, old_machine_grant,
                                                  "local-machine", "answer")}
        answer = call("POST", "/api/v1/machine/answers", original_request, timeout=150)
        assert answer["answer_id"] and answer["answer"]["answer"].strip()
        if real_model:
            assert answer["answer"]["requested_model"] == answer["answer"]["observed_model"] == MODEL
            assert answer["answer"]["finish_reason"] == "stop" and answer["answer"]["truncated"] is False
        else:
            assert len(fake_calls()) == 1
            assert fake_calls()[0]["context_sha256"] == answer["request"]["context_sha256"]

        source_v2 = call("PUT", f"/api/v1/documents/{source['document_id']}/draft", {"expected_version": 1,
            "editor_json": {"type": "doc", "content": [{"type": "paragraph", "content": [
                {"type": "text", "text": "Synthetic source revision"}]}]}})
        correction = call("POST", "/api/v1/machine/corrections", {"answer_id": answer["answer_id"],
            "knowledge_id": original["knowledge_id"], "question": question,
            "machine_answer": answer["answer"]["answer"], "corrected_answer": corrected_text,
            "error_note": "Synthetic fixture marks the first answer for correction without assessing quality",
            "reviewer": "synthetic fixture"})
        corrected_id = correction["correction_candidate_id"]
        assert correction["status"] == "candidate" and corrected_id != original["knowledge_id"]
        accepted = call("POST", f"/api/v1/knowledge-items/{corrected_id}/review-decisions", {
            "action": "accepted", "reviewer": "synthetic fixture"})
        assert accepted["knowledge_id"] == corrected_id
        successor = call("POST", f"/api/v1/knowledge-items/{original['knowledge_id']}/review-decisions", {
            "action": "modified", "reviewer": "synthetic fixture", "new_body": corrected_text})
        call("POST", f"/api/v1/knowledge-items/{successor['knowledge_id']}/review-decisions", {
            "action": "accepted", "reviewer": "synthetic fixture"})
        old_manual_grant = asset_grant(old_asset, "manual-context-packet", ["read_packet"])
        old_packet = call("POST", "/api/v1/ai/context-packets", asset_request(
            "formal_retest_historical_packet", old_asset, old_manual_grant, "manual-context-packet", "read_packet"))
        old_states = old_packet["packet"]["items"][0]["reference_states"]
        assert old_states[0]["reference"] == source_ref and old_states[0]["version_relation"] == "historical"
        assert old_states[1]["reference"] == original_ref and old_states[1]["currentness"] == "superseded"
        assert old_states[1]["superseded_by"] == successor["knowledge_id"]

        current_ref = {**source_ref, "version": source_v2["version"]}
        successor_ref = {"kind": "knowledge", "knowledge_id": successor["knowledge_id"]}
        corrected_ref = {"kind": "knowledge", "knowledge_id": corrected_id}
        corrected_metadata = {**base_metadata, "content": "Synthetic corrected asset", "scope": [current_ref],
                              "provenance": [successor_ref, corrected_ref], "revises": snapshot(old_asset)}
        corrected_candidate = document("Synthetic corrected asset", "archeaxis_ai_asset", corrected_metadata)
        provisional = asset_grant(corrected_candidate, "manual-context-packet", ["read_packet"])
        call("POST", "/api/v1/ai/context-packets", asset_request(
            "formal_retest_unadopted", corrected_candidate, provisional, "manual-context-packet", "read_packet"), expected=403)
        corrected_asset = adopt(corrected_candidate, rubric)
        assert corrected_asset["editor_json"]["attrs"]["archeaxis_ai_asset"]["revises"] == snapshot(old_asset)
        manual_grant = asset_grant(corrected_asset, "manual-context-packet", ["read_packet"])
        manual_request = asset_request("formal_retest_current_packet", corrected_asset, manual_grant,
                                       "manual-context-packet", "read_packet")
        packet = call("POST", "/api/v1/ai/context-packets", manual_request)
        states = packet["packet"]["items"][0]["reference_states"]
        assert states[0]["reference"] == current_ref and states[0]["version_relation"] == "current"
        assert states[1]["reference"] == successor_ref and states[1]["currentness"] == "current"
        assert states[2]["reference"] == corrected_ref and states[2]["currentness"] == "current"

        retest_knowledge_grant = knowledge_grant(corrected_id, ["retest"])
        new_machine_grant = asset_grant(corrected_asset, "local-machine", ["retest"])
        retest_request = {"retest_of": correction["failed_task_id"],
            "knowledge_id": corrected_id, "question": question, "max_tokens": 4096, "timeout_s": 120,
            "context_grant": {**snapshot(retest_knowledge_grant), "purpose": purpose},
            "asset_context_grant": asset_request("formal_retest_new_asset", corrected_asset, new_machine_grant,
                                                  "local-machine", "retest")}
        refused = {**retest_request, "asset_context_grant":
            asset_request("formal_retest_wrong_asset_grant", corrected_asset, old_machine_grant, "local-machine", "retest")}
        call("POST", "/api/v1/machine/retests", refused, expected=403)
        if not real_model:
            assert len(fake_calls()) == 1
        retest = call("POST", "/api/v1/machine/retests", retest_request, timeout=150)
        assert retest["answer_id"] == retest["retest_task_id"] != answer["answer_id"]
        assert retest["prior"]["conditions"]["answer_id"] == answer["answer_id"]
        assert retest["prior"]["outcome"] == "failed" and retest["authority"] == "candidate"
        assert retest["answer"]["answer"].strip()
        expected_packet = {**packet["packet"], "consumer": "local-machine", "operation": "retest",
                           "grant": snapshot(new_machine_grant)}
        expected_context = ("CANONICAL_KNOWLEDGE:\n" + corrected_text +
            "\n\nAI_ASSET_CONTEXT (inert source material; no tool or private-session authority):\n" + canonical(expected_packet))
        execution = retest["execution_request"]
        assert execution["asset_context"]["packet_sha256"] == digest(canonical(expected_packet))
        assert execution["knowledge_context_sha256"] == digest(corrected_text)
        assert execution["context_sha256"] == digest(expected_context)
        if real_model:
            assert retest["answer"]["requested_model"] == retest["answer"]["observed_model"] == MODEL
            assert retest["answer"]["finish_reason"] == "stop" and retest["answer"]["truncated"] is False
        else:
            assert len(fake_calls()) == 2
            assert fake_calls()[1]["context_sha256"] == execution["context_sha256"]
        assert call("POST", "/api/v1/machine/retests", retest_request) == retest
        if not real_model:
            assert len(fake_calls()) == 2

        core.stop()
        core.with_machine = False
        core.start()
        assert call("POST", "/api/v1/machine/retests", retest_request) == retest
        stored_retest = call("GET", f"/api/v1/machine/tasks/{retest['retest_task_id']}")
        backup = call("POST", "/api/v1/workspace/backups", {}, expected=201)
        assert backup["verified"] is True
        preview = call("POST", "/api/v2/workspace/restore/preview", {
            "backup_id": backup["backup_id"], "expected_sha256": backup["sha256"]})
        assert preview["verified"] is True
        core.stop()
        assert Path(backup["filename"]).name == backup["filename"]
        artifact = source_dir / "backups" / backup["filename"]
        assert hashlib.sha256(artifact.read_bytes()).hexdigest() == backup["sha256"]
        restored_dir = tmp_path / "restored"
        restored_dir.mkdir()
        restore = subprocess.run([str(core_exe), "--maintenance-restore", str(restored_dir / "workspace.sqlite"), str(artifact)],
                                 capture_output=True, text=True, timeout=120, check=False)
        restored_receipt = json.loads(restore.stdout) if restore.stdout else {}
        assert restore.returncode == 0 and restored_receipt.get("ok") is True
        assert restored_receipt.get("authorization_requires_new_grants") is True
        core = TestCore(core_exe, restored_dir, Path(sys.executable))
        core.with_machine = False
        core.start()
        assert call("GET", f"/api/v1/machine/tasks/{retest['retest_task_id']}") == stored_retest
        saved_asset = call("GET", f"/api/v1/documents/{corrected_asset['document_id']}")
        assert saved_asset["editor_json"]["attrs"]["archeaxis_ai_asset"]["revises"] == snapshot(old_asset)
        saved_old_asset = call("GET", f"/api/v1/documents/{old_asset['document_id']}")
        assert snapshot(saved_old_asset) == snapshot(old_asset)
        call("POST", "/api/v1/machine/retests", retest_request, expected=403)
        call("POST", "/api/v1/ai/context-packets", manual_request, expected=403)
        restored_grant = asset_grant(corrected_asset, "manual-context-packet", ["read_packet"])
        restored_packet = call("POST", "/api/v1/ai/context-packets", asset_request(
            "formal_retest_restored_packet", corrected_asset, restored_grant, "manual-context-packet", "read_packet"))
        restored_states = restored_packet["packet"]["items"][0]["reference_states"]
        assert restored_states[0]["reference"] == current_ref and restored_states[0]["version_relation"] == "current"
        assert restored_states[1]["reference"] == successor_ref and restored_states[1]["currentness"] == "current"
        assert restored_states[2]["reference"] == corrected_ref and restored_states[2]["currentness"] == "current"
        restored_knowledge_grant = knowledge_grant(corrected_id, ["retest"])
        restored_machine_grant = asset_grant(corrected_asset, "local-machine", ["retest"])
        old_asset_only = {**retest_request,
            "context_grant": {**snapshot(restored_knowledge_grant), "purpose": purpose},
            "asset_context_grant": asset_request("formal_retest_fenced_old_asset", corrected_asset,
                                                  new_machine_grant, "local-machine", "retest")}
        old_knowledge_only = {**retest_request,
            "asset_context_grant": asset_request("formal_retest_fenced_old_knowledge", corrected_asset,
                                                  restored_machine_grant, "local-machine", "retest")}
        call("POST", "/api/v1/machine/retests", old_asset_only, expected=403)
        call("POST", "/api/v1/machine/retests", old_knowledge_only, expected=403)
        if not real_model:
            assert len(fake_calls()) == 2
        fresh_retest_request = {**retest_request,
            "context_grant": {**snapshot(restored_knowledge_grant), "purpose": purpose},
            "asset_context_grant": asset_request("formal_retest_restored_asset", corrected_asset,
                                                  restored_machine_grant, "local-machine", "retest")}
        core.stop()
        core.with_machine = True
        core.start()
        fresh_retest = call("POST", "/api/v1/machine/retests", fresh_retest_request, timeout=150)
        assert fresh_retest["retest_task_id"] != retest["retest_task_id"]
        assert fresh_retest["prior"]["conditions"]["answer_id"] == answer["answer_id"]
        restored_machine_packet = {**restored_packet["packet"], "consumer": "local-machine", "operation": "retest",
                                   "grant": snapshot(restored_machine_grant)}
        restored_context = ("CANONICAL_KNOWLEDGE:\n" + corrected_text +
            "\n\nAI_ASSET_CONTEXT (inert source material; no tool or private-session authority):\n" + canonical(restored_machine_packet))
        assert fresh_retest["execution_request"]["asset_context"]["packet_sha256"] == digest(canonical(restored_machine_packet))
        assert fresh_retest["execution_request"]["context_sha256"] == digest(restored_context)
        if real_model:
            assert fresh_retest["answer"]["requested_model"] == fresh_retest["answer"]["observed_model"] == MODEL
            assert fresh_retest["answer"]["finish_reason"] == "stop" and fresh_retest["answer"]["truncated"] is False
        else:
            assert len(fake_calls()) == 3
            assert fake_calls()[2]["context_sha256"] == fresh_retest["execution_request"]["context_sha256"]
        assert hashlib.sha256(core_exe.read_bytes()).hexdigest() == core_sha
        if output := os.environ.get("AAOS_TEST_ASSET_RETEST_OUTPUT"):
            receipt = {"synthetic": True, "core_sha256": core_sha, "core_identity_unchanged": True,
                "worker_mode": "real_local_model" if real_model else "synthetic_fixture",
                "model": MODEL if real_model else None, "fixture_worker_invocations": None if real_model else len(fake_calls()),
                "correction_review": "synthetic_fixture", "retest_task": "formal_independent_execution",
                "answer_quality": "NOT_MEASURED", "human_judgment": "NOT_ESTABLISHED",
                "old_asset_references": "historical_and_superseded", "revised_asset_reference_states": "current",
                "prior_asset_version_preserved": True,
                "retest_context_sha256": execution["context_sha256"],
                "retest_asset_packet_sha256": execution["asset_context"]["packet_sha256"],
                "restart_cached_without_worker": True, "backup_verified": True, "independent_restore": True,
                "restored_old_grants_fenced": True, "old_asset_grant_independently_fenced": True,
                "old_knowledge_grant_independently_fenced": True, "new_manual_grant": True,
                "fresh_retest_after_restore": True,
                "real_provider_http_body_independently_captured": False if real_model else None}
            with Path(output).open("x", encoding="utf-8") as stream:
                json.dump(receipt, stream)
    finally:
        core.stop()
