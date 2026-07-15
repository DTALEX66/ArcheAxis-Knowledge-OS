"""Lossless adapter for decoded legacy machine-knowledge rows."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from pydantic import ValidationError

from app.adapters.taskpack import ContractMappingError
from app.contracts.v1 import CONTRACT_VERSION, MachineKnowledgeUnitV1

_ROW_FIELDS = {
    "id",
    "title",
    "content",
    "unit_type",
    "tags",
    "confidence",
    "source_type",
    "source_id",
    "active",
    "created_at",
    "updated_at",
}


def from_machine_knowledge_row(row: dict[str, Any]) -> MachineKnowledgeUnitV1:
    unknown = set(row) - _ROW_FIELDS
    if unknown:
        raise ContractMappingError(f"unmapped machine knowledge fields: {sorted(unknown)}")
    missing = _ROW_FIELDS - set(row)
    if missing:
        raise ContractMappingError(f"missing machine knowledge fields: {sorted(missing)}")
    lifecycle_status = "legacy_active_unverified" if row["active"] else "deprecated"
    try:
        return MachineKnowledgeUnitV1(
            schema_version=CONTRACT_VERSION,
            unit_id=row["id"],
            title=row["title"],
            content=row["content"],
            unit_type=row["unit_type"],
            tags=deepcopy(row["tags"]),
            confidence=row["confidence"],
            source_type=row["source_type"],
            source_id=row["source_id"],
            legacy_active=row["active"],
            lifecycle_status=lifecycle_status,
            provenance_status="legacy_unverified",
            requires_human_review=True,
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
    except ValidationError as error:
        raise ContractMappingError(f"invalid machine knowledge row: {error}") from error


def to_machine_knowledge_row(unit: MachineKnowledgeUnitV1) -> dict[str, Any]:
    if unit.lifecycle_status == "approved":
        raise ContractMappingError(
            "legacy machine knowledge row cannot represent approved governance"
        )
    expected_status = "legacy_active_unverified" if unit.legacy_active else "deprecated"
    if unit.lifecycle_status != expected_status:
        raise ContractMappingError(
            "legacy active flag conflicts with canonical lifecycle governance"
        )
    return {
        "id": unit.unit_id,
        "title": unit.title,
        "content": unit.content,
        "unit_type": unit.unit_type,
        "tags": deepcopy(unit.tags),
        "confidence": unit.confidence,
        "source_type": unit.source_type,
        "source_id": unit.source_id,
        "active": unit.legacy_active,
        "created_at": unit.created_at,
        "updated_at": unit.updated_at,
    }
