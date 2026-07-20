"""Governed Phase 5 tracer: reviewed learning, deterministic practice and audit read-back."""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

from app.contracts.v1 import LearningArtifactV1, MachineKnowledgeUnitV1, MasterySignalV1
from app.knowledge.learning_artifact import (
    KnowledgeLearningArtifactApproval,
    approve_artifact_cards,
    create_candidate_learning_artifact,
)
from app.knowledge.machine_knowledge import create_machine_knowledge_candidate
from app.knowledge.mastery import persist_mastery_signal
from shared import knowledge_governance_migration


@dataclass(frozen=True)
class PracticeResult:
    mastery_signal: MasterySignalV1
    machine_knowledge: MachineKnowledgeUnitV1 | None


@dataclass(frozen=True)
class ClosedLoopAuditEvent:
    event_type: str
    occurred_at: str


def start_learning_candidate(
    *, unit_id: str, approval_id: str, reviewer_id: str, rationale: str, reviewed_at: str, db_path: str | Path
) -> LearningArtifactV1:
    return create_candidate_learning_artifact(
        KnowledgeLearningArtifactApproval(
            approval_id=approval_id, unit_id=unit_id, reviewer_id=reviewer_id,
            rationale=rationale, reviewed_at=reviewed_at,
        ), db_path=db_path,
    )


def approve_learning_artifact(
    *, artifact_id: str, command_id: str, reviewer_id: str, reviewed_at: str, db_path: str | Path
) -> list[str]:
    if not command_id:
        raise ValueError("learning approval requires command_id")
    cards = approve_artifact_cards(
        artifact_id, reviewer_id=reviewer_id, reviewed_at=reviewed_at, db_path=db_path
    )
    return [card["id"] for card in cards]


def _card_id(connection: sqlite3.Connection, artifact_id: str) -> str:
    row = connection.execute(
        "SELECT id FROM kb_cards WHERE id GLOB ? ORDER BY id LIMIT 1", (f"{artifact_id}-card-*",)
    ).fetchone()
    if row is None:
        raise ValueError("practice requires an approved learning artifact")
    return str(row[0])


def _signal_id(card_id: str, calculated_at: str, signal: MasterySignalV1) -> str:
    return "mastery_" + sha256(
        f"{card_id}:{calculated_at}:{signal.model_dump_json()}".encode()
    ).hexdigest()[:24]


def record_practice_evidence(
    *, artifact_id: str, command_id: str, quality: int, recorded_at: str, db_path: str | Path
) -> PracticeResult:
    if not command_id:
        raise ValueError("practice requires command_id")
    if not 0 <= quality <= 5:
        raise ValueError("practice quality must be between 0 and 5")
    database = Path(db_path)
    knowledge_governance_migration.require_applied(db_path=database)
    review_id = "practice_" + sha256(command_id.encode()).hexdigest()[:24]
    with sqlite3.connect(database) as connection:
        connection.row_factory = sqlite3.Row
        card_id = _card_id(connection, artifact_id)
        existing_review = connection.execute(
            "SELECT card_id, quality, created_at FROM kb_reviews WHERE id=?", (review_id,)
        ).fetchone()
        if existing_review is not None:
            if str(existing_review["card_id"]) != card_id or int(existing_review["quality"]) != quality:
                raise RuntimeError("practice command id conflicts with an existing receipt")
            original_recorded_at = str(existing_review["created_at"])
            signal_row = connection.execute(
                "SELECT id, signal_json FROM mastery_signals_v1 "
                "WHERE card_id=? AND calculated_at=? ORDER BY id LIMIT 1",
                (card_id, original_recorded_at),
            ).fetchone()
            if signal_row is not None:
                signal = MasterySignalV1.model_validate_json(signal_row["signal_json"])
                candidate = connection.execute(
                    "SELECT unit_json FROM machine_knowledge_candidates_v1 WHERE source_signal_id=?",
                    (str(signal_row["id"]),),
                ).fetchone()
                machine = (
                    MachineKnowledgeUnitV1.model_validate_json(candidate["unit_json"])
                    if candidate is not None
                    else None
                )
                return PracticeResult(mastery_signal=signal, machine_knowledge=machine)
            recorded_at = original_recorded_at
        else:
            connection.execute(
                "INSERT INTO kb_reviews(id, card_id, quality, interval_days, ease_factor, next_review_at, created_at) "
                "VALUES (?, ?, ?, 1, 2.5, ?, ?)",
                (review_id, card_id, quality, recorded_at, recorded_at),
            )
        connection.commit()
    signal = persist_mastery_signal(card_id, db_path=database, calculated_at=recorded_at)
    machine = None
    if signal.is_mastered:
        with sqlite3.connect(database) as connection:
            connection.row_factory = sqlite3.Row
            signal_id = _signal_id(card_id, recorded_at, signal)
            machine = create_machine_knowledge_candidate(
                signal_id, title="Reviewed learning rule", content="Apply the reviewed learning rule.", db_path=database
            )
    return PracticeResult(mastery_signal=signal, machine_knowledge=machine)


def audit_closed_loop(artifact_id: str, *, db_path: str | Path) -> list[ClosedLoopAuditEvent]:
    database = Path(db_path)
    with sqlite3.connect(database) as connection:
        connection.row_factory = sqlite3.Row
        artifact = connection.execute(
            "SELECT artifact_json, created_at FROM knowledge_candidate_learning_artifacts_v1 WHERE id=?", (artifact_id,)
        ).fetchone()
        if artifact is None:
            raise ValueError("closed-loop audit requires an existing learning artifact")
        events = [ClosedLoopAuditEvent("learning_candidate_created", str(artifact["created_at"]))]
        card_id = _card_id(connection, artifact_id)
        events.append(ClosedLoopAuditEvent("learning_artifact_approved", str(connection.execute("SELECT created_at FROM kb_cards WHERE id=?", (card_id,)).fetchone()[0])))
        reviews = connection.execute("SELECT created_at FROM kb_reviews WHERE card_id=? ORDER BY created_at, id", (card_id,)).fetchall()
        events.extend(ClosedLoopAuditEvent("practice_recorded", str(row["created_at"])) for row in reviews)
        signals = connection.execute("SELECT id, calculated_at FROM mastery_signals_v1 WHERE card_id=? ORDER BY calculated_at, id", (card_id,)).fetchall()
        for signal in signals:
            events.append(ClosedLoopAuditEvent("mastery_calculated", str(signal["calculated_at"])))
            candidate = connection.execute("SELECT updated_at FROM machine_knowledge_candidates_v1 WHERE source_signal_id=?", (signal["id"],)).fetchone()
            if candidate is not None:
                events.append(ClosedLoopAuditEvent("machine_knowledge_candidate_created", str(candidate["updated_at"])))
    return events
