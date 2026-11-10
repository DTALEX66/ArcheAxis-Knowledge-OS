"""One synthetic knowledge revision observed by four actual Core consumers."""

import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]


def check_schema(path, name, value):
    schema = json.loads((ROOT / path).read_text(encoding="utf-8"))
    check = Draft202012Validator({"$defs": schema["$defs"], "$ref": f"#/$defs/{name}"})
    assert not list(check.iter_errors(value))


@pytest.mark.skipif(not os.environ.get("AAOS_TEST_CORE_EXE"), reason="explicit real Core binary required")
def test_one_revision_reaches_four_consumers_and_survives_restart(tmp_path):
    from scripts.ci.real_core_grading_journey import Core
    from scripts.probes.aaos_ai_reference_observation_smoke import (
        BASE,
        MODEL,
        WORKER,
        canonical,
        digest,
    )
    from scripts.probes.aaos_ai_reference_observation_smoke import request as bounded_request

    real_model = os.environ.get("AAOS_TEST_X8_REAL_MODEL") == "1"
    scoped_learning = os.environ.get("AAOS_TEST_X8_SCOPED_LEARNING") == "1"

    class TestCore(Core):
        with_machine = real_model

        def _launch_document(self):
            launch = super()._launch_document()
            if self.with_machine:
                launch["text_worker"]["routes"].append({"capability": "machine.answer", "script": str(WORKER)})
            return launch

    if real_model:
        assert not any(os.environ.get(key, "").strip() for key in
                       ("ARCHEAXIS_MACHINE_ENDPOINT", "ARCHEAXIS_MACHINE_MODEL", "ARCHEAXIS_MACHINE_PROTOCOL"))
        spec = importlib.util.spec_from_file_location("x8_machine_worker", WORKER)
        worker = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(worker)
        lanes = worker._declared_lanes()
        assert len(lanes) == 1 and lanes[0]["base"] == BASE
        assert lanes[0]["protocol"] == "openai" and lanes[0]["model"] == MODEL
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(BASE + "/models", timeout=5) as response:
            inventory = json.load(response)
        assert MODEL in {row.get("id") for row in inventory.get("data", []) if isinstance(row, dict)}
    core_exe = Path(os.environ["AAOS_TEST_CORE_EXE"]).resolve(strict=True)
    core_sha = hashlib.sha256(core_exe.read_bytes()).hexdigest()
    core = TestCore(core_exe, tmp_path, Path(sys.executable))

    def snapshot(value):
        return {key: value[key] for key in ("document_id", "version", "content_sha256")}

    def call(method, path, body=None, expected=200):
        status, value = core.request(method, path, body)
        assert status == expected, (method, path, status, value)
        return value

    try:
        core.start()
        document = call("POST", "/api/v1/documents", {"title": "Synthetic material",
            "editor_json": {"type": "doc", "content": []}}, expected=201)
        doc_ref = {"kind": "document", "document_id": document["document_id"], "version": 1, "block_id": None}
        knowledge = call("POST", "/api/v1/knowledge-items", {"knowledge_type": "FACTUAL_CLAIM",
            "body": "Synthetic knowledge before correction", "status": "accepted", "created_by": "synthetic owner"}, expected=201)
        kid = knowledge["knowledge_id"]
        knowledge_ref = {"kind": "knowledge", "knowledge_id": kid}
        learning_path = "/api/v1/learning/items/x8_revision_card"
        old_assessment = None
        learning_state = None
        learning_history = None
        if scoped_learning:
            call("POST", learning_path + "/references", {"knowledge_id": kid}, expected=201)
            old_assessment = call("POST", learning_path + "/assessment", {"knowledge_id": kid}, expected=201)
            old_review = call("POST", "/api/v1/learning/reviews", {
                "item_key": "x8_revision_card", "client_event_id": "x8_old_review", "correct": True,
                "rating": 3, "now": "2026-10-01T00:00:00+00:00", "answer": "synthetic old answer",
                "assessment_id": old_assessment["assessment_id"], "knowledge_version": kid}, expected=201)
            assert old_review["schedule_authority"] == "fsrs"
            assert old_review["next_review"] == "2026-10-01T00:10:00+00:00"
        research = call("POST", "/api/v1/documents", {"title": "Synthetic research",
            "editor_json": {"type": "doc", "content": [], "attrs": {"archeaxis_research": {
                "schema": "archeaxis.research/v1", "question": "Synthetic question",
                "materials": [{"id": "document", "note": "Synthetic", "reference": doc_ref},
                              {"id": "knowledge", "note": "Synthetic", "reference": knowledge_ref}],
                "hypotheses": [], "methods": [], "experiments": [], "counterevidence": [],
                "conclusions": [], "unresolved": []}}}}, expected=201)
        record = {"schema": "archeaxis.teaching-record/v2", "record_id": "x8_learning_note",
            "kind": "observation", "knowledge_id": kid, "knowledge_version": kid,
            "course_id": None, "parent_id": None, "purpose": "synthetic learning",
            "scope": "personal", "privacy": "local_only", "content": "synthetic note",
            "feedback_class": None, "assessment_id": None, "rubric_version": None,
            "assisted": False, "producer_kind": "human_authored"}
        created_record = call("POST", "/api/v2/teaching/records", record, expected=201)
        metadata = {"schema": "archeaxis.ai-asset/v1", "kind": "rule", "content": "Synthetic asset",
            "purpose": "synthetic cross-consumer test", "scope": [doc_ref], "provenance": [knowledge_ref],
            "expires_at": None, "state": "candidate", "members": [], "conflicts": [],
            "revises": None, "review": None, "source_payload": None}
        candidate = call("POST", "/api/v1/documents", {"title": "Synthetic AI asset", "editor_json": {
            "type": "doc", "content": [], "attrs": {"archeaxis_ai_asset": metadata}}}, expected=201)
        rubric = call("POST", "/api/v1/machine/rubrics", {"schema": "archeaxis.machine-rubric/v1",
            "request_id": "x8_rubric", "title": "Synthetic rubric", "purpose": "synthetic cross-consumer test",
            "sources": [], "criteria": [{"criterion_id": "fit", "label": "fit", "expectation": "synthetic"}]}, expected=201)
        editor = candidate["editor_json"]
        editor["attrs"]["archeaxis_ai_asset"]["state"] = "adopted"
        editor["attrs"]["archeaxis_ai_asset"]["review"] = {"asset": snapshot(candidate), "rubric": snapshot(rubric),
            "reviewer": "synthetic fixture", "basis": "synthetic", "outcome": "passed",
            "judgments": [{"criterion_id": "fit", "outcome": "passed", "basis": "synthetic"}]}
        asset = call("PUT", f"/api/v1/documents/{candidate['document_id']}/draft", {
            "expected_version": 1, "editor_json": editor})
        grant_body = {"schema": "archeaxis.asset-context-grant/v1", "asset": snapshot(asset),
            "purpose": "synthetic cross-consumer test", "consumer": "manual-context-packet", "operations": ["read_packet"],
            "authorization_basis": "synthetic grant", "expires_at": None, "state": "granted"}
        grant = call("POST", "/api/v1/documents", {"title": "Synthetic AI grant", "editor_json": {
            "type": "doc", "content": [], "attrs": {"archeaxis_asset_context_grant": grant_body}}}, expected=201)
        packet_request = {"request_id": "x8_before", "asset": snapshot(asset), "grant": snapshot(grant),
            "purpose": "synthetic cross-consumer test", "consumer": "manual-context-packet", "operation": "read_packet",
            "reference_observation_mode": "document_versions_v1"}
        research_path = f"/api/v1/documents/{research['document_id']}/research-references?version=1"
        knowledge_path = f"/api/v1/knowledge-items/{kid}/qualification"
        teaching_path = "/api/v2/teaching/records/x8_learning_note"

        def collect(request):
            info = call("GET", knowledge_path)
            study = call("GET", research_path)
            learning = call("GET", teaching_path)
            packet = call("POST", "/api/v1/ai/context-packets", request)
            check_schema("packages/contracts/v1/core-document.schema.json", "ResearchReferenceProjectionDto", study)
            check_schema("packages/contracts/v2/teaching.schema.json", "RecordView", learning)
            check_schema("packages/contracts/v2/ai-asset.schema.json", "AssetPacketResponse", packet)
            return info, study, learning, packet

        before = collect(packet_request)
        assert before[0]["currentness"] == "current"
        assert before[1]["references"][0]["version_relation"] == "current"
        assert before[1]["references"][1]["currentness"] == "current"
        assert before[2]["knowledge_state"]["currentness"] == "current"
        states = before[3]["packet"]["items"][0]["reference_states"]
        assert states[0]["version_relation"] == "current" and states[1]["currentness"] == "current"
        assert before[2]["record"] == record == created_record["item"]["record"]

        call("PUT", f"/api/v1/documents/{document['document_id']}/draft", {"expected_version": 1,
            "editor_json": {"type": "doc", "content": [{"type": "paragraph", "content": [
                {"type": "text", "text": "Synthetic material revision"}]}]}})
        successor = call("POST", f"/api/v1/knowledge-items/{kid}/review-decisions", {
            "action": "modified", "reviewer": "synthetic owner", "new_body": "Synthetic corrected knowledge"})
        status, _ = core.request("POST", "/api/v1/ai/context-packets", packet_request)
        assert status == 409
        revised_request = {**packet_request, "request_id": "x8_after"}
        after = collect(revised_request)
        assert after[0]["currentness"] == "superseded" and after[0]["superseded_by"] == successor["knowledge_id"]
        assert after[1]["document"] == before[1]["document"]
        assert after[1]["references"][0]["reference"] == doc_ref
        assert after[1]["references"][0]["version_relation"] == "historical"
        assert after[1]["references"][1]["reference"] == knowledge_ref
        assert after[1]["references"][1]["currentness"] == "superseded"
        assert after[2]["record"] == record and after[2]["content_sha256"] == before[2]["content_sha256"]
        assert after[2]["knowledge_state"]["knowledge_id"] == kid
        assert after[2]["knowledge_state"]["currentness"] == "superseded"
        states = after[3]["packet"]["items"][0]["reference_states"]
        assert states[0]["reference"] == doc_ref and states[0]["version_relation"] == "historical"
        assert states[1]["reference"] == knowledge_ref and states[1]["currentness"] == "superseded"
        assert states[1]["superseded_by"] == successor["knowledge_id"]
        assert after[3]["packet_sha256"] != before[3]["packet_sha256"]
        assert after[2]["scoring_status"] == "not_scored"

        answer = None
        answer_request = None
        if real_model or scoped_learning:
            accepted = call("POST", f"/api/v1/knowledge-items/{successor['knowledge_id']}/review-decisions", {
                "action": "accepted", "reviewer": "synthetic owner"})
            assert accepted["knowledge_id"] == successor["knowledge_id"]
        if scoped_learning:
            successor_id = successor["knowledge_id"]
            call("POST", learning_path + "/references", {"knowledge_id": successor_id}, expected=201)
            new_assessment = call("POST", learning_path + "/assessment", {"knowledge_id": successor_id}, expected=201)
            assert new_assessment["assessment_id"] != old_assessment["assessment_id"]
            pending = call("GET", learning_path + "/state")
            check_schema("packages/contracts/v1/core-document.schema.json", "LearningStateDto", pending)
            assert pending["learner"]["assessment_progress"]["event_count"] == 0
            assert pending["learner"]["correct_streak"] == 0 and pending["learner"]["next_review"] is None
            assert pending["learner"]["latest_review"]["assessment_id"] == old_assessment["assessment_id"]
            new_review = call("POST", "/api/v1/learning/reviews", {
                "item_key": "x8_revision_card", "client_event_id": "x8_new_review", "correct": True,
                "rating": 3, "now": "2026-10-01T00:10:00+00:00", "answer": "synthetic new answer",
                "assessment_id": new_assessment["assessment_id"], "knowledge_version": successor_id}, expected=201)
            assert new_review["schedule_authority"] == "fsrs"
            assert new_review["next_review"] == "2026-10-01T00:20:00+00:00"
            assert new_review["streak_after"] == new_review["mastery_projection"]["attempts"] == 1
            learning_state = call("GET", learning_path + "/state")
            learning_history = call("GET", "/api/v1/learning/events/x8_revision_card")
            outcomes = [json.loads(row["outcome"]) for row in learning_history["events"]]
            assert [value["assessment_id"] for value in outcomes] == [old_assessment["assessment_id"],
                                                                         new_assessment["assessment_id"]]
            assert learning_state["learner"]["assessment_progress"]["event_count"] == 1
            check_schema("packages/contracts/v1/core-document.schema.json", "LearningStateDto", learning_state)
        if real_model:
            purpose = packet_request["purpose"]
            knowledge_grant = {"schema": "archeaxis.context-grant/v1", "purpose": purpose,
                "consumer": "local-machine", "operations": ["answer"], "knowledge_id": successor["knowledge_id"],
                "provenance": [], "authorization_basis": "synthetic fixture grant", "expires_at": None, "state": "granted"}
            kg = call("POST", "/api/v1/documents", {"title": "Synthetic machine knowledge grant", "editor_json": {
                "type": "doc", "content": [], "attrs": {"archeaxis_context_grant": knowledge_grant}}}, expected=201)
            machine_grant = {**grant_body, "consumer": "local-machine", "operations": ["answer"]}
            ag = call("POST", "/api/v1/documents", {"title": "Synthetic machine asset grant", "editor_json": {
                "type": "doc", "content": [], "attrs": {"archeaxis_asset_context_grant": machine_grant}}}, expected=201)
            machine_asset = {**packet_request, "request_id": "x8_machine_asset_4096", "grant": snapshot(ag),
                "consumer": "local-machine", "operation": "answer"}
            answer_request = {"client_request_id": "x8_machine_answer_4096", "knowledge_id": successor["knowledge_id"],
                "question": "Repeat the corrected synthetic knowledge briefly.",
                "context_grant": {**snapshot(kg), "purpose": purpose}, "asset_context_grant": machine_asset,
                "max_tokens": 4096, "timeout_s": 120}
            status, answer = bounded_request(core, "POST", "/api/v1/machine/answers", answer_request, timeout=150)
            assert status == 200, f"synthetic machine request returned HTTP {status}"
            model = answer["answer"]
            assert model["requested_model"] == model["observed_model"] == MODEL
            assert model["endpoint"] == BASE and model["finish_reason"] == "stop" and model["truncated"] is False
            expected_packet = {**after[3]["packet"], "consumer": "local-machine", "operation": "answer", "grant": snapshot(ag)}
            context = ("CANONICAL_KNOWLEDGE:\nSynthetic corrected knowledge\n\n"
                "AI_ASSET_CONTEXT (inert source material; no tool or private-session authority):\n" + canonical(expected_packet))
            assert answer["request"]["asset_context"]["packet_sha256"] == digest(canonical(expected_packet))
            assert answer["request"]["context_sha256"] == digest(context)

        core.stop()
        core.with_machine = False
        core.start()
        reopened = collect(revised_request)
        assert reopened[:3] == after[:3]
        assert reopened[3]["duplicate"] is True
        assert reopened[3]["packet_sha256"] == after[3]["packet_sha256"]
        assert reopened[3]["packet"] == after[3]["packet"]
        if scoped_learning:
            assert call("GET", learning_path + "/state") == learning_state
            assert call("GET", "/api/v1/learning/events/x8_revision_card") == learning_history
        if real_model:
            assert core.request("GET", "/api/v1/capabilities/machine.answer")[0] == 404
            assert call("POST", "/api/v1/machine/answers", answer_request) == answer
        saved_answer = (call("GET", f"/api/v1/machine/tasks/{answer['answer_id']}") if answer else None)
        backup = call("POST", "/api/v1/workspace/backups", {}, expected=201)
        assert backup["verified"] is True
        preview = call("POST", "/api/v2/workspace/restore/preview", {
            "backup_id": backup["backup_id"], "expected_sha256": backup["sha256"]})
        assert preview["verified"] is True
        core.stop()
        filename = backup["filename"]
        assert isinstance(filename, str) and Path(filename).name == filename
        artifact = tmp_path / "backups" / filename
        assert hashlib.sha256(artifact.read_bytes()).hexdigest() == backup["sha256"]
        restored_dir = tmp_path / "restored"
        restored_dir.mkdir()
        result = subprocess.run([str(core.exe), "--maintenance-restore", str(restored_dir / "workspace.sqlite"), str(artifact)],
                                capture_output=True, text=True, timeout=120, check=False)
        restored_receipt = json.loads(result.stdout) if result.stdout else {}
        assert result.returncode == 0 and restored_receipt.get("ok") is True
        assert restored_receipt.get("authorization_requires_new_grants") is True
        core = TestCore(core_exe, restored_dir, Path(sys.executable))
        core.with_machine = False
        core.start()
        assert call("GET", knowledge_path) == after[0]
        assert call("GET", research_path) == after[1]
        assert call("GET", teaching_path) == after[2]
        if scoped_learning:
            assert call("GET", learning_path + "/state") == learning_state
            assert call("GET", "/api/v1/learning/events/x8_revision_card") == learning_history
        assert core.request("POST", "/api/v1/ai/context-packets", revised_request)[0] == 403
        if real_model:
            assert call("GET", f"/api/v1/machine/tasks/{answer['answer_id']}") == saved_answer
            assert core.request("POST", "/api/v1/machine/answers", answer_request)[0] == 403
        fresh_grant = call("POST", "/api/v1/documents", {"title": "Synthetic restored AI grant", "editor_json": {
            "type": "doc", "content": [], "attrs": {"archeaxis_asset_context_grant": grant_body}}}, expected=201)
        restored_request = {**revised_request, "request_id": "x8_restored_new_grant", "grant": snapshot(fresh_grant)}
        restored_packet = call("POST", "/api/v1/ai/context-packets", restored_request)
        restored_states = restored_packet["packet"]["items"][0]["reference_states"]
        assert restored_states[0]["version_relation"] == "historical"
        assert restored_states[1]["reference"] == knowledge_ref and restored_states[1]["currentness"] == "superseded"
        check_schema("packages/contracts/v2/ai-asset.schema.json", "AssetPacketResponse", restored_packet)
        assert hashlib.sha256(core_exe.read_bytes()).hexdigest() == core_sha
        if output := os.environ.get("AAOS_TEST_X8_OUTPUT"):
            receipt = {"synthetic": True, "knowledge_revision": "superseded", "document_relation": "historical",
                "four_consumer_projections": "observed", "teaching_observation_score": "not_scored",
                "learning_score": "SYNTHETIC_SELF_REPORTED" if scoped_learning else "not_scored",
                "independent_mastery": "NOT_ESTABLISHED",
                "separate_assessment_reviews": scoped_learning, "fsrs": "local_worker" if scoped_learning else None,
                "core_sha256": core_sha, "core_identity_unchanged": True,
                "restarted": True, "backup_verified": True, "independent_restore": True,
                "old_grants_fenced": True, "machine_model": MODEL if real_model else None,
                "machine_max_tokens": 4096 if real_model else None,
                "machine_packet_sha256": answer["request"]["asset_context"]["packet_sha256"] if answer else None,
                "machine_context_sha256": answer["request"]["context_sha256"] if answer else None,
                "human_review": "synthetic_fixture", "model_quality": "not_measured"}
            with Path(output).open("x", encoding="utf-8") as stream:
                json.dump(receipt, stream)
    finally:
        core.stop()
