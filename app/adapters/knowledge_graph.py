"""Lossless adapters for legacy graph entity and relation rows."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from pydantic import ValidationError

from app.adapters.taskpack import ContractMappingError
from app.contracts.v1 import CONTRACT_VERSION, KnowledgeUnitV1, RelationV1

_ENTITY_FIELDS = {"id", "entity_type", "properties", "graph_name", "created_at"}
_RELATION_FIELDS = {
    "id",
    "source_id",
    "target_id",
    "relation_type",
    "weight",
    "graph_name",
    "created_at",
}


def _require_exact_fields(row: dict[str, Any], expected: set[str], label: str) -> None:
    unknown = set(row) - expected
    if unknown:
        raise ContractMappingError(f"unmapped {label} fields: {sorted(unknown)}")
    missing = expected - set(row)
    if missing:
        raise ContractMappingError(f"missing {label} fields: {sorted(missing)}")


def from_graph_entity_row(row: dict[str, Any]) -> KnowledgeUnitV1:
    _require_exact_fields(row, _ENTITY_FIELDS, "graph entity")
    try:
        return KnowledgeUnitV1(
            schema_version=CONTRACT_VERSION,
            unit_id=row["id"],
            unit_type=row["entity_type"],
            properties=deepcopy(row["properties"]),
            graph_name=row["graph_name"],
            created_at=row["created_at"],
        )
    except ValidationError as error:
        raise ContractMappingError(f"invalid graph entity row: {error}") from error


def to_graph_entity_row(unit: KnowledgeUnitV1) -> dict[str, Any]:
    return {
        "id": unit.unit_id,
        "entity_type": unit.unit_type,
        "properties": deepcopy(unit.properties),
        "graph_name": unit.graph_name,
        "created_at": unit.created_at,
    }


def from_graph_relation_row(row: dict[str, Any]) -> RelationV1:
    _require_exact_fields(row, _RELATION_FIELDS, "graph relation")
    try:
        return RelationV1(
            schema_version=CONTRACT_VERSION,
            relation_id=row["id"],
            source_unit_id=row["source_id"],
            target_unit_id=row["target_id"],
            relation_type=row["relation_type"],
            weight=row["weight"],
            graph_name=row["graph_name"],
            created_at=row["created_at"],
        )
    except ValidationError as error:
        raise ContractMappingError(f"invalid graph relation row: {error}") from error


def to_graph_relation_row(relation: RelationV1) -> dict[str, Any]:
    return {
        "id": relation.relation_id,
        "source_id": relation.source_unit_id,
        "target_id": relation.target_unit_id,
        "relation_type": relation.relation_type,
        "weight": relation.weight,
        "graph_name": relation.graph_name,
        "created_at": relation.created_at,
    }
