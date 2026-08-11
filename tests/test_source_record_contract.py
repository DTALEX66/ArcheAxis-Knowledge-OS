from __future__ import annotations

import pytest
from pydantic import ValidationError

SOURCE_RECORD_SCHEMA_ID = (
    "https://archeaxis.local/contracts/v1/source-record.schema.json"
)


def _legacy_document_row() -> dict[str, object]:
    return {
        "id": "doc_source_001",
        "title": "DNS rebinding notes",
        "content": "Caller-supplied research content.",
        "source": "https://example.test/research",
        "tags": ["network", "security"],
        "created_at": "2026-07-15 00:01:00",
    }


def test_source_record_v1_schema_is_stable_and_strict():
    from app.contracts.v1 import CONTRACT_VERSION, SourceRecordV1

    schema = SourceRecordV1.model_json_schema()
    payload = {
        "schema_version": CONTRACT_VERSION,
        "source_id": "source-strict",
        "title": "Strict source",
        "content": "content",
        "source_locator": "manual:test",
        "tags": [],
        "provenance_status": "unverified",
        "quarantine_status": "candidate",
        "created_at": "2026-07-15 00:00:00",
    }

    assert schema["$id"] == SOURCE_RECORD_SCHEMA_ID
    with pytest.raises(ValidationError):
        SourceRecordV1(**{**payload, "schema_version": "2.0.0"})
    with pytest.raises(ValidationError):
        SourceRecordV1(**{**payload, "unmapped": "forbidden"})
    with pytest.raises(ValidationError):
        SourceRecordV1(**{**payload, "provenance_status": "trusted-by-default"})
    with pytest.raises(ValidationError):
        SourceRecordV1(**{**payload, "quarantine_status": "bypassed"})


def test_kb_document_row_becomes_unverified_quarantined_source_record_v1():
    from app.adapters.source_record import from_kb_document_row
    from app.contracts.v1 import CONTRACT_VERSION, SourceRecordV1

    canonical = from_kb_document_row(_legacy_document_row())

    assert isinstance(canonical, SourceRecordV1)
    assert canonical.schema_version == CONTRACT_VERSION
    assert canonical.source_id == "doc_source_001"
    assert canonical.source_locator == "https://example.test/research"
    assert canonical.provenance_status == "unverified"
    assert canonical.quarantine_status == "candidate"


def test_kb_document_row_roundtrips_without_dropping_legacy_fields():
    from app.adapters.source_record import from_kb_document_row, to_kb_document_row

    row = _legacy_document_row()

    assert to_kb_document_row(from_kb_document_row(row)) == row


def test_kb_document_row_rejects_unmapped_columns():
    from app.adapters.source_record import from_kb_document_row
    from app.adapters.taskpack import ContractMappingError

    row = {**_legacy_document_row(), "provenance_signature": "signed"}

    with pytest.raises(ContractMappingError, match="unmapped fields: provenance_signature"):
        from_kb_document_row(row)


@pytest.mark.parametrize(
    ("field", "value"),
    [("provenance_status", "verified"), ("quarantine_status", "released")],
)
def test_legacy_projection_fails_closed_for_unrepresentable_governance(field: str, value: str):
    from app.adapters.source_record import from_kb_document_row, to_kb_document_row
    from app.adapters.taskpack import ContractMappingError

    canonical = from_kb_document_row(_legacy_document_row()).model_copy(update={field: value})

    with pytest.raises(ContractMappingError, match=f"cannot represent {field}"):
        to_kb_document_row(canonical)


def test_source_record_v1_crosses_real_kb_sqlite_row_boundary(tmp_path, monkeypatch):
    from app.adapters.source_record import from_kb_document_row, to_kb_document_row
    from app.contracts.v1 import CONTRACT_VERSION, SourceRecordV1
    from shared import storage

    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "source-record.sqlite")
    storage.init()
    canonical = SourceRecordV1(
        schema_version=CONTRACT_VERSION,
        source_id="doc_source_sqlite_001",
        title="Quarantined source",
        content="Unverified content remains a candidate.",
        source_locator="manual:cycle-31",
        tags=["candidate"],
        provenance_status="unverified",
        quarantine_status="candidate",
        created_at="2026-07-15 00:02:00",
    )

    storage.insert("kb_documents", to_kb_document_row(canonical))
    persisted = storage.select_one("kb_documents", canonical.source_id)

    assert persisted is not None
    assert from_kb_document_row(persisted) == canonical


def test_contracts_facade_publishes_source_record_v1_adapter_surface():
    from app.adapters.source_record import from_kb_document_row, to_kb_document_row
    from app.contracts.v1 import SourceRecordV1
    from app.facades import contracts

    assert contracts.SourceRecordV1 is SourceRecordV1
    assert contracts.from_kb_document_row is from_kb_document_row
    assert contracts.to_kb_document_row is to_kb_document_row
