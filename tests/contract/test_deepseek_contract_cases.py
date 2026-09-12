"""DS08: cross-language contract cases (schema-checkable).

Independent positive/negative cases per v1 schema using the real jsonschema
validator (never string-contains assertions). Cases assert exactly what the
schema decides; measured-null coupling is schema-enforced (see the
quality-report case below), not a runtime-only boundary.
"""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

from jsonschema import Draft202012Validator, RefResolver

ROOT = Path(__file__).resolve().parents[2]
CONTRACTS = ROOT / "packages" / "contracts" / "v1"


def _registry() -> dict[str, dict]:
    return {
        json.loads(p.read_text(encoding="utf-8")).get("$id", p.name):
        json.loads(p.read_text(encoding="utf-8"))
        for p in CONTRACTS.glob("*.schema.json")
    }


def _validator(schema_name: str) -> Draft202012Validator:
    schema = json.loads((CONTRACTS / schema_name).read_text(encoding="utf-8"))
    resolver = RefResolver.from_schema(schema, store=_registry())
    return Draft202012Validator(schema, resolver=resolver)


def _errors(schema_name: str, payload: dict) -> list:
    return list(_validator(schema_name).iter_errors(payload))


def _flatten(errors):
    """Yield each error plus its nested context errors (oneOf/allOf branches)."""
    for err in errors:
        yield err
        yield from _flatten(err.context)


WORKER_RESPONSE = {
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


def test_worker_unknown_status_and_missing_field_and_wrong_version_rejected():
    # unknown status (closed enum)
    assert _errors("worker-protocol.schema.json", {**WORKER_RESPONSE, "status": "almost_done"})
    # missing required request_id
    missing = {k: v for k, v in WORKER_RESPONSE.items() if k != "request_id"}
    assert _errors("worker-protocol.schema.json", missing)
    # wrong schema version (const)
    assert _errors("worker-protocol.schema.json", {**WORKER_RESPONSE, "schema": "archeaxis.worker-response/v2"})


def test_worker_output_hash_and_uri_are_single_field_negatives():
    asset = {
        "kind": "text", "uri": "job://output/" + "a" * 64,
        "sha256": "a" * 64, "media_type": "text/plain", "byte_length": 1,
        "schema": "archeaxis.text/v1", "authority_effect": "candidate_or_measurement_only",
    }
    valid = {**WORKER_RESPONSE, "outputs": [asset]}
    # Valid base passes before any negative is introduced.
    assert not _errors("worker-protocol.schema.json", valid)
    bad_hash = deepcopy(valid)
    bad_hash["outputs"][0]["sha256"] = "zzz"
    hash_errors = list(_flatten(_errors("worker-protocol.schema.json", bad_hash)))
    assert hash_errors
    # The hash negative must fail on the sha256 pattern specifically, not on an
    # unrelated required field or on the URI.
    assert any(err.validator == "pattern" and list(err.absolute_path) == ["outputs", 0, "sha256"]
               for err in hash_errors)
    bad_uri = deepcopy(valid)
    bad_uri["outputs"][0]["uri"] = "job://output/zzz"
    uri_errors = list(_flatten(_errors("worker-protocol.schema.json", bad_uri)))
    assert uri_errors
    assert any(err.validator == "pattern" and list(err.absolute_path) == ["outputs", 0, "uri"]
               for err in uri_errors)


def test_worker_hash_pattern_removal_accepts_bad_hash_in_memory_only():
    # Negative control: weaken a deep copy of the loaded schema in memory by
    # removing only the sha256 pattern; the same bad hash must then be accepted.
    # This proves the test can detect when the constraint is silently dropped.
    schema = json.loads((CONTRACTS / "worker-protocol.schema.json").read_text(encoding="utf-8"))
    weakened = deepcopy(schema)
    del weakened["$defs"]["response"]["properties"]["outputs"]["items"]["properties"]["sha256"]["pattern"]
    weak_validator = Draft202012Validator(weakened)
    asset = {
        "kind": "text", "uri": "job://output/" + "a" * 64,
        "sha256": "zzz", "media_type": "text/plain", "byte_length": 1,
        "schema": "archeaxis.text/v1", "authority_effect": "candidate_or_measurement_only",
    }
    valid = {**WORKER_RESPONSE, "outputs": [asset]}
    assert not list(weak_validator.iter_errors(valid))
    # The untouched schema still rejects the same payload.
    assert _errors("worker-protocol.schema.json", valid)


def test_job_status_closed_enums_reject_unknown():
    base = {"job_status": "queued", "worker_status": "succeeded",
            "research_verdict": "PASS", "machine_competence": "MEASURED"}
    for field, value in [("job_status", "half_done"), ("worker_status", "killed"),
                         ("research_verdict", "MAYBE"), ("machine_competence", "KINDA")]:
        assert _errors("job-status.schema.json", {**base, field: value}), (field, value)


def test_anchor_coordinate_rejects_bad_geometry():
    base = {
        "schema": "archeaxis.anchor-coordinate/v1",
        "anchor_id": "a1",
        "source": {"source_sha256": "a" * 64, "media_type": "text/plain"},
        "coordinate": {"kind": "char_range", "start": 0, "end": 1, "text_excerpt": "x"},
        "resolution": "EXACT",
        "resolution_method": "QUOTE_CONTEXT",
    }
    assert _errors("anchor-coordinate.schema.json", {**base, "source": {"source_sha256": "short", "media_type": "text/plain"}})
    assert _errors("anchor-coordinate.schema.json",
                   {**base, "coordinate": {"kind": "page", "page_index": -1, "page_count_hint": 3}})
    assert _errors("anchor-coordinate.schema.json",
                   {**base, "coordinate": {"kind": "media_time", "offset_ms": 0, "duration_ms": 0, "track": "audio"}})
    assert _errors("anchor-coordinate.schema.json",
                   {**base, "coordinate": {"kind": "structure_block", "block_path": [], "block_role": "section"}})


def test_assessment_vocabulary_closed_enums_reject_unknown():
    base = {
        "knowledge_type": "NOTE",
        "review_status": "DRAFT",
        "evidence_status": "UNASSESSED",
        "test_status": "NOT_TESTED",
        "rumor_status": "NOT_APPLICABLE",
        "forecast_status": "NOT_APPLICABLE",
        "use_status": "DRAFT",
        "anchor_resolution": "UNRESOLVED",
    }
    assert not _errors("assessment-vocabulary.schema.json", base)
    for field, value in [("knowledge_type", "SECRET"), ("review_status", "APPROVED")]:
        assert _errors("assessment-vocabulary.schema.json", {**base, field: value}), (field, value)


def test_learning_feedback_rejects_unknown_event_and_missing_item_ref():
    base = {
        "schema": "archeaxis.learning-feedback/v1",
        "event_id": "e1",
        "learner_id": "u1",
        "event": "question_answered",
        "item_ref": {"kind": "question", "id": "q1"},
        "occurred_at": "2026-09-06T00:00:00Z",
    }
    assert not _errors("learning-feedback.schema.json", base)
    assert _errors("learning-feedback.schema.json", {**base, "event": "slept"})
    assert _errors("learning-feedback.schema.json", {k: v for k, v in base.items() if k != "item_ref"})


def test_machine_feedback_rejects_unknown_event_and_missing_budget():
    base = {
        "schema": "archeaxis.machine-feedback/v1",
        "event_id": "m1",
        "client_id": "c1",
        "event": "context_served",
        "item_ref": {"kind": "candidate", "id": "x1"},
        "context_budget_chars": 10,
        "occurred_at": "2026-09-06T00:00:00Z",
    }
    assert not _errors("machine-feedback.schema.json", base)
    assert _errors("machine-feedback.schema.json", {**base, "event": "hallucinated"})
    assert _errors("machine-feedback.schema.json", {k: v for k, v in base.items() if k != "context_budget_chars"})


def test_quality_report_status_value_coupling_is_schema_enforced():
    row = {
        "metric": "cer",
        "sample_id": "s",
        "status": "measured",
        "value": 0.0,
        "unit": "error_rate",
        "prediction_ref": {"sha256": "a" * 64, "path": "p"},
        "gold_ref": {"sha256": "b" * 64, "path": "g"},
    }
    report = {"schema": "archeaxis.quality-report/v1", "report_id": "r", "run_id": "run",
              "engine": {"name": "e", "version": "v"}, "rows": [row], "generated_at": "2026-09-06T00:00:00Z"}
    assert not _errors("quality-report.schema.json", report)
    # unknown status rejected
    assert _errors("quality-report.schema.json", {**report, "rows": [{**row, "status": "guessed"}]})
    # measured row missing gold_ref rejected
    assert _errors("quality-report.schema.json", {**report, "rows": [{k: v for k, v in row.items() if k != "gold_ref"}]})
    # measured value must be a number (null rejected at schema level)
    assert _errors("quality-report.schema.json", {**report, "rows": [{**row, "value": None}]})
    # unmeasured value must be null (a number is rejected)
    assert not _errors("quality-report.schema.json",
                       {**report, "rows": [{**row, "status": "unmeasured", "value": None, "unit": "error_rate"}]})
    assert _errors("quality-report.schema.json",
                   {**report, "rows": [{**row, "status": "unmeasured", "value": 0.5}]})


def test_coverage_receipt_requires_providers_and_provider_fields():
    base = {
        "schema": "archeaxis.coverage-receipt/v1",
        "receipt_id": "r1",
        "run_id": "run1",
        "claim_revision_id": "c1",
        "scope": {"question": "q", "languages": ["zh"], "query_families": ["f"], "required_source_roles": ["primary"]},
        "providers": [{"provider_id": "p", "index_family": "web", "queries": 1, "returned": 1,
                       "retrieved": 1, "blocked": 0, "failed": 0}],
        "dedup": {"raw_results": 1, "canonical_urls": 1, "document_clusters": 1,
                  "assertion_origin_groups": 1, "evidence_generation_groups": 1, "independence_unknown": 0},
        "coverage": {"status": "PARTIAL", "planned_query_families": 2, "executed_query_families": 1,
                     "primary_candidates_found": 3, "primary_sources_retrieved": 2,
                     "contradiction_search_executed": True, "earliest_origin_checked": False,
                     "inaccessible_sources": [], "unresolved_gaps": ["gap-1"]},
        "assessment": {"evidence_status": "PARTIALLY_SUPPORTED", "test_status": "NOT_TESTED",
                       "rumor_status": "NOT_APPLICABLE", "forecast_status": "NOT_APPLICABLE",
                       "human_review_required": True, "rationale": "r"},
        "reproducibility": {"query_plan_sha256": "a" * 64, "provider_registry_version": "v",
                            "dedup_profile_version": "v", "extractor_version": "v",
                            "model_id": "m", "prompt_sha256": "b" * 64,
                            "schema_version": "v", "snapshot_sha256": ["c" * 64]},
        "stop": {"reason": "SUFFICIENT", "stopped_at": "2026-09-06T00:00:00Z"},
        "receipt_payload_sha256": "d" * 64,
    }
    assert not _errors("coverage-receipt.schema.json", base)
    assert _errors("coverage-receipt.schema.json", {k: v for k, v in base.items() if k != "providers"})
    assert _errors("coverage-receipt.schema.json", {**base, "providers": [{"provider_id": "p"}]})


def test_loss_receipt_schema_rejects_unknown_and_partial_coverage():
    minimal = {"engine": "e", "engine_version": "v", "params": {}, "loss_note": None}
    assert not _errors("loss-receipt.schema.json", minimal)
    assert _errors("loss-receipt.schema.json", {**minimal, "surprise": True})
    # dependentRequired: covered without total+coverage is rejected
    assert _errors("loss-receipt.schema.json", {**minimal, "covered": 3})
    # coverage is capped at 1 by the schema
    assert _errors("loss-receipt.schema.json", {**minimal, "covered": 1, "total": 1, "coverage": 2.0})
