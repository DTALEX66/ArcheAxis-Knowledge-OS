"""Finite failed-call measurements; no model text or provider-body admission."""
import copy
import json
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]


def schemas():
    outline = yaml.safe_load((ROOT / "packages/contracts/v1/openapi-outline.yaml").read_text(encoding="utf-8"))
    yield outline["components"]["schemas"]["MachineFailureDiagnostics"]
    for name in ("material-question", "conversation"):
        schema = json.loads((ROOT / f"packages/contracts/v2/{name}.schema.json").read_text(encoding="utf-8"))
        yield schema["$defs"]["MachineFailureDiagnostics"]


def test_failure_measurement_contracts_agree_and_exclude_private_payloads():
    definitions = list(schemas())
    assert definitions[0] == definitions[1] == definitions[2]
    for schema in definitions:
        validator = Draft202012Validator(schema)
        assert not list(validator.iter_errors({"requested_model": "aaos-deep-27b-mtp", "observed_model": None, "elapsed_s": 0, "usage": {"output_tokens": 0}}))
        for field, value in (("requested_model", "bad\\model"), ("finish_reason", "PRIVATE"), ("stderr", "PRIVATE"), ("reasoning_content", "PRIVATE"), ("max_tokens", True), ("elapsed_s", -1), ("http_status", 600), ("usage", {"output_tokens": -1}), ("usage", {"raw": "PRIVATE"})):
            assert list(validator.iter_errors({field: value})), (field, value)


def test_timeout_stage_contract_is_finite_and_discovery_duration_is_optional():
    for schema in schemas():
        validator = Draft202012Validator(schema)
        for stage in ("service_discovery", "model_request", "response_deadline", "worker_deadline"):
            assert not list(validator.iter_errors({"request_stage": stage, "discovery_elapsed_s": 0.25}))
        for raw in ({"request_stage": "PRIVATE path"}, {"discovery_elapsed_s": -1}, {"discovery_elapsed_s": True}):
            assert list(validator.iter_errors(raw))


@pytest.mark.parametrize("name,receipt", [("material-question", "MaterialQuestionReceiptDto"), ("conversation", "ConversationReceiptDto")])
def test_failed_receipt_diagnostics_are_optional_and_finite(name, receipt):
    schema = json.loads((ROOT / f"packages/contracts/v2/{name}.schema.json").read_text(encoding="utf-8"))
    if receipt not in schema["$defs"]:
        receipt = next(k for k, v in schema["$defs"].items() if v.get("properties", {}).get("schema", {}).get("const") == "archeaxis.material-answer/v1")
    assert "diagnostics" not in schema["$defs"][receipt]["required"]
    node = copy.deepcopy(schema)
    node["$ref"] = "#/$defs/MachineFailureDiagnostics"
    assert not list(Draft202012Validator(node).iter_errors({"finish_reason": "length"}))
    assert list(Draft202012Validator(node).iter_errors({"answer": "PRIVATE"}))


def test_request_phase_measurements_are_optional_finite_and_never_ttft_or_provider_state():
    for schema in schemas():
        validator=Draft202012Validator(schema)
        for phase in ("http_open","body_read","json_parse","response_validation"):
            assert not list(validator.iter_errors({"request_stage":"model_request","request_phase":phase,"http_open_elapsed_s":0.25,"body_read_elapsed_s":0,"json_parse_elapsed_s":1,"prompt_utf8_bytes":0,"serialized_request_bytes":753,"response_bytes":4194305}))
        for key in ("prompt_utf8_bytes","serialized_request_bytes","response_bytes"):
            for value in (True,-1,1.5,9007199254740992,"PRIVATE"):
                assert list(validator.iter_errors({key:value}))
        for key in ("http_open_elapsed_s","body_read_elapsed_s","json_parse_elapsed_s"):
            for value in (True,-1,9007199254740992,"PRIVATE"):
                assert list(validator.iter_errors({key:value}))
        for raw in ({"request_phase":"PRIVATE"},{"ttft_s":0},{"provider_stop_state":"STOPPED"},{"prompt":"PRIVATE"},{"headers":{"token":"PRIVATE"}}):
            assert list(validator.iter_errors(raw))
