"""Governed MachineKnowledge candidates derived from mastered signals."""
from __future__ import annotations

import sqlite3
from hashlib import sha256
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from app.contracts.v1 import MachineKnowledgeUnitV1, MasterySignalV1
from shared import core_schema, knowledge_governance_migration


class MachineKnowledgeApproval(BaseModel):
    model_config = ConfigDict(extra="forbid")
    approval_id: str = Field(min_length=1)
    candidate_id: str = Field(min_length=1)
    reviewer_id: str = Field(min_length=1)
    decision: str = Field(pattern="^(approved|deprecated)$")
    rationale: str = Field(min_length=1)
    reviewed_at: str = Field(min_length=1)


def _candidate_id(signal_id: str) -> str:
    return "machine_candidate_" + sha256(signal_id.encode()).hexdigest()[:24]


def create_machine_knowledge_candidate(
    signal_id: str, *, title: str, content: str, db_path: str | Path
) -> MachineKnowledgeUnitV1:
    with sqlite3.connect(Path(db_path)) as connection:
        connection.row_factory = sqlite3.Row
        core_schema.validate(connection)
        existing = connection.execute("SELECT unit_json FROM machine_knowledge_candidates_v1 WHERE source_signal_id=?", (signal_id,)).fetchone()
        if existing:
            return MachineKnowledgeUnitV1.model_validate_json(existing["unit_json"])
        row = connection.execute("SELECT signal_json, calculated_at FROM mastery_signals_v1 WHERE id=?", (signal_id,)).fetchone()
        if row is None or not MasterySignalV1.model_validate_json(row["signal_json"]).is_mastered:
            raise ValueError("machine knowledge candidate requires a mastered signal")
        unit = MachineKnowledgeUnitV1(schema_version="1.0.0", unit_id=_candidate_id(signal_id), title=title, content=content, unit_type="rule", tags=[], confidence=0.8, source_type="mastery_signal", source_id=signal_id, legacy_active=0, lifecycle_status="candidate", provenance_status="server_verified", requires_human_review=True, created_at=row["calculated_at"], updated_at=row["calculated_at"])
        connection.execute("INSERT INTO machine_knowledge_candidates_v1 VALUES (?, ?, ?, 'candidate', NULL, NULL, NULL, ?)", (unit.unit_id, signal_id, unit.model_dump_json(), row["calculated_at"]))
        connection.commit()
        return unit


def deprecate_machine_knowledge_candidate(approval: MachineKnowledgeApproval, *, db_path: str | Path) -> MachineKnowledgeUnitV1:
    database = Path(db_path)
    knowledge_governance_migration.require_applied(db_path=database)
    with sqlite3.connect(database) as connection:
        connection.row_factory = sqlite3.Row
        core_schema.validate(connection)
        connection.execute("BEGIN IMMEDIATE")
        try:
            existing = connection.execute(
                "SELECT candidate_id, reviewer_id, decision, rationale, reviewed_at FROM machine_knowledge_approval_events_v1 WHERE approval_id=?",
                (approval.approval_id,),
            ).fetchone()
            expected = (approval.candidate_id, approval.reviewer_id, approval.decision, approval.rationale, approval.reviewed_at)
            if existing is not None and tuple(str(value) for value in existing) != expected:
                raise RuntimeError("machine knowledge approval id conflicts with an existing receipt")
            row = connection.execute("SELECT unit_json FROM machine_knowledge_candidates_v1 WHERE id=?", (approval.candidate_id,)).fetchone()
            if row is None:
                raise ValueError("machine knowledge candidate not found")
            current = MachineKnowledgeUnitV1.model_validate_json(row["unit_json"])
            if existing is not None:
                if current.lifecycle_status != approval.decision:
                    raise RuntimeError("machine knowledge approval receipt conflicts with current lifecycle")
                connection.commit()
                return current
            unit = MachineKnowledgeUnitV1.model_validate({**current.model_dump(), "legacy_active": 0, "lifecycle_status": approval.decision, "requires_human_review": approval.decision != "approved", "updated_at": approval.reviewed_at})
            event_id = "machine_knowledge_approval_" + sha256(approval.approval_id.encode()).hexdigest()[:24]
            connection.execute(
                "INSERT INTO machine_knowledge_approval_events_v1 VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (event_id, approval.candidate_id, approval.approval_id, approval.reviewer_id, approval.decision, approval.rationale, approval.reviewed_at, approval.reviewed_at),
            )
            connection.execute("UPDATE machine_knowledge_candidates_v1 SET unit_json=?, lifecycle_status=?, approval_id=?, reviewer_id=?, rationale=?, updated_at=? WHERE id=?", (unit.model_dump_json(), approval.decision, approval.approval_id, approval.reviewer_id, approval.rationale, approval.reviewed_at, unit.unit_id))
            connection.commit()
            return unit
        except Exception:
            connection.rollback()
            raise


def list_runtime_machine_knowledge(*, db_path: str | Path) -> list[MachineKnowledgeUnitV1]:
    """Return only strictly validated, human-approved units for Runtime consumption."""
    with sqlite3.connect(Path(db_path)) as connection:
        connection.row_factory = sqlite3.Row
        core_schema.validate(connection)
        rows = connection.execute(
            "SELECT id, unit_json, approval_id, reviewer_id, rationale "
            "FROM machine_knowledge_candidates_v1 "
            "WHERE lifecycle_status='approved' ORDER BY updated_at, id"
        ).fetchall()

    approved: list[MachineKnowledgeUnitV1] = []
    for row in rows:
        unit = MachineKnowledgeUnitV1.model_validate_json(row["unit_json"])
        if (
            unit.unit_id != row["id"]
            or unit.lifecycle_status != "approved"
            or unit.requires_human_review
            or not row["approval_id"]
            or not row["reviewer_id"]
            or not row["rationale"]
        ):
            raise RuntimeError("approved machine knowledge payload conflicts with governance row")
        approved.append(unit)
    return approved
