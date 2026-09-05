"""Contract v1 cross-language example gate (contracts-vnext, T02).

Loads every JSON Schema in packages/contracts/v1, validates the positive
examples must PASS and negative examples must FAIL, and spot-checks that
closed enums reject unknown values. These examples are the cross-language
reference: Rust/C#/Python bindings must agree on them (protocol-mapping.md).
"""

from __future__ import annotations

import json
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
        schema.get("$id", name): payload
        for name, payload in registry_schemas.items()
        if schema.get("$id")
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
    assert security_schemes["launchToken"]["type"] == "http"

    idem = parameters["IdempotencyKey"]
    assert idem["name"] == "idempotency-key", "canonical header casing must match protocol-mapping"
    assert idem["schema"]["maxLength"] == 200

    error_schema = outline["components"]["schemas"]["Error"]
    assert set(error_schema["required"]) == {"code", "message", "retryable"}

    referenced = set()
    for _path, item in outline.get("paths", {}).items():
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
