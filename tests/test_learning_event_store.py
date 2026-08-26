"""Append-only learning truth, replay, and receipt-gated machine competence."""
from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.learning.event_store import (
    EventConflictError,
    EvidenceGateError,
    LearningEvent,
    append_event,
    create_distillation_candidate,
    current_machine_level,
    record_machine_receipt,
    replay_human_state,
)
from shared.migration_runner import MigrationOperator


def _db(tmp_path: Path) -> Path:
    path = tmp_path / "learning.sqlite"
    path.touch()
    MigrationOperator(db_path=path, backup_dir=tmp_path / "backups").apply(
        "knowledge-governance.sqlite"
    )
    return path


def _event(**overrides: object) -> LearningEvent:
    data: dict[str, object] = {
        "event_id": "le-1",
        "learner_id": "learner-a",
        "node_id": "node-a",
        "event_type": "review",
        "payload": {"rating": 4, "confidence": 0.9, "correct": True},
        "occurred_at": "2026-08-27T00:00:00+00:00",
        "idempotency_key": "idem-1",
        "source_system": "archeaxis",
    }
    data.update(overrides)
    return LearningEvent(**data)


def test_learning_events_are_idempotent_and_conflicts_fail_closed(tmp_path: Path) -> None:
    db = _db(tmp_path)
    first = append_event(db, _event())
    second = append_event(db, _event(event_id="le-retry"))

    assert first.event_id == "le-1"
    assert second.event_id == "le-1"
    with pytest.raises(EventConflictError, match="idempotency"):
        append_event(db, _event(event_id="le-evil", node_id="other"))


def test_human_state_replays_from_ordered_events(tmp_path: Path) -> None:
    db = _db(tmp_path)
    append_event(db, _event())
    append_event(
        db,
        _event(
            event_id="le-2",
            idempotency_key="idem-2",
            occurred_at="2026-08-27T00:01:00+00:00",
            event_type="quiz",
            payload={"correct": True, "confidence": 0.8},
        ),
    )
    append_event(
        db,
        _event(
            event_id="le-3",
            idempotency_key="idem-3",
            occurred_at="2026-08-27T00:02:00+00:00",
            event_type="teach_back",
            payload={"score": 0.85, "confidence": 0.9},
        ),
    )

    state = replay_human_state(db, learner_id="learner-a", node_id="node-a")
    assert state.event_count == 3
    assert state.level.value == "M4"
    assert state.evidence.quiz_pass is True
    assert state.evidence.teach_back_score == 0.85


def test_distillation_candidate_is_durable_but_unverified(tmp_path: Path) -> None:
    db = _db(tmp_path)
    append_event(db, _event())
    candidate = create_distillation_candidate(
        db,
        candidate_id="dc-1",
        source_event_id="le-1",
        source_card_id="card-a",
        payload={"proposal": "spaced repetition principle"},
    )

    assert candidate["status"] == "unverified"
    with sqlite3.connect(db) as connection:
        assert connection.execute(
            "SELECT status FROM distillation_candidates_v2 WHERE candidate_id='dc-1'"
        ).fetchone()[0] == "unverified"


def test_machine_competence_requires_verified_bundle_and_contiguous_receipts(
    tmp_path: Path,
) -> None:
    db = _db(tmp_path)
    now = datetime.now(UTC).isoformat()
    with sqlite3.connect(db) as connection:
        connection.execute(
            "INSERT INTO evidence_bundles_v1(id, claim_id, bundle_fingerprint, created_at) "
            "VALUES ('eb-1','claim-1','f-1',?)",
            (now,),
        )
        connection.commit()

    with pytest.raises(EvidenceGateError, match="verified"):
        record_machine_receipt(
            db,
            receipt_id="mr-k3",
            node_id="node-a",
            task_id="task-k3",
            level="K3",
            outcome="passed",
            evidence_bundle_id="eb-1",
            evaluator="eval-a",
            payload={"score": 1.0},
        )

    with sqlite3.connect(db) as connection:
        connection.execute(
            "INSERT INTO evidence_bundle_reviews_v1 "
            "(id,bundle_id,decision,reviewer_id,rationale,reviewed_at,created_at) "
            "VALUES ('ebr-1','eb-1','verified','human-a','checked',?,?)",
            (now, now),
        )
        connection.commit()

    record_machine_receipt(
        db,
        receipt_id="mr-k3",
        node_id="node-a",
        task_id="task-k3",
        level="K3",
        outcome="passed",
        evidence_bundle_id="eb-1",
        evaluator="eval-a",
        payload={"score": 1.0},
    )
    assert current_machine_level(db, node_id="node-a") is None

    for level in ("K0", "K1"):
        record_machine_receipt(
            db,
            receipt_id=f"mr-{level.lower()}",
            node_id="node-a",
            task_id=f"task-{level.lower()}",
            level=level,
            outcome="passed",
            evidence_bundle_id="eb-1",
            evaluator="eval-a",
            payload={"score": 1.0},
        )
    assert current_machine_level(db, node_id="node-a") == "K1"
