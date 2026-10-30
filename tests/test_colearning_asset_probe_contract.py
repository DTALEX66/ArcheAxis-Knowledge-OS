"""Finite asset/scoped contract: captured synthetic Core shapes, adversarial bindings.

GOLDEN contains only owned synthetic objects from the current C1/production-worker
parser fixture. It is not a real-model answer or a credential/runtime configuration.
"""
from __future__ import annotations
import copy
import importlib.util
import json
import os
from pathlib import Path
import pytest

PROBE = Path(os.environ.get("AAOS_ASSET_CANDIDATE",
    str(Path(__file__).resolve().parents[1] / "scripts/probes/colearning_asset_scoped_smoke.py")))
GOLDEN = json.loads('{"before":{"question":"Which component writes the canonical store, and is the release frozen? Return only JSON with writer (string) and frozen (boolean).","knowledge_id":"k_6408b058e19215cb776fd481","answer":{"answer":"{\\"writer\\": \\"Python\\", \\"frozen\\": true}","model":"qwen3.5-4b","engine":"python-worker-machine-answer","engine_version":"0.1.0","requested_model":"qwen3.5-4b","observed_model":"qwen3.5-4b","endpoint":"http://127.0.0.1:1234/v1","protocol":"openai","prompt_version":"archeaxis.vnext/v1 2026-10-02","answer_policy":"grounded","max_tokens":2048,"finish_reason":"stop","truncated":false},"context_authorization":{"authorization":{"authorization_basis":"explicit owned synthetic fixture use","consumer":"local-machine","expires_at":null,"knowledge_id":"k_6408b058e19215cb776fd481","operations":["answer","retest"],"provenance":[],"purpose":"finite synthetic store and release application","schema":"archeaxis.context-grant/v1","state":"granted"},"checked_at":1793378381,"content_sha256":"8da1e638efb9332c643e2c80b06ae104e8ed96fbd8633576ea57d93341a9b01a","current_permission_valid":true,"document_id":"doc_req_bd599c29542e64f7961f282bb8c318b48f2ba5a2bb427e8d63af1b44da44da97","operation":"answer","version":1},"answer_id":"answer_req_75529b4393e71f8d9554f51e85d29a02cd97da6195741eda2b37a3032a6e12a9","request":{"context_grant":{"content_sha256":"8da1e638efb9332c643e2c80b06ae104e8ed96fbd8633576ea57d93341a9b01a","document_id":"doc_req_bd599c29542e64f7961f282bb8c318b48f2ba5a2bb427e8d63af1b44da44da97","purpose":"finite synthetic store and release application","version":1},"context_sha256":"bd5825850edd147246c4d869d2d33b2546fcce84dccb0ae7ad30d87f32913575","knowledge_id":"k_6408b058e19215cb776fd481","max_tokens":2048,"question":"Which component writes the canonical store, and is the release frozen? Return only JSON with writer (string) and frozen (boolean).","schema":"archeaxis.machine-answer-request/v1","timeout_s":120},"client_request_id":"asset-answer-original-before"},"after":{"question":"Which component writes the canonical store, and is the release frozen? Return only JSON with writer (string) and frozen (boolean).","knowledge_id":"k_6408b058e19215cb776fd481","answer":{"answer":"{\\"writer\\": \\"Rust Core\\", \\"frozen\\": true}","model":"qwen3.5-4b","engine":"python-worker-machine-answer","engine_version":"0.1.0","requested_model":"qwen3.5-4b","observed_model":"qwen3.5-4b","endpoint":"http://127.0.0.1:1234/v1","protocol":"openai","prompt_version":"archeaxis.vnext/v1 2026-10-02","answer_policy":"grounded","max_tokens":2048,"finish_reason":"stop","truncated":false},"context_authorization":{"authorization":{"authorization_basis":"explicit owned synthetic fixture use","consumer":"local-machine","expires_at":null,"knowledge_id":"k_6408b058e19215cb776fd481","operations":["answer","retest"],"provenance":[],"purpose":"finite synthetic store and release application","schema":"archeaxis.context-grant/v1","state":"granted"},"checked_at":1793378382,"content_sha256":"8da1e638efb9332c643e2c80b06ae104e8ed96fbd8633576ea57d93341a9b01a","current_permission_valid":true,"document_id":"doc_req_bd599c29542e64f7961f282bb8c318b48f2ba5a2bb427e8d63af1b44da44da97","operation":"retest","version":1},"retest_task_id":"retest_03a3959244191db09615556ffc73302c","execution_request":{"asset_context":{"asset":{"content_sha256":"37b37bd45e39972eab6ab2d47dc384ecb5f5729922e9678e3eb0779d20f50729","document_id":"doc_req_8e899f5ca768d36a925c2fc7044092042fc90ea86ad9abca823a4111ce9ef8b1","version":2},"consumer":"local-machine","grant":{"content_sha256":"0d7aa1658d64ce4069b7f6a5eee0c20699f2454f79a0b3f5bb4e8c7286aa5b72","document_id":"doc_req_e8a6cb70cd714c3b8fb2e33ddc3d3c706bdef59062ebfca77856478c1327fe2a","version":1},"member_snapshots":[{"content_sha256":"37b37bd45e39972eab6ab2d47dc384ecb5f5729922e9678e3eb0779d20f50729","document_id":"doc_req_8e899f5ca768d36a925c2fc7044092042fc90ea86ad9abca823a4111ce9ef8b1","version":2},{"content_sha256":"a5a21fba4bd3e51b06f8809faff250576fd1a9749372d289aa1fbaa54fb4f1b4","document_id":"doc_req_c8e0c62a08732a1d0a1ba809a70388803577f8c978947e290d967cebf7fe971d","version":2}],"operation":"retest","packet_sha256":"5ebfd0f4bfbfa0a37f7828bd3b5a7c9d392b8b35ab9998d65cc3d24fe100c4e5","private_session_access":false,"schema":"archeaxis.machine-asset-context/v1","tool_execution":"NOT_EXECUTED"},"context_sha256":"c62c7a3596fcc9fbfe7a5400d489273e3cb35f979a2dbfc9d3ed77dcfb3b4e7f","knowledge_context_sha256":"bd5825850edd147246c4d869d2d33b2546fcce84dccb0ae7ad30d87f32913575","request":{"asset_context_grant":{"asset":{"content_sha256":"37b37bd45e39972eab6ab2d47dc384ecb5f5729922e9678e3eb0779d20f50729","document_id":"doc_req_8e899f5ca768d36a925c2fc7044092042fc90ea86ad9abca823a4111ce9ef8b1","version":2},"consumer":"local-machine","grant":{"content_sha256":"0d7aa1658d64ce4069b7f6a5eee0c20699f2454f79a0b3f5bb4e8c7286aa5b72","document_id":"doc_req_e8a6cb70cd714c3b8fb2e33ddc3d3c706bdef59062ebfca77856478c1327fe2a","version":1},"operation":"retest","purpose":"finite synthetic store and release application","request_id":"asset-use-original-retest"},"context_grant":{"content_sha256":"8da1e638efb9332c643e2c80b06ae104e8ed96fbd8633576ea57d93341a9b01a","document_id":"doc_req_bd599c29542e64f7961f282bb8c318b48f2ba5a2bb427e8d63af1b44da44da97","purpose":"finite synthetic store and release application","version":1},"knowledge_id":"k_6408b058e19215cb776fd481","max_tokens":2048,"question":"Which component writes the canonical store, and is the release frozen? Return only JSON with writer (string) and frozen (boolean).","retest_of":"evaluation_answer_req_75529b4393e71f8d9554f51e85d29a02cd97da6195741eda2b37a3032a6e12a9"},"schema":"archeaxis.machine-retest-execution/v1","timeout_s":120}},"sent_before":{"knowledge_id":"k_6408b058e19215cb776fd481","question":"Which component writes the canonical store, and is the release frozen? Return only JSON with writer (string) and frozen (boolean).","context_grant":{"content_sha256":"8da1e638efb9332c643e2c80b06ae104e8ed96fbd8633576ea57d93341a9b01a","document_id":"doc_req_bd599c29542e64f7961f282bb8c318b48f2ba5a2bb427e8d63af1b44da44da97","purpose":"finite synthetic store and release application","version":1},"max_tokens":2048,"timeout_s":120,"client_request_id":"asset-answer-original-before"},"sent_after":{"asset_context_grant":{"asset":{"content_sha256":"37b37bd45e39972eab6ab2d47dc384ecb5f5729922e9678e3eb0779d20f50729","document_id":"doc_req_8e899f5ca768d36a925c2fc7044092042fc90ea86ad9abca823a4111ce9ef8b1","version":2},"consumer":"local-machine","grant":{"content_sha256":"0d7aa1658d64ce4069b7f6a5eee0c20699f2454f79a0b3f5bb4e8c7286aa5b72","document_id":"doc_req_e8a6cb70cd714c3b8fb2e33ddc3d3c706bdef59062ebfca77856478c1327fe2a","version":1},"operation":"retest","purpose":"finite synthetic store and release application","request_id":"asset-use-original-retest"},"context_grant":{"content_sha256":"8da1e638efb9332c643e2c80b06ae104e8ed96fbd8633576ea57d93341a9b01a","document_id":"doc_req_bd599c29542e64f7961f282bb8c318b48f2ba5a2bb427e8d63af1b44da44da97","purpose":"finite synthetic store and release application","version":1},"knowledge_id":"k_6408b058e19215cb776fd481","max_tokens":2048,"question":"Which component writes the canonical store, and is the release frozen? Return only JSON with writer (string) and frozen (boolean).","retest_of":"evaluation_answer_req_75529b4393e71f8d9554f51e85d29a02cd97da6195741eda2b37a3032a6e12a9","timeout_s":120},"knowledge_grant":{"document_id":"doc_req_bd599c29542e64f7961f282bb8c318b48f2ba5a2bb427e8d63af1b44da44da97","version":1,"content_sha256":"8da1e638efb9332c643e2c80b06ae104e8ed96fbd8633576ea57d93341a9b01a","editor_json":{"attrs":{"archeaxis_context_grant":{"authorization_basis":"explicit owned synthetic fixture use","consumer":"local-machine","expires_at":null,"knowledge_id":"k_6408b058e19215cb776fd481","operations":["answer","retest"],"provenance":[],"purpose":"finite synthetic store and release application","schema":"archeaxis.context-grant/v1","state":"granted"}},"content":[],"type":"doc"}},"packet":{"asset":{"content_sha256":"37b37bd45e39972eab6ab2d47dc384ecb5f5729922e9678e3eb0779d20f50729","document_id":"doc_req_8e899f5ca768d36a925c2fc7044092042fc90ea86ad9abca823a4111ce9ef8b1","version":2},"consumer":"local-machine","grant":{"content_sha256":"0d7aa1658d64ce4069b7f6a5eee0c20699f2454f79a0b3f5bb4e8c7286aa5b72","document_id":"doc_req_e8a6cb70cd714c3b8fb2e33ddc3d3c706bdef59062ebfca77856478c1327fe2a","version":1},"human_mastery":false,"items":[{"content":"Finite inert synthetic store and release rules.","engine_execution":"NOT_EXECUTED","grants_human_mastery":false,"grants_machine_qualification":false,"grants_professional_truth":false,"kind":"knowledge_package","provenance":[],"purpose":"finite synthetic store and release application","scope":[],"snapshot":{"content_sha256":"37b37bd45e39972eab6ab2d47dc384ecb5f5729922e9678e3eb0779d20f50729","document_id":"doc_req_8e899f5ca768d36a925c2fc7044092042fc90ea86ad9abca823a4111ce9ef8b1","version":2}},{"content":"Only the Rust Core writes the SQLite canonical store. Python workers may not write it directly. The release is FROZEN pending the Owner gate; publication without that gate is not allowed.","engine_execution":"NOT_EXECUTED","grants_human_mastery":false,"grants_machine_qualification":false,"grants_professional_truth":false,"kind":"rule","provenance":[],"purpose":"finite synthetic store and release application","scope":[],"snapshot":{"content_sha256":"a5a21fba4bd3e51b06f8809faff250576fd1a9749372d289aa1fbaa54fb4f1b4","document_id":"doc_req_c8e0c62a08732a1d0a1ba809a70388803577f8c978947e290d967cebf7fe971d","version":2}}],"machine_qualification":false,"operation":"retest","private_session_access":false,"professional_truth":false,"purpose":"finite synthetic store and release application","reference_only_sources":true,"schema":"archeaxis.ai-context-packet/v1","tool_execution":"NOT_EXECUTED"},"correction":{"answer_id":"answer_req_75529b4393e71f8d9554f51e85d29a02cd97da6195741eda2b37a3032a6e12a9","authority":"candidate","corrected_answer":"Only the Rust Core writes the SQLite canonical store. Python workers may not write it directly. The release is FROZEN pending the Owner gate; publication without that gate is not allowed.","correction_candidate_id":"k_ec1b13913923c1e5ede22c59","corrects_knowledge_id":"k_6408b058e19215cb776fd481","error_note":"frozen bounded original rubric differs; no accepted knowledge rewrite","failed_task_id":"evaluation_answer_req_75529b4393e71f8d9554f51e85d29a02cd97da6195741eda2b37a3032a6e12a9","machine_answer":"{\\"writer\\": \\"Python\\", \\"frozen\\": true}","promotion":"this candidate is not knowledge until a human accepts it through review-decisions","question":"Which component writes the canonical store, and is the release frozen? Return only JSON with writer (string) and frozen (boolean).","reviewer":"scripted-human-fixture","schema":"archeaxis.machine-correction/v1","status":"candidate"},"sent_correction":{"answer_id":"answer_req_75529b4393e71f8d9554f51e85d29a02cd97da6195741eda2b37a3032a6e12a9","question":"Which component writes the canonical store, and is the release frozen? Return only JSON with writer (string) and frozen (boolean).","machine_answer":"{\\"writer\\": \\"Python\\", \\"frozen\\": true}","corrected_answer":"Only the Rust Core writes the SQLite canonical store. Python workers may not write it directly. The release is FROZEN pending the Owner gate; publication without that gate is not allowed.","reviewer":"scripted-human-fixture","error_note":"frozen bounded original rubric differs; no accepted knowledge rewrite","knowledge_id":"k_6408b058e19215cb776fd481"}}')

def module():
    spec = importlib.util.spec_from_file_location("asset_scoped_test", PROBE)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result

def bound(fixture=None):
    p = module()
    g = copy.deepcopy(GOLDEN if fixture is None else fixture)
    return p.verify_answer(g["after"], g["sent_after"], "original", g["knowledge_grant"],
                           g["packet"], retest=True)

def test_actual_synthetic_core_packet_and_scoped_retest_bind():
    result = bound()
    assert result["score"] == "CORRECT"
    assert result["packet_sha256"] == GOLDEN["after"]["execution_request"]["asset_context"]["packet_sha256"]
    assert len(result["asset_members"]) == 2

@pytest.mark.parametrize(("path", "value"), [
    (("after", "execution_request", "asset_context", "packet_sha256"), "0" * 64),
    (("after", "execution_request", "asset_context", "member_snapshots", 1, "version"), 999),
    (("after", "execution_request", "asset_context", "consumer"), "manual-context-packet"),
    (("after", "execution_request", "asset_context", "operation"), "answer"),
    (("after", "execution_request", "asset_context", "asset", "content_sha256"), "0" * 64),
    (("after", "execution_request", "asset_context", "grant", "version"), 999),
    (("after", "execution_request", "request", "asset_context_grant", "purpose"), "other"),
    (("after", "execution_request", "request", "asset_context_grant", "request_id"), "other"),
    (("after", "execution_request", "knowledge_context_sha256"), "0" * 64),
    (("after", "execution_request", "context_sha256"), "0" * 64),
    (("after", "execution_request", "timeout_s"), 119),
    (("after", "execution_request", "request", "max_tokens"), 4096),
    (("after", "question"), "different task"),
    (("after", "knowledge_id"), "different knowledge"),
    (("after", "context_authorization", "current_permission_valid"), False),
    (("after", "context_authorization", "version"), 999),
    (("after", "context_authorization", "authorization", "state"), "revoked"),
    (("after", "answer", "model"), "other-model"),
    (("after", "answer", "requested_model"), "other-model"),
    (("after", "answer", "observed_model"), "other-model"),
    (("after", "answer", "endpoint"), "http://127.0.0.1:9999/v1"),
    (("after", "answer", "prompt_version"), "changed-prompt"),
    (("after", "answer", "answer_policy"), "companion_general"),
    (("after", "answer", "max_tokens"), 4096),
    (("after", "answer", "finish_reason"), "length"),
    (("after", "answer", "truncated"), True),
    (("packet", "items", 1, "content"), "altered asset content"),
    (("packet", "purpose"), "different purpose"),
])
def test_rejects_changed_identity_material_authorization_or_budget(path, value):
    fixture = copy.deepcopy(GOLDEN)
    target = fixture
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    with pytest.raises(ValueError):
        bound(fixture)

def test_scoped_no_asset_baseline_is_exact_frozen_knowledge():
    p = module()
    binding = p.verify_answer(GOLDEN["before"], GOLDEN["sent_before"], "original",
                              GOLDEN["knowledge_grant"])
    assert binding["score"] == "INCORRECT"
    assert binding["packet_sha256"] is None
    assert binding["context_sha256"] == p.text_sha(p.legacy.CONTEXT)

def test_scoped_baseline_cannot_silently_include_asset():
    p = module()
    changed = copy.deepcopy(GOLDEN["before"])
    changed["request"]["asset_context"] = GOLDEN["after"]["execution_request"]["asset_context"]
    with pytest.raises(ValueError):
        p.verify_answer(changed, GOLDEN["sent_before"], "original", GOLDEN["knowledge_grant"])

def comparison(scores):
    p = module()
    bindings = [{"answer_id": "answer-" + str(i), "score": score, "model": p.ROUTE["model"],
                 "generation_identity": copy.deepcopy(p.ROUTE)} for i, score in enumerate(scores)]
    return p, bindings

@pytest.mark.parametrize(("scores", "status", "original", "transfer"), [
    (["INCORRECT", "CORRECT", "INCORRECT", "CORRECT"], "FINITE_ASSET_COMPARISON_RECORDED", "FINITE_TASK_DELTA", "FINITE_INDEPENDENT_TASK_DELTA"),
    (["CORRECT"] * 4, "FINITE_ASSET_COMPARISON_RECORDED", "NO_FAILURE_OBSERVED", "NO_MEASURED_DELTA"),
    (["CORRECT", "CORRECT", "INCORRECT", "INCORRECT"], "TRANSFER_FAILURE_REVIEW", "NO_FAILURE_OBSERVED", "NO_IMPROVEMENT"),
    (["INCORRECT", "INCORRECT", "CORRECT", "CORRECT"], "ORIGINAL_TASK_FAILURE_REVIEW", "NO_IMPROVEMENT", "NO_MEASURED_DELTA"),
    (["INCORRECT", "CORRECT", "REVIEW_REQUIRED", "CORRECT"], "UNSCORABLE_COMPARISON", "UNCOMPARABLE", "UNCOMPARABLE"),
])
def test_measured_comparison_not_candidate_save_or_forced_correct_answer_failure(scores, status, original, transfer):
    p, bindings = comparison(scores)
    result = p.compare(*bindings)
    assert result["status"] == status
    assert result["original_observation"] == original
    assert result["transfer_observation"] == transfer
    assert result["learning_improvement"] == "NOT_ESTABLISHED"
    assert result["generalization"] == "NOT_ESTABLISHED"

def test_same_task_reused_as_independent_transfer_is_rejected():
    p, bindings = comparison(["CORRECT"] * 4)
    bindings[-1]["answer_id"] = bindings[0]["answer_id"]
    with pytest.raises(ValueError):
        p.compare(*bindings)

def test_changed_prompt_regime_is_not_asset_effect():
    p, bindings = comparison(["INCORRECT", "CORRECT", "INCORRECT", "CORRECT"])
    bindings[-1]["generation_identity"]["prompt_version"] = "changed"
    with pytest.raises(ValueError):
        p.compare(*bindings)

def test_asset_fixture_does_not_change_legacy_problem_or_budget():
    p = module()
    assert p.CONTRACT["knowledge"] == p.legacy.CONTEXT
    assert p.CONTRACT["rubric"] == p.legacy.RUBRIC
    assert p.CONTRACT["budget"] == {"max_tokens": 2048, "timeout_s": 120}
    assert p.METHOD_MAPPING["actual_kind"] == "rule"

def test_exact_correction_receipt_binds_all_submitted_fields():
    p = module()
    p.verify_correction(GOLDEN["correction"], GOLDEN["sent_correction"], GOLDEN["before"])

@pytest.mark.parametrize(("key", "value"), [
    ("answer_id", "other-answer"), ("corrects_knowledge_id", "other-knowledge"),
    ("question", "different-question"), ("machine_answer", "different-answer"),
    ("corrected_answer", "WRONG CORRECTION"), ("reviewer", "different-reviewer"),
    ("error_note", "different-basis"), ("failed_task_id", "other-failure"),
    ("correction_candidate_id", ""), ("status", "accepted"), ("authority", "knowledge"),
])
def test_corrupted_correction_cannot_be_promoted_by_self_consistent_retest_prior(key, value):
    p = module()
    correction = copy.deepcopy(GOLDEN["correction"])
    correction[key] = value
    with pytest.raises(ValueError):
        p.verify_correction(correction, GOLDEN["sent_correction"], GOLDEN["before"])

def test_correction_candidate_cannot_alias_original_knowledge():
    p = module()
    correction = copy.deepcopy(GOLDEN["correction"])
    correction["correction_candidate_id"] = GOLDEN["before"]["knowledge_id"]
    with pytest.raises(ValueError):
        p.verify_correction(correction, GOLDEN["sent_correction"], GOLDEN["before"])

def test_correct_original_cannot_be_labelled_a_failure():
    p = module()
    original = copy.deepcopy(GOLDEN["before"])
    original["answer"]["answer"] = json.dumps(p.legacy.RUBRIC["original"]["expected"])
    sent = copy.deepcopy(GOLDEN["sent_correction"])
    sent["machine_answer"] = original["answer"]["answer"]
    correction = copy.deepcopy(GOLDEN["correction"])
    correction["machine_answer"] = original["answer"]["answer"]
    with pytest.raises(ValueError):
        p.verify_correction(correction, sent, original)
