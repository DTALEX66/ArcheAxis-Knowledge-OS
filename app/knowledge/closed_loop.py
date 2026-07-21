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
    approve_artifact_cards_on_connection,
    create_candidate_learning_artifact,
    create_candidate_learning_artifact_on_connection,
)
from app.knowledge.machine_knowledge import create_machine_knowledge_candidate_on_connection
from app.knowledge.mastery import persist_mastery_signal_on_connection
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


def start_and_approve_learning_candidate(
    *,
    unit_id: str,
    approval_id: str,
    approval_command_id: str,
    reviewer_id: str,
    rationale: str,
    reviewed_at: str,
    db_path: str | Path,
) -> tuple[LearningArtifactV1, list[str]]:
    """Create and approve a learning candidate in one caller-visible transaction."""
    database = Path(db_path)
    knowledge_governance_migration.require_applied(db_path=database)
    approval = KnowledgeLearningArtifactApproval(
        approval_id=approval_id,
        unit_id=unit_id,
        reviewer_id=reviewer_id,
        rationale=rationale,
        reviewed_at=reviewed_at,
    )
    with sqlite3.connect(database) as connection:
        connection.row_factory = sqlite3.Row
        connection.execute("BEGIN IMMEDIATE")
        try:
            artifact = create_candidate_learning_artifact_on_connection(connection, approval)
            cards = approve_artifact_cards_on_connection(
                connection,
                artifact.artifact_id,
                command_id=approval_command_id,
                reviewer_id=reviewer_id,
                reviewed_at=reviewed_at,
            )
            connection.commit()
            return artifact, [card["id"] for card in cards]
        except Exception:
            connection.rollback()
            raise


def approve_learning_artifact(
    *, artifact_id: str, command_id: str, reviewer_id: str, reviewed_at: str, db_path: str | Path
) -> list[str]:
    if not command_id:
        raise ValueError("learning approval requires command_id")
    cards = approve_artifact_cards(
        artifact_id, command_id=command_id, reviewer_id=reviewer_id,
        reviewed_at=reviewed_at, db_path=db_path
    )
    return [card["id"] for card in cards]


def _card_id(connection: sqlite3.Connection, artifact_id: str) -> str:
    artifact = connection.execute(
        "SELECT id FROM knowledge_candidate_learning_artifacts_v1 WHERE id=?", (artifact_id,)
    ).fetchone()
    if artifact is None:
        raise ValueError("practice requires an existing learning artifact")
    card_id = f"{artifact_id}-card-0"
    row = connection.execute(
        "SELECT id FROM kb_cards WHERE id=?", (card_id,)
    ).fetchone()
    if row is None:
        raise ValueError("practice requires an approved learning artifact")
    return str(row[0])


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
        connection.execute("BEGIN IMMEDIATE")
        try:
            existing_review = connection.execute(
                "SELECT card_id, quality, created_at FROM kb_reviews WHERE id=?", (review_id,)
            ).fetchone()
            if existing_review is not None:
                if (
                    str(existing_review["card_id"]) != f"{artifact_id}-card-0"
                    or int(existing_review["quality"]) != quality
                ):
                    raise RuntimeError("practice command id conflicts with an existing receipt")
                card_id = _card_id(connection, artifact_id)
                recorded_at = str(existing_review["created_at"])
                signal_row = connection.execute(
                    "SELECT id, signal_json FROM mastery_signals_v1 "
                    "WHERE card_id=? AND calculated_at=? ORDER BY id LIMIT 1",
                    (card_id, recorded_at),
                ).fetchone()
                if signal_row is not None:
                    signal = MasterySignalV1.model_validate_json(signal_row["signal_json"])
                    candidate = connection.execute(
                        "SELECT unit_json FROM machine_knowledge_candidates_v1 "
                        "WHERE source_signal_id=?",
                        (str(signal_row["id"]),),
                    ).fetchone()
                    machine = (
                        MachineKnowledgeUnitV1.model_validate_json(candidate["unit_json"])
                        if candidate is not None
                        else None
                    )
                    connection.commit()
                    return PracticeResult(mastery_signal=signal, machine_knowledge=machine)
            else:
                card_id = _card_id(connection, artifact_id)
                connection.execute(
                    "INSERT INTO kb_reviews(id, card_id, quality, interval_days, ease_factor, "
                    "next_review_at, created_at) VALUES (?, ?, ?, 1, 2.5, ?, ?)",
                    (review_id, card_id, quality, recorded_at, recorded_at),
                )
            signal, signal_id = persist_mastery_signal_on_connection(
                connection, card_id, calculated_at=recorded_at
            )
            machine = None
            if signal.is_mastered:
                machine = create_machine_knowledge_candidate_on_connection(
                    connection,
                    signal_id,
                    title="Reviewed learning rule",
                    content="Apply the reviewed learning rule.",
                )
            connection.commit()
            return PracticeResult(mastery_signal=signal, machine_knowledge=machine)
        except Exception:
            connection.rollback()
            raise


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
