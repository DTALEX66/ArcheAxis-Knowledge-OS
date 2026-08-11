from __future__ import annotations

import pytest
from pydantic import ValidationError

LEARNING_ARTIFACT_SCHEMA_ID = (
    "https://archeaxis.local/contracts/v1/learning-artifact.schema.json"
)


def _legacy_artifact():
    from app.facades.enhancement import EnhancementArtifact

    return EnhancementArtifact(
        status="candidate",
        summary={"layer_4_executive": "Evidence must remain reviewable."},
        cards=[
            {
                "card_id": "card-001",
                "title": "Evidence governance",
                "content": "Generated content is a candidate.",
                "source_ids": ["source-001"],
                "tags": ["governance"],
                "review_status": "draft",
            }
        ],
        quality={"status": "clean_by_static_rules", "limitations": "does not prove truth"},
    )


def test_learning_artifact_v1_schema_is_explicit_strict_and_governed():
    from app.contracts.v1 import LearningArtifactV1

    payload = {
        "schema_version": "1.0.0",
        "artifact_id": "artifact-001",
        "artifact_type": "enhancement_bundle",
        "source_record_ids": ["source-001"],
        "summary": {},
        "cards": [],
        "quality": {},
        "status": "candidate",
        "provenance_status": "caller_supplied",
        "requires_human_review": True,
        "created_at": "2026-07-16T00:00:00+00:00",
    }

    assert LearningArtifactV1.model_json_schema()["$id"] == LEARNING_ARTIFACT_SCHEMA_ID
    with pytest.raises(ValidationError):
        LearningArtifactV1(**{key: value for key, value in payload.items() if key != "schema_version"})
    with pytest.raises(ValidationError):
        LearningArtifactV1(**{**payload, "invented": "forbidden"})
    with pytest.raises(ValidationError, match="caller_supplied artifact must remain candidate"):
        LearningArtifactV1(**{**payload, "status": "reviewed"})
    with pytest.raises(ValidationError, match="caller_supplied artifact requires human review"):
        LearningArtifactV1(**{**payload, "requires_human_review": False})


def test_enhancement_artifact_round_trips_losslessly_and_isolated():
    from app.adapters.learning_artifact import (
        from_enhancement_artifact,
        to_enhancement_artifact,
    )

    legacy = _legacy_artifact()
    canonical = from_enhancement_artifact(
        legacy,
        artifact_id="artifact-001",
        source_record_ids=["source-001"],
        created_at="2026-07-16T00:00:00+00:00",
    )

    legacy.summary["layer_4_executive"] = "mutated"
    legacy.cards[0]["source_ids"].append("source-mutated")
    assert canonical.summary["layer_4_executive"] == "Evidence must remain reviewable."
    assert canonical.cards[0]["source_ids"] == ["source-001"]
    assert canonical.status == "candidate"
    assert canonical.provenance_status == "caller_supplied"
    assert canonical.requires_human_review is True

    restored = to_enhancement_artifact(canonical)
    assert restored.model_dump() == _legacy_artifact().model_dump()
    restored.cards[0]["source_ids"].append("projection-mutated")
    assert canonical.cards[0]["source_ids"] == ["source-001"]


def test_learning_artifact_adapter_rejects_unknown_legacy_fields():
    from app.adapters.learning_artifact import from_enhancement_artifact
    from app.adapters.taskpack import ContractMappingError

    class FutureArtifact:
        def model_dump(self):
            return {
                **_legacy_artifact().model_dump(),
                "approved": True,
            }

    with pytest.raises(ContractMappingError, match="unmapped enhancement artifact fields"):
        from_enhancement_artifact(
            FutureArtifact(),
            artifact_id="artifact-future",
            source_record_ids=[],
            created_at="2026-07-16T00:00:00+00:00",
        )


def test_contracts_facade_exports_learning_artifact_surface():
    from app.adapters.learning_artifact import (
        from_enhancement_artifact,
        to_enhancement_artifact,
    )
    from app.contracts.v1 import LearningArtifactV1
    from app.facades import contracts

    assert contracts.LearningArtifactV1 is LearningArtifactV1
    assert contracts.from_enhancement_artifact is from_enhancement_artifact
    assert contracts.to_enhancement_artifact is to_enhancement_artifact
