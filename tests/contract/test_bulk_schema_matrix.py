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


LIVE_SCHEMA_CASES = {
    "closed-loop.schema.json": {
        "schema": "archeaxis.closed-loop/v1",
        "journey_id": "journey-1",
        "canonical_writer": "archeaxis-core-rust-sqlite",
        "stages": [
            {"stage": stage, "status": "pass", "evidence_level": "real"}
            for stage in (
                "source",
                "knowledge",
                "human_learning",
                "machine_use",
                "evaluation",
                "correction",
                "lesson",
                "retest",
            )
        ],
        "overall_status": "complete",
        "synthetic": False,
    },
    "courseware-artifact.schema.json": {
        "schema": "archeaxis.courseware-artifact/v1",
        "artifact_id": "artifact-1",
        "artifact_type": "lesson",
        "title": "Lesson",
        "domain_pack_id": "general",
        "source_ids": ["source-1"],
        "knowledge_ids": ["knowledge-1"],
        "renderer": "renderer",
        "renderer_version": "1",
        "status": "ready",
        "interactive": False,
        "derived_only": True,
    },
    "derived-projection.schema.json": {
        "schema": "archeaxis.derived-projection/v1",
        "projection_id": "projection-1",
        "projection_kind": "fts",
        "query": "query",
        "algorithm": "bm25",
        "algorithm_version": "1",
        "canonical_source_ids": ["source-1"],
        "items": [{"source_id": "source-1", "source_revision": "1", "score": 1}],
        "generated_at": "2026-09-22T00:00:00Z",
        "rebuildable": True,
        "writes_canonical": False,
    },
    "desktop-routes.schema.json": {
        "schema": "archeaxis.desktop-routes/v1",
        "shell_project": "apps/ArcheAxis.Desktop",
        "routes": [
            {"page_id": page_id, "core_endpoint": f"/api/v1/{page_id}", "read_only": True}
            for page_id in (
                "knowledge",
                "source_reader",
                "learning",
                "jobs",
                "machine_assets",
                "settings",
                "recovery",
            )
        ],
        "canonical_writer": "archeaxis-core-rust-sqlite",
    },
    "domain-pack.schema.json": {
        "schema": "archeaxis.domain-pack/v1",
        "pack_id": "general",
        "domain": "general",
        "version": "1",
        "title": "General",
        "status": "content_ready",
        "source_policy": "canonical_only",
        "learning_modes": ["read"],
        "assessment_types": ["recall"],
        "canonical_object_types": ["source"],
        "entrypoint": "knowledge",
    },
    "format-execution-receipt.schema.json": {
        "schema": "archeaxis.format-execution-receipt/v1",
        "receipt_id": "receipt-1",
        "status": "complete",
        "original": {"sha256": "a" * 64, "name": "input.txt", "format": "txt", "retained": True},
        "transform": {"engine": "text", "engine_version": "1", "derived_document_id": "document-1"},
        "loss": {"status": "none"},
        "structure": {"block_count": 1},
        "anchors": [{"block_id": "block-1", "kind": "paragraph", "locator": {}}],
        "quality_facts": [{"name": "coverage", "status": "measured", "value": 1}],
        "fallback": {"used": False},
    },
    "local-green-identity.schema.json": {
        "schema": "archeaxis.local-green-identity/v1",
        "distribution": "local-green",
        "public_release_base": "v0.6.14",
        "source_commit": "a" * 40,
        "source_tree": "b" * 40,
        "build_timestamp": "2026-09-22T00:00:00Z",
        "runtime_manifest_digest": "c" * 64,
        "published": False,
        "candidate_status": "verified",
    },
    "machine-growth.schema.json": {
        "schema": "archeaxis.machine-growth/v1",
        "receipt_id": "receipt-1",
        "source_event_ids": ["event-1"],
        "goal": "learn",
        "outcome": "success",
        "steps": [{"stage": "experience", "state": "observed", "actor": "system"}],
        "machine_verified": False,
    },
    "model-capability-pool.schema.json": {
        "schema": "archeaxis.model-capability-pool/v1",
        "profile_id": "profile-1",
        "platform": "windows",
        "entries": [
            {
                "role": "llm_text",
                "model": "model",
                "quantization": "q4",
                "runtime": "runtime",
                "fallback": "fallback",
                "status": "unmeasured",
            }
        ],
        "inventory_scope": "repository_profile",
        "benchmark_status": "not_run",
    },
}


def test_hello_and_request_positives_pass():
    assert not _errors("worker-protocol.schema.json", HELLO)
    assert not _errors("worker-protocol.schema.json", REQUEST)


def test_live_schema_matrix_positives_pass():
    for schema_name, payload in LIVE_SCHEMA_CASES.items():
        assert not _errors(schema_name, payload), schema_name


def test_live_schema_matrix_single_field_negatives_hit_expected_subpaths():
    cases = [
        ("closed-loop.schema.json", {**LIVE_SCHEMA_CASES["closed-loop.schema.json"], "canonical_writer": "other"}, ["canonical_writer"]),
        ("courseware-artifact.schema.json", {**LIVE_SCHEMA_CASES["courseware-artifact.schema.json"], "source_ids": []}, ["source_ids"]),
        ("derived-projection.schema.json", {**LIVE_SCHEMA_CASES["derived-projection.schema.json"], "rebuildable": False}, ["rebuildable"]),
        ("desktop-routes.schema.json", {**LIVE_SCHEMA_CASES["desktop-routes.schema.json"], "routes": [{**LIVE_SCHEMA_CASES["desktop-routes.schema.json"]["routes"][0], "read_only": "yes"}, *LIVE_SCHEMA_CASES["desktop-routes.schema.json"]["routes"][1:]]}, ["routes", 0, "read_only"]),
        ("domain-pack.schema.json", {**LIVE_SCHEMA_CASES["domain-pack.schema.json"], "domain": "unknown"}, ["domain"]),
        ("format-execution-receipt.schema.json", {**LIVE_SCHEMA_CASES["format-execution-receipt.schema.json"], "original": {**LIVE_SCHEMA_CASES["format-execution-receipt.schema.json"]["original"], "retained": False}}, ["original", "retained"]),
        ("local-green-identity.schema.json", {**LIVE_SCHEMA_CASES["local-green-identity.schema.json"], "published": True}, ["published"]),
        ("machine-growth.schema.json", {**LIVE_SCHEMA_CASES["machine-growth.schema.json"], "machine_verified": True}, ["machine_verified"]),
        ("model-capability-pool.schema.json", {**LIVE_SCHEMA_CASES["model-capability-pool.schema.json"], "entries": [{**LIVE_SCHEMA_CASES["model-capability-pool.schema.json"]["entries"][0], "status": "unknown"}]}, ["entries", 0, "status"]),
    ]
    for schema_name, payload, expected_path in cases:
        errors = list(_flatten(_errors(schema_name, payload)))
        assert errors, schema_name
        assert any(list(error.absolute_path) == expected_path for error in errors), (schema_name, expected_path)


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
        "closed-loop.schema.json": "covered (test_live_schema_matrix_positives_pass; test_live_schema_matrix_single_field_negatives_hit_expected_subpaths)",
        "courseware-artifact.schema.json": "covered (test_live_schema_matrix_positives_pass; test_live_schema_matrix_single_field_negatives_hit_expected_subpaths)",
        "derived-projection.schema.json": "covered (test_live_schema_matrix_positives_pass; test_live_schema_matrix_single_field_negatives_hit_expected_subpaths)",
        "desktop-routes.schema.json": "covered (test_live_schema_matrix_positives_pass; test_live_schema_matrix_single_field_negatives_hit_expected_subpaths)",
        "domain-pack.schema.json": "covered (test_live_schema_matrix_positives_pass; test_live_schema_matrix_single_field_negatives_hit_expected_subpaths)",
        "format-execution-receipt.schema.json": "covered (test_live_schema_matrix_positives_pass; test_live_schema_matrix_single_field_negatives_hit_expected_subpaths)",
        "local-green-identity.schema.json": "covered (test_live_schema_matrix_positives_pass; test_live_schema_matrix_single_field_negatives_hit_expected_subpaths)",
        "machine-growth.schema.json": "covered (test_live_schema_matrix_positives_pass; test_live_schema_matrix_single_field_negatives_hit_expected_subpaths)",
        "model-capability-pool.schema.json": "covered (test_live_schema_matrix_positives_pass; test_live_schema_matrix_single_field_negatives_hit_expected_subpaths)",
    }
    present = {p.name for p in CONTRACTS.glob("*.schema.json")}
    assert set(status) == present
