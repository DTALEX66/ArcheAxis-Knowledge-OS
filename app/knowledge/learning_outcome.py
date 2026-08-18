"""Learning outcome persistence — closes the human-learning feedback arc.

Teach-Back and quiz results are currently pure evaluations (returned but not
stored), so they never feed FSRS scheduling, mastery signals, or machine
knowledge candidates. This module persists any learning outcome into the
canonical review ledger and re-runs the governed cascade:

    outcome (teach-back / quiz / review) → kb_reviews (+ kb_mistakes)
        → mastery signal (append-only) → machine knowledge candidate (if mastered)

Uses the same tables and SM-2 scheduling as closed_loop.record_practice_evidence
but takes a card_id directly, so any card (artifact-created or not) can feed
the loop.
"""

from __future__ import annotations

import sqlite3
from hashlib import sha256
from pathlib import Path
from typing import Any

from app.contracts.v1 import MachineKnowledgeUnitV1, MasterySignalV1
from app.knowledge.machine_knowledge import create_machine_knowledge_candidate_on_connection
from app.knowledge.mastery import persist_mastery_signal_on_connection
from shared import core_schema


class LearningOutcomeError(ValueError):
    """Raised when a learning outcome cannot be persisted."""


def _review_id(command_id: str) -> str:
    return "outcome_" + sha256(command_id.encode()).hexdigest()[:24]


def _sm2(quality: int, prev_interval: int, prev_ease: float):
    """SM-2 schedule (mirrors knowledge_base.reviews._sm2_interval)."""
    from knowledge_base.reviews import _sm2_interval
    return _sm2_interval(quality, prev_interval, prev_ease)


def record_learning_outcome(
    *,
    card_id: str,
    command_id: str,
    quality: int,
    recorded_at: str,
    db_path: str | Path,
    mistake_detail: str | None = None,
    error_type: str = "recall_failure",
) -> dict[str, Any]:
    """Persist one learning outcome and return the governed cascade.

    Args:
        card_id: target card (must exist in kb_cards).
        command_id: idempotency key for the review receipt.
        quality: 0..5 review quality (FSRS/SM-2 scale).
        recorded_at: ISO timestamp.
        mistake_detail: when set, an unresolved mistake row is also written.
        error_type: mistake classification (default recall_failure).

    Returns:
        {review_id, mastery_signal, machine_knowledge, mistake_id}
    """
    if not card_id or not command_id:
        raise LearningOutcomeError("card_id and command_id are required")
    if not 0 <= quality <= 5:
        raise LearningOutcomeError("quality must be between 0 and 5")
    database = Path(db_path)
    review_id = _review_id(command_id)
    with sqlite3.connect(database) as connection:
        connection.row_factory = sqlite3.Row
        connection.execute("BEGIN IMMEDIATE")
        try:
            core_schema.validate(connection)
            card = connection.execute("SELECT id FROM kb_cards WHERE id=?", (card_id,)).fetchone()
            if card is None:
                raise LearningOutcomeError(f"card not found: {card_id}")

            mistake_id: str | None = None
            if mistake_detail:
                mistake_id = "mistake_" + sha256(f"{card_id}:{command_id}".encode()).hexdigest()[:24]
                connection.execute(
                    "INSERT INTO kb_mistakes (id, card_id, error_type, detail, source_topic, "
                    "resolved, resolution_note, resolved_at, created_at) VALUES (?, ?, ?, ?, ?, 0, '', NULL, ?)",
                    (mistake_id, card_id, error_type, mistake_detail, "", recorded_at),
                )

            prev = connection.execute(
                "SELECT interval_days, ease_factor FROM kb_reviews "
                "WHERE card_id=? ORDER BY created_at DESC LIMIT 1",
                (card_id,),
            ).fetchone()
            prev_interval = int(prev["interval_days"]) if prev else 0
            prev_ease = float(prev["ease_factor"]) if prev else 2.5
            new_interval, new_ease, next_date = _sm2(quality, prev_interval, prev_ease)
            connection.execute(
                "INSERT INTO kb_reviews (id, card_id, quality, interval_days, ease_factor, "
                "next_review_at, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (review_id, card_id, quality, new_interval, new_ease,
                 next_date.isoformat(), recorded_at),
            )

            signal, signal_id = persist_mastery_signal_on_connection(
                connection, card_id, calculated_at=recorded_at
            )
            machine: MachineKnowledgeUnitV1 | None = None
            if signal.is_mastered:
                machine = create_machine_knowledge_candidate_on_connection(
                    connection, signal_id, title="Mastered learning rule",
                    content="Learner mastered this card; extract as reusable knowledge.",
                )
            connection.commit()
            return {
                "review_id": review_id,
                "mistake_id": mistake_id,
                "mastery_signal": signal,
                "machine_knowledge": machine,
            }
        except Exception:
            connection.rollback()
            raise
