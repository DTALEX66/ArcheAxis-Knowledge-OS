"""Adapter for the current in-memory enhancement artifact."""

from __future__ import annotations

from copy import deepcopy
from typing import TYPE_CHECKING, Any

from pydantic import ValidationError

from app.adapters.taskpack import ContractMappingError
from app.contracts.v1 import CONTRACT_VERSION, LearningArtifactV1

if TYPE_CHECKING:
    from app.facades.enhancement import EnhancementArtifact

_LEGACY_FIELDS = {"status", "summary", "cards", "quality"}


def from_enhancement_artifact(
    artifact: EnhancementArtifact,
    *,
    artifact_id: str,
    source_record_ids: list[str],
    created_at: str,
) -> LearningArtifactV1:
    payload: dict[str, Any] = artifact.model_dump()
    unknown = set(payload) - _LEGACY_FIELDS
    if unknown:
        raise ContractMappingError(
            f"unmapped enhancement artifact fields: {sorted(unknown)}"
        )
    missing = _LEGACY_FIELDS - set(payload)
    if missing:
        raise ContractMappingError(
            f"missing enhancement artifact fields: {sorted(missing)}"
        )
    try:
        return LearningArtifactV1(
            schema_version=CONTRACT_VERSION,
            artifact_id=artifact_id,
            artifact_type="enhancement_bundle",
            source_record_ids=deepcopy(source_record_ids),
            summary=deepcopy(payload["summary"]),
            cards=deepcopy(payload["cards"]),
            quality=deepcopy(payload["quality"]),
            status="candidate",
            provenance_status="caller_supplied",
            requires_human_review=True,
            created_at=created_at,
        )
    except ValidationError as error:
        raise ContractMappingError(f"invalid enhancement artifact: {error}") from error


def to_enhancement_artifact(artifact: LearningArtifactV1) -> EnhancementArtifact:
    from app.facades.enhancement import EnhancementArtifact

    if artifact.status != "candidate":
        raise ContractMappingError(
            "reviewed or rejected learning artifact cannot be represented by legacy enhancement"
        )
    return EnhancementArtifact(
        status="candidate",
        summary=deepcopy(artifact.summary),
        cards=deepcopy(artifact.cards),
        quality=deepcopy(artifact.quality),
    )
