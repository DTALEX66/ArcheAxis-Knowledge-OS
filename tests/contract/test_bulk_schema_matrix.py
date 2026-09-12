"""BULK-0907 P16: schema matrix gap coverage (worker-protocol hello/request).

Focused, genuinely additive single-field negatives for the two worker-protocol
shapes not isolated in the contract dir (hello/request); every other v1 schema's
positive+negative coverage lives in the existing focused contract cases, R2 cases,
P19 business fixtures and transport tests (see the status dict at the bottom).
"""

import json
from pathlib import Path

from jsonschema import Draft202012Validator, RefResolver

ROOT = Path(__file__).resolve().parents[2]
CONTRACTS = ROOT / "packages" / "contracts" / "v1"


def _errors(schema_name: str, payload: dict) -> list:
    schema = json.loads((CONTRACTS / schema_name).read_text(encoding="utf-8"))
    registry = {
        json.loads(p.read_text(encoding="utf-8")).get("$id", p.name):
        json.loads(p.read_text(encoding="utf-8"))
        for p in CONTRACTS.glob("*.schema.json")
    }
    validator = Draft202012Validator(schema, resolver=RefResolver.from_schema(schema, store=registry))
    return list(validator.iter_errors(payload))


def _flatten(errors):
    for err in errors:
        yield err
        yield from _flatten(err.context)


HELLO = {
    "schema": "archeaxis.worker-hello/v1",
    "type": "hello",
    "protocol": {"major": 1, "min_minor": 0, "max_minor": 0},
    "worker": {"name": "python-worker-text-ndjson", "version": "1"},
    "capabilities": ["text.extract"],
    "schemas": ["archeaxis.text/v1"],
}

REQUEST = {
    "schema": "archeaxis.worker-request/v1",
    "type": "job_request",
    "request_id": "r",
    "job_id": "j",
    "attempt": 1,
    "protocol_minor": 0,
    "capability": "text.extract",
    "capability_version": "1",
    "deadline_ms": 30000,
    "inputs": [{"uri": "job://input/" + "a" * 64, "sha256": "a" * 64, "media_type": "text/plain"}],
    "parameters": {},
}


def test_hello_and_request_positives_pass():
    assert not _errors("worker-protocol.schema.json", HELLO)
    assert not _errors("worker-protocol.schema.json", REQUEST)


def _missing_required(errors, field: str) -> bool:
    return any(e.validator == "required" and field in (e.validator_value or []) for e in errors)


def test_hello_single_field_negatives():
    cases = [
        ({**HELLO, "schema": "archeaxis.worker-hello/v2"}, ["schema"], None),
        ({**HELLO, "protocol": {**HELLO["protocol"], "major": 2}}, ["protocol", "major"], None),
        ({**HELLO, "capabilities": ["text.extract", "text.extract"]}, ["capabilities"], None),
        ({k: v for k, v in HELLO.items() if k != "worker"}, None, "worker"),
    ]
    for payload, expected_path, missing_field in cases:
        errors = list(_flatten(_errors("worker-protocol.schema.json", payload)))
        assert errors, (expected_path, missing_field)
        if missing_field:
            assert _missing_required(errors, missing_field), missing_field
        else:
            assert any(list(e.absolute_path) == expected_path for e in errors), expected_path


def test_request_single_field_negatives_hit_expected_subpaths():
    base = REQUEST
    cases = [
        ({**base, "inputs": [{**base["inputs"][0], "uri": "job://input/zzz"}]}, ["inputs", 0, "uri"]),
        ({**base, "inputs": [{**base["inputs"][0], "sha256": "zzz"}]}, ["inputs", 0, "sha256"]),
        ({**base, "attempt": True}, ["attempt"]),
        ({**base, "protocol_minor": -1}, ["protocol_minor"]),
        ({k: v for k, v in base.items() if k != "inputs"}, None),
    ]
    for payload, expected in cases:
        errors = list(_flatten(_errors("worker-protocol.schema.json", payload)))
        assert errors, expected
        if expected is None:
            assert _missing_required(errors, "inputs")
        else:
            assert any(list(e.absolute_path) == expected for e in errors), expected


def test_schema_matrix_coverage_status_is_explicit():
    # Positive/negative coverage status for every v1 schema (audit contract).
    status = {
        "worker-protocol.schema.json": "covered (response negatives + hello/request here)",
        "job-status.schema.json": "covered",
        "anchor-coordinate.schema.json": "covered",
        "assessment-vocabulary.schema.json": "covered",
        "learning-feedback.schema.json": "covered",
        "machine-feedback.schema.json": "covered",
        "quality-report.schema.json": "covered",
        "coverage-receipt.schema.json": "covered",
        "loss-receipt.schema.json": "covered",
    }
    present = {p.name for p in CONTRACTS.glob("*.schema.json")}
    assert set(status) == present
