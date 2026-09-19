"""R6 A04 Knowledge/Source V3 governance tests."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.contracts.knowledge_v3 import KnowledgeObjectV3, KnowledgeSourceV3


def _personal(**overrides):
    payload = {
        "schema_version": "3.0.0",
        "source_id": "src-personal-1",
        "title": "A project observation",
        "content": "The local build needs the registered tool path.",
        "source_type": "project_observation",
        "owner": "human",
        "status": "accepted",
        "confidence": 0.9,
        "created_at": "2026-09-19T00:00:00+00:00",
    }
    payload.update(overrides)
    return payload


def test_personal_knowledge_can_be_accepted_without_external_evidence():
    source = KnowledgeSourceV3.model_validate(_personal())
    assert source.status == "accepted"
    assert source.external_evidence == []
    assert source.support_level == "none"


def test_machine_candidate_stays_candidate_even_with_links_and_confidence():
    payload = _personal(
        source_id="src-machine-1",
        source_type="machine_candidate",
        owner="machine",
        status="candidate",
        external_evidence=["https://example.invalid/evidence"],
        confidence=1.0,
    )
    source = KnowledgeSourceV3.model_validate(payload)
    assert source.status == "candidate"
    with pytest.raises(ValidationError, match="cannot be accepted or verified"):
        KnowledgeSourceV3.model_validate({**payload, "status": "verified", "requires_human_review": False, "support_level": "strong"})


def test_machine_owner_cannot_write_a_non_candidate_source_type():
    with pytest.raises(ValidationError, match="machine owner"):
        KnowledgeSourceV3.model_validate(_personal(owner="machine", source_type="external_document"))


def test_knowledge_object_preserves_temporal_and_supersession_fields():
    obj = KnowledgeObjectV3.model_validate({
        "schema_version": "3.0.0",
        "knowledge_id": "k-1",
        "source_id": "src-personal-1",
        "title": "A correction",
        "body": "The corrected method.",
        "source_type": "personal_experience",
        "owner": "human",
        "status": "accepted",
        "support_level": "none",
        "confidence": 0.8,
        "valid_from": "2026-09-01T00:00:00+00:00",
        "valid_to": "2026-09-19T00:00:00+00:00",
        "supersedes": ["k-old"],
        "created_at": "2026-09-19T00:00:00+00:00",
        "updated_at": "2026-09-19T00:00:00+00:00",
    })
    assert obj.supersedes == ["k-old"]


def test_invalid_temporal_range_is_rejected():
    with pytest.raises(ValidationError, match="valid_to"):
        KnowledgeSourceV3.model_validate(_personal(
            valid_from="2026-09-20T00:00:00+00:00",
            valid_to="2026-09-19T00:00:00+00:00",
        ))


def test_versioned_json_schema_is_present_and_names_both_v3_objects():
    import json
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    schema = json.loads((root / "packages/contracts/v3/knowledge-source.schema.json").read_text(encoding="utf-8"))
    assert schema["$id"].endswith("/contracts/v3/knowledge-source.schema.json")
    assert len(schema["oneOf"]) == 2
    assert all(item["properties"]["schema_version"]["const"] == "3.0.0" for item in schema["oneOf"])
