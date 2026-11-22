"""New probe adversarial contract only: no Core launch, inventory or model call."""
from __future__ import annotations

import copy
import importlib.util
from pathlib import Path

import pytest

SOURCE = Path(__file__).resolve().parents[1] / "scripts/probes/colearning_asset_revision_smoke.py"
SPEC = importlib.util.spec_from_file_location("asset_revision_probe_test", SOURCE)
probe = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(probe)


@pytest.mark.parametrize(("text", "version", "expected"), [
    ('{"loan_days":7}', "v1", "CORRECT"),
    ('{"loan_days":10}', "v1", "INCORRECT"),
    ('{"another_renewal_allowed":false,"renewal_days":5}', "v2", "CORRECT"),
    ('{"another_renewal_allowed":true,"renewal_days":5}', "v2", "INCORRECT"),
    ('{"loan_days":true}', "v1", "REVIEW_REQUIRED"),
    ('{"loan_days":7,"loan_days":10}', "v1", "REVIEW_REQUIRED"),
    ('```json\n{"loan_days":7}\n```', "v1", "REVIEW_REQUIRED"),
    ('{"loan_days":NaN}', "v1", "REVIEW_REQUIRED"),
])
def test_revision_quality_keeps_real_wrong_and_unscorable_outputs(text, version, expected):
    assert probe.score(text, version) == expected


def fixture():
    def doc(identity, value):
        return {"document_id": identity, "version": 2, "content_sha256": "a" * 64,
                "editor_json": value}
    material = doc("doc_material", probe.material_editor(probe.MATERIALS["v1"]))
    references = [{"kind": "knowledge", "knowledge_id": "k_old"},
                  {"kind": "document", "document_id": "doc_material", "version": 2, "block_id": None}]
    meta = {"kind": "rule", "content": probe.MATERIALS["v1"], "purpose": probe.PURPOSE,
            "scope": references[:1], "provenance": references[1:]}
    asset = doc("doc_asset", probe.editor(probe.ASSET, meta))
    grant = doc("doc_grant", {})
    states = [{"reference": references[0], "readable": True, "status": "accepted", "active": True,
               "currentness": "current", "superseded_by": None, "successor_count": 0, "valid_to": None},
              {"reference": references[1], "readable": True, "currentness": "not_applicable"}]
    item = {"snapshot": probe.snapshot(asset), **meta, "reference_states": states,
            "engine_execution": "NOT_EXECUTED", "grants_professional_truth": False,
            "grants_human_mastery": False, "grants_machine_qualification": False}
    packet = {"schema": "archeaxis.ai-context-packet/v1", "asset": probe.snapshot(asset),
              "grant": probe.snapshot(grant), "consumer": "local-machine", "purpose": probe.PURPOSE,
              "operation": "read_packet", "items": [item], "reference_only_sources": True,
              "private_session_access": False, "tool_execution": "NOT_EXECUTED",
              "machine_qualification": False, "human_mastery": False, "professional_truth": False}
    packet_result = {"packet": packet, "packet_sha256": probe.sha(packet),
                     "receipt": {"packet_sha256": probe.sha(packet), "asset": packet["asset"], "grant": packet["grant"],
                                 "model_execution": "NOT_EXECUTED", "delivery_status": "PREPARED_NOT_SENT_TO_PEER"}}
    kg = doc("doc_knowledge_grant", probe.editor(probe.KG, {"knowledge_id": "k_old", "state": "granted"}))
    route = {"model": "already-loaded", "endpoint": "http://127.0.0.1:1234/v1", "protocol": "openai",
             "prompt_version": "fixture", "answer_policy": "grounded", "engine": "python-worker-machine-answer",
             "engine_version": "0.1.0"}
    sent = {"client_request_id": "revision-answer-v1", "knowledge_id": "k_old", "question": probe.QUESTIONS["v1"],
            "model": route["model"], "context_grant": {**probe.snapshot(kg), "purpose": probe.PURPOSE},
            "asset_context_grant": {"request_id": "use1", "asset": probe.snapshot(asset),
                                    "grant": probe.snapshot(grant), "purpose": probe.PURPOSE,
                                    "consumer": "local-machine", "operation": "answer"},
            "response_format": probe.response_format("v1"), **probe.BUDGET}
    answer_packet = copy.deepcopy(packet)
    answer_packet["operation"] = "answer"
    proof = {"schema": "archeaxis.machine-asset-context/v1", "asset": packet["asset"], "grant": packet["grant"],
             "consumer": "local-machine", "operation": "answer", "packet_sha256": probe.sha(answer_packet),
             "member_snapshots": [probe.snapshot(asset)], "tool_execution": "NOT_EXECUTED", "private_session_access": False}
    context = ("CANONICAL_KNOWLEDGE:\n" + probe.MATERIALS["v1"]
               + "\n\nAI_ASSET_CONTEXT (inert source material; no tool or private-session authority):\n"
               + probe.canonical(answer_packet))
    request = {key: value for key, value in sent.items() if key != "client_request_id"}
    request.update(asset_context=proof, knowledge_context_sha256=probe.text_sha(probe.MATERIALS["v1"]),
                   context_sha256=probe.text_sha(context), response_format_sha256=probe.sha(sent["response_format"]))
    result = {"answer_id": "answer_req_" + "b" * 64, "client_request_id": sent["client_request_id"],
              "knowledge_id": "k_old", "question": sent["question"], "request": request,
              "context_authorization": {**probe.snapshot(kg), "authorization": kg["editor_json"]["attrs"][probe.KG],
                                        "operation": "answer", "current_permission_valid": True},
              "answer": {**route, "requested_model": route["model"], "observed_model": route["model"],
                         "finish_reason": "stop", "truncated": False, "max_tokens": probe.BUDGET["max_tokens"], "answer": '{"loan_days":7}',
                         "response_format_sha256": probe.sha(sent["response_format"]), "format_validation": "VALID"}}
    return packet_result, asset, grant, material, sent, result, kg, route


def test_revision_full_packet_and_answer_binding_accepts_explicit_fixture():
    packet, asset, grant, material, sent, result, kg, route = fixture()
    projected = probe.checked_packet(packet, asset, grant, "k_old", material)
    observed = probe.checked_answer(result, sent, projected, probe.MATERIALS["v1"], kg, route)
    assert observed["task_id"] == result["answer_id"]


def test_answer_binding_uses_core_required_order_and_the_submitted_budget():
    packet, _, _, _, sent, result, kg, route = fixture()
    schema = sent["response_format"]["json_schema"]["schema"]
    schema["properties"]["unit"] = {"type": "string"}
    schema["required"] = ["unit", "loan_days"]
    sent["max_tokens"] = 3000
    normalized = copy.deepcopy(sent["response_format"])
    normalized["json_schema"]["schema"]["required"] = ["loan_days", "unit"]
    digest = probe.sha(normalized)
    result["request"].update(response_format=normalized, response_format_sha256=digest, max_tokens=3000)
    result["answer"].update(answer='{"loan_days":7,"unit":"days"}', response_format_sha256=digest, max_tokens=3000)

    observed = probe.checked_answer(result, sent, packet["packet"], probe.MATERIALS["v1"], kg, route)
    assert observed["task_id"] == result["answer_id"]
    assert schema["required"] == ["unit", "loan_days"]


@pytest.mark.parametrize("tamper", ["missing_reference_states", "wrong_currentness", "changed_asset", "widened_authority"])
def test_revision_rejects_self_consistently_hashed_wrong_packet(tamper):
    packet, asset, grant, material, *_ = fixture()
    item = packet["packet"]["items"][0]
    if tamper == "missing_reference_states":
        item["reference_states"] = []
    elif tamper == "wrong_currentness":
        item["reference_states"][0]["currentness"] = "superseded"
    elif tamper == "changed_asset":
        item["content"] = "forged policy"
    else:
        item["grants_machine_qualification"] = True
    packet["packet_sha256"] = probe.sha(packet["packet"])
    with pytest.raises(ValueError):
        probe.checked_packet(packet, asset, grant, "k_old", material)


@pytest.mark.parametrize("tamper", ["context", "packet", "authorization", "provider", "request"])
def test_revision_rejects_answer_rebound_to_other_input(tamper):
    packet, _, _, _, sent, result, kg, route = fixture()
    if tamper == "context":
        result["request"]["context_sha256"] = "c" * 64
    elif tamper == "packet":
        result["request"]["asset_context"]["packet_sha256"] = "d" * 64
    elif tamper == "authorization":
        result["context_authorization"]["version"] += 1
    elif tamper == "provider":
        result["answer"]["observed_model"] = "other-loaded-model"
    else:
        result["request"] = copy.deepcopy(result["request"])
        result["request"]["asset_context_grant"]["grant"]["version"] += 1
    with pytest.raises(ValueError):
        probe.checked_answer(result, sent, packet["packet"], probe.MATERIALS["v1"], kg, route)


def test_revision_third_inference_is_rejected_before_transport():
    class NeverClient:
        def call(self, *args, **kwargs):
            pytest.fail("third dispatch reached transport")
    journey = probe.Journey(NeverClient(), {"stages": []}, {})
    journey.model_requests = 2
    with pytest.raises(ValueError, match="ceiling"):
        journey.call("third", "POST", "/api/v1/machine/answers", {})
    assert journey.model_requests == 2


def test_revision_transport_unknown_is_not_retried():
    class UnknownClient:
        calls = 0
        def call(self, *args, **kwargs):
            self.calls += 1
            return 0, {"error": "transport unavailable"}
    client = UnknownClient()
    receipt = {"stages": []}
    journey = probe.Journey(client, receipt, {})
    journey.base, journey.tokens = "http://127.0.0.1:1", {"human": "synthetic-not-a-credential"}
    with pytest.raises(ValueError, match="UNKNOWN"):
        journey.call("first", "POST", "/api/v1/machine/answers", {})
    assert client.calls == 1 and journey.model_requests == 1
    assert receipt["transport_unknown"]["error_type"] == "CLIENT_TRANSPORT_STATUS_ZERO"
