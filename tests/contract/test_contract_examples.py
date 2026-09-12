"""Contract v1 cross-language example gate (contracts-vnext, T02).

Loads every JSON Schema in packages/contracts/v1, validates the positive
examples must PASS and negative examples must FAIL, and spot-checks that
closed enums reject unknown values. These examples are the cross-language
reference: Rust/C#/Python bindings must agree on them (protocol-mapping.md).
"""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, RefResolver

ROOT = Path(__file__).resolve().parents[2]
CONTRACTS = ROOT / "packages" / "contracts" / "v1"

# example basename (without extension) -> schema file name
POSITIVE = {
    "job-status.ok": "job-status.schema.json",
    "anchor-coordinate.ok": "anchor-coordinate.schema.json",
    "learning-feedback.ok": "learning-feedback.schema.json",
    "machine-feedback.ok": "machine-feedback.schema.json",
    "quality-report.ok": "quality-report.schema.json",
}
NEGATIVE = {
    "job-status-unknown-verdict.bad": "job-status.schema.json",
    "anchor-unknown-kind.bad": "anchor-coordinate.schema.json",
    "worker-success-with-error.bad": "worker-protocol.schema.json",
}


def _schemas() -> dict[str, dict]:
    result: dict[str, dict] = {}
    for path in CONTRACTS.glob("*.schema.json"):
        result[path.name] = json.loads(path.read_text(encoding="utf-8"))
    return result


def _validator(schema: dict, registry_schemas: dict[str, dict]) -> Draft202012Validator:
    schema_store = {
        payload.get("$id", name): payload
        for name, payload in registry_schemas.items()
        if payload.get("$id")
    }
    resolver = RefResolver.from_schema(schema, store=schema_store)
    return Draft202012Validator(schema, resolver=resolver)


def test_all_positive_examples_validate() -> None:
    registry = _schemas()
    for basename, schema_name in POSITIVE.items():
        payload = json.loads(
            (CONTRACTS / "examples" / "positive" / f"{basename}.json").read_text(encoding="utf-8")
        )
        errors = sorted(_validator(registry[schema_name], registry).iter_errors(payload))
        assert not errors, f"{basename} must validate: {[e.message for e in errors]}"


def test_all_negative_examples_fail() -> None:
    registry = _schemas()
    for basename, schema_name in NEGATIVE.items():
        payload = json.loads(
            (CONTRACTS / "examples" / "negative" / f"{basename}.json").read_text(encoding="utf-8")
        )
        errors = list(_validator(registry[schema_name], registry).iter_errors(payload))
        assert errors, f"{basename} must be rejected"


def test_cross_file_refs_use_each_registered_schema_id(monkeypatch) -> None:
    registry = _schemas()
    schema = {
        "$id": "https://archeaxis.local/contracts/v1/test-report-wrapper.schema.json",
        "type": "object",
        "properties": {"report": {"$ref": "quality-report.schema.json"}},
        "required": ["report"],
    }
    payload = json.loads((CONTRACTS / "examples/positive/quality-report.ok.json").read_text(encoding="utf-8"))
    validator = _validator(schema, registry)
    # The ref points at the real on-disk schema; offline resolution must not fetch.
    monkeypatch.setattr(validator.resolver, "resolve_remote", lambda uri: pytest.fail(f"unexpected remote ref: {uri}"))
    assert not list(validator.iter_errors({"report": payload}))
    payload["rows"][0]["metric"] = "invented_metric"
    assert list(validator.iter_errors({"report": payload}))


def test_existing_coverage_assessment_cross_file_refs_resolve_offline(monkeypatch):
    registry = _schemas()
    coverage = registry["coverage-receipt.schema.json"]
    validator = _validator(coverage, registry)
    monkeypatch.setattr(validator.resolver, "resolve_remote", lambda uri: pytest.fail(f"unexpected remote ref: {uri}"))
    # Exercise the four relative $refs already present in the production schema.
    assessment_validator = validator.evolve(schema=coverage["properties"]["assessment"])
    assessment = {"evidence_status": "SUPPORTED", "test_status": "NOT_TESTED",
                  "rumor_status": "NOT_APPLICABLE", "forecast_status": "NOT_APPLICABLE",
                  "human_review_required": True, "rationale": "independent review pending"}
    assert not list(assessment_validator.iter_errors(assessment))
    for field in ("evidence_status", "test_status", "rumor_status", "forecast_status"):
        invalid = {**assessment, field: "invented_status"}
        assert list(assessment_validator.iter_errors(invalid)), field


@pytest.mark.parametrize("status,value,interval", [
    ("measured", None, None), ("measured", "0.1", None),
    ("unmeasured", 0, None), ("failed", 1, None), ("unsupported", 0.5, None),
    ("unmeasured", None, [0, 1]), ("failed", None, [0, 1]), ("unsupported", None, [0, 1]),
])
def test_quality_schema_rejects_inconsistent_state_and_measurement(status, value, interval):
    registry = _schemas()
    payload = json.loads((CONTRACTS / "examples/positive/quality-report.ok.json").read_text(encoding="utf-8"))
    payload["rows"][0].update(status=status, value=value, interval=interval)
    assert list(_validator(registry["quality-report.schema.json"], registry).iter_errors(payload))


def test_measured_value_is_required_and_error_rates_above_one_are_valid():
    registry = _schemas()
    payload = json.loads((CONTRACTS / "examples/positive/quality-report.ok.json").read_text(encoding="utf-8"))
    validator = _validator(registry["quality-report.schema.json"], registry)
    missing = deepcopy(payload)
    del missing["rows"][0]["value"]
    assert list(validator.iter_errors(missing))
    payload["rows"][0].update(value=2.5, interval=[2.0, 3.0])
    assert not list(validator.iter_errors(payload))


def test_job_status_closed_enum_rejects_unknown() -> None:
    registry = _schemas()
    schema = registry["job-status.schema.json"]
    validator = _validator(schema, registry)
    for field, value in (
        ("job_status", "almost_done"),
        ("research_verdict", "TRUE"),
        ("machine_competence", "MEASURED_SOON"),
    ):
        payload = {
            "job_status": "queued",
            "worker_status": "succeeded",
            "research_verdict": "PASS",
            "machine_competence": "MEASURED",
        }
        payload[field] = value
        assert list(validator.iter_errors(payload)), f"{field}={value!r} must be rejected"


def test_anchor_bounds_are_strict() -> None:
    registry = _schemas()
    schema = registry["anchor-coordinate.schema.json"]
    validator = _validator(schema, registry)
    base = {
        "schema": "archeaxis.anchor-coordinate/v1",
        "anchor_id": "anc_x",
        "source": {
            "source_sha256": "a" * 64,
            "media_type": "text/plain",
        },
        "resolution": "EXACT",
        "resolution_method": "QUOTE_CONTEXT",
    }
    for coordinate in (
        {"kind": "page", "page_index": -1, "page_count_hint": 3},
        {"kind": "media_time", "offset_ms": 0, "duration_ms": 0, "track": "audio"},
        {"kind": "structure_block", "block_path": [], "block_role": "section"},
        {"kind": "selection", "selector": "", "resolved_sha256": "b" * 64},
    ):
        payload = dict(base)
        payload["coordinate"] = coordinate
        assert list(validator.iter_errors(payload)), f"coordinate {coordinate!r} must be rejected"


def test_worker_protocol_success_requires_null_error() -> None:
    registry = _schemas()
    schema = registry["worker-protocol.schema.json"]
    validator = _validator(schema, registry)
    # $defs are exercised through the top-level oneOf; build a full success message.
    payload = {
        "schema": "archeaxis.worker-response/v1",
        "type": "job_result",
        "request_id": "r1",
        "job_id": "j1",
        "attempt": 1,
        "protocol_minor": 0,
        "status": "succeeded",
        "outputs": [],
        "measurements": {},
        "warnings": [],
        "error": None,
    }
    assert not list(validator.iter_errors(payload)), "valid success envelope must pass"
    payload["error"] = {"code": "AAK-X", "message": "boom", "retryable": True}
    assert list(validator.iter_errors(payload)), "success with non-null error must fail"


def test_openapi_reference_internal_consistency() -> None:
    """T02 slice2: the OpenAPI reference's parameter $refs resolve, the
    idempotency header matches protocol-mapping.md canonical casing, the
    security scheme matches the launch-token contract, and every failure
    path speaks the Error envelope vocabulary."""
    import yaml

    outline = yaml.safe_load((CONTRACTS / "openapi-outline.yaml").read_text(encoding="utf-8"))
    assert outline["openapi"] == "3.1.0"
    assert outline["info"]["version"].endswith("reference-slice2")
    assert outline.get("x-freeze", {}).get("status") == "reference-not-implementation"

    parameters = outline["components"]["parameters"]
    security_schemes = outline["components"]["securitySchemes"]
    assert "launchToken" in security_schemes
    launch = security_schemes["launchToken"]
    assert launch["type"] == "apiKey"
    assert launch["in"] == "header"
    assert launch["name"] == "x-archeaxis-launch-token"

    idem = parameters["IdempotencyKey"]
    assert idem["name"] == "idempotency-key", "canonical header casing must match protocol-mapping"
    assert idem["schema"]["maxLength"] == 200

    error_schema = outline["components"]["schemas"]["Error"]
    assert set(error_schema["required"]) == {"code", "message", "retryable"}

    referenced = set()
    for _path, item in outline.get("paths", {}).items():
        for parameter in item.get("parameters", []):
            ref = parameter.get("$ref", "")
            if ref.startswith("#/components/parameters/"):
                referenced.add(ref.rsplit("/", 1)[-1])
        for _verb, operation in item.items():
            if not isinstance(operation, dict):
                continue
            for parameter in operation.get("parameters", []) or []:
                ref = parameter.get("$ref", "")
                if ref.startswith("#/components/parameters/"):
                    referenced.add(ref.rsplit("/", 1)[-1])
    missing = referenced - set(parameters)
    assert not missing, f"openapi references undefined parameters: {missing}"

    mapping = (CONTRACTS / "protocol-mapping.md").read_text(encoding="utf-8")
    assert "idempotency-key" in mapping
    assert "PARTIAL" in mapping and "BLOCKED_CREDENTIALS" in mapping
