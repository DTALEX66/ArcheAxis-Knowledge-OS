"""Adapters between canonical source records and legacy KB document rows."""

from __future__ import annotations

from typing import Any

from app.adapters.taskpack import ContractMappingError
from app.contracts.v1 import CONTRACT_VERSION, SourceRecordV1

_KB_DOCUMENT_FIELDS = {
    "id",
    "title",
    "content",
    "source",
    "tags",
    "created_at",
}


def from_kb_document_row(row: dict[str, Any]) -> SourceRecordV1:
    """Promote a decoded legacy KB row into quarantined canonical form."""

    unmapped = sorted(row.keys() - _KB_DOCUMENT_FIELDS)
    if unmapped:
        raise ContractMappingError(f"source record row unmapped fields: {', '.join(unmapped)}")
    missing = sorted(_KB_DOCUMENT_FIELDS - row.keys())
    if missing:
        raise ContractMappingError(f"source record row missing fields: {', '.join(missing)}")
    tags = row["tags"]
    if not isinstance(tags, list) or not all(isinstance(tag, str) for tag in tags):
        raise ContractMappingError("source record row tags must be a list of strings")

    return SourceRecordV1(
        schema_version=CONTRACT_VERSION,
        source_id=row["id"],
        title=row["title"],
        content=row["content"],
        source_locator=row["source"],
        tags=list(tags),
        provenance_status="unverified",
        quarantine_status="candidate",
        created_at=row["created_at"],
    )


def to_kb_document_row(source: SourceRecordV1) -> dict[str, Any]:
    """Project to legacy storage only when governance remains representable."""

    if source.provenance_status != "unverified":
        raise ContractMappingError("cannot represent provenance_status in legacy KB document")
    if source.quarantine_status != "candidate":
        raise ContractMappingError("cannot represent quarantine_status in legacy KB document")
    return {
        "id": source.source_id,
        "title": source.title,
        "content": source.content,
        "source": source.source_locator,
        "tags": list(source.tags),
        "created_at": source.created_at,
    }
