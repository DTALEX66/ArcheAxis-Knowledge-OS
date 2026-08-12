from __future__ import annotations

import pytest
from pydantic import ValidationError

MACHINE_KNOWLEDGE_UNIT_SCHEMA_ID = (
    "https://archeaxis.local/contracts/v1/machine-knowledge-unit.schema.json"
)


def _legacy_row(*, active: int = 1):
    return {
        "id": "mku-001",
        "title": "Evidence-first execution",
        "content": "Do not report success without tool evidence.",
        "unit_type": "rule",
        "tags": ["runtime", "evidence"],
        "confidence": 0.8,
        "source_type": "a_to_b",
        "source_id": "card-001",
        "active": active,
        "created_at": "2026-07-16T00:00:00+00:00",
        "updated_at": "2026-07-16T00:01:00+00:00",
    }


def test_machine_knowledge_unit_v1_schema_is_explicit_strict_and_governed():
    from app.contracts.v1 import MachineKnowledgeUnitV1

    payload = {
        "schema_version": "1.0.0",
        "unit_id": "mku-001",
        "title": "Rule",
        "content": "Use evidence.",
        "unit_type": "rule",
        "tags": [],
        "confidence": 0.5,
        "source_type": "manual",
        "source_id": "",
        "legacy_active": 1,
        "lifecycle_status": "legacy_active_unverified",
        "provenance_status": "legacy_unverified",
        "requires_human_review": True,
        "created_at": "now",
        "updated_at": "now",
    }

    assert MachineKnowledgeUnitV1.model_json_schema()["$id"] == MACHINE_KNOWLEDGE_UNIT_SCHEMA_ID
    with pytest.raises(ValidationError):
        MachineKnowledgeUnitV1(**{key: value for key, value in payload.items() if key != "schema_version"})
    with pytest.raises(ValidationError):
        MachineKnowledgeUnitV1(**{**payload, "invented": "forbidden"})
    with pytest.raises(ValidationError, match="unverified machine knowledge requires human review"):
        MachineKnowledgeUnitV1(**{**payload, "requires_human_review": False})
    with pytest.raises(ValidationError, match="approved machine knowledge requires server_verified provenance"):
        MachineKnowledgeUnitV1(**{**payload, "lifecycle_status": "approved"})


def test_active_machine_knowledge_row_round_trips_without_auto_approval():
    from app.adapters.machine_knowledge import (
        from_machine_knowledge_row,
        to_machine_knowledge_row,
    )

    row = _legacy_row(active=1)
    unit = from_machine_knowledge_row(row)

    assert unit.lifecycle_status == "legacy_active_unverified"
    assert unit.provenance_status == "legacy_unverified"
    assert unit.requires_human_review is True
    assert to_machine_knowledge_row(unit) == row


def test_inactive_machine_knowledge_row_round_trips_as_deprecated():
    from app.adapters.machine_knowledge import (
        from_machine_knowledge_row,
        to_machine_knowledge_row,
    )

    row = _legacy_row(active=0)
    unit = from_machine_knowledge_row(row)

    assert unit.lifecycle_status == "deprecated"
    assert to_machine_knowledge_row(unit) == row


def test_machine_knowledge_row_rejects_unknown_fields_and_isolates_tags():
    from app.adapters.machine_knowledge import from_machine_knowledge_row
    from app.adapters.taskpack import ContractMappingError

    row = _legacy_row()
    unit = from_machine_knowledge_row(row)
    row["tags"].append("mutated")
    assert unit.tags == ["runtime", "evidence"]

    with pytest.raises(ContractMappingError, match="unmapped machine knowledge fields"):
        from_machine_knowledge_row({**_legacy_row(), "published": True})


def test_approved_canonical_machine_knowledge_cannot_downgrade_to_legacy_active():
    from app.adapters.machine_knowledge import (
        from_machine_knowledge_row,
        to_machine_knowledge_row,
    )
    from app.adapters.taskpack import ContractMappingError

    approved = from_machine_knowledge_row(_legacy_row()).model_copy(
        update={
            "lifecycle_status": "approved",
            "provenance_status": "server_verified",
            "requires_human_review": False,
        }
    )
    with pytest.raises(ContractMappingError, match="cannot represent approved governance"):
        to_machine_knowledge_row(approved)


def test_contracts_facade_exports_machine_knowledge_surface():
    from app.adapters.machine_knowledge import (
        from_machine_knowledge_row,
        to_machine_knowledge_row,
    )
    from app.contracts.v1 import MachineKnowledgeUnitV1
    from app.facades import contracts

    assert contracts.MachineKnowledgeUnitV1 is MachineKnowledgeUnitV1
    assert contracts.from_machine_knowledge_row is from_machine_knowledge_row
    assert contracts.to_machine_knowledge_row is to_machine_knowledge_row


def test_scoped_unit_cannot_round_trip_to_legacy_row():
    """GOV-001 review: a scoped unit has no legacy row representation, so it
    must fail closed rather than silently drop its scope."""
    from app.adapters.machine_knowledge import to_machine_knowledge_row
    from app.adapters.taskpack import ContractMappingError
    from app.contracts.v1 import MachineKnowledgeUnitV1

    unit = MachineKnowledgeUnitV1(
        schema_version="1.0.0",
        unit_id="mku-scoped",
        title="Scoped",
        content="rule",
        unit_type="rule",
        tags=[],
        confidence=0.8,
        source_type="mastery_signal",
        source_id="signal-1",
        legacy_active=0,
        scope="knowledge",
        lifecycle_status="deprecated",
        provenance_status="server_verified",
        requires_human_review=False,
        created_at="now",
        updated_at="now",
    )
    with pytest.raises(ContractMappingError, match="cannot represent a scoped unit"):
        to_machine_knowledge_row(unit)
