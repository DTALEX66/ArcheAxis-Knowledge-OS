"""Human-to-AI distillation requires evidence, review, and reversible promotion."""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from app.learning.distillation import (
    DistillationApprovalError,
    approve_candidate,
    reject_candidate,
    revoke_promotion,
)
from app.learning.event_store import LearningEvent, append_event, create_distillation_candidate
from shared.migration_runner import MigrationOperator


def _db(tmp_path: Path) -> Path:
    db = tmp_path / "distill.sqlite"
    db.touch()
    MigrationOperator(db_path=db, backup_dir=tmp_path / "backups").apply(
        "knowledge-governance.sqlite"
    )
    append_event(
        db,
        LearningEvent(
            event_id="event-a",
            learner_id="learner-a",
            node_id="node-a",
            event_type="teach_back",
            payload={"score": 0.9, "principle": "retrieval strengthens memory"},
            occurred_at="2026-08-27T01:00:00+00:00",
            idempotency_key="event-a",
            source_system="archeaxis",
        ),
    )
    create_distillation_candidate(
        db,
        candidate_id="distill-a",
        source_event_id="event-a",
        source_card_id="card-a",
        payload={"principle": "retrieval strengthens memory"},
    )
    return db


def _verified_bundle(db: Path) -> None:
    with sqlite3.connect(db) as connection:
        connection.execute(
            "INSERT INTO evidence_bundles_v1 "
            "(id,claim_id,bundle_fingerprint,created_at) VALUES (?,?,?,?)",
            (
                "bundle-a",
                "distill-a",
                "f" * 64,
                "2026-08-27T01:02:00+00:00",
            ),
        )
        connection.execute(
            "INSERT INTO evidence_bundle_reviews_v1 "
            "(id,bundle_id,reviewer_id,decision,rationale,reviewed_at,created_at) "
            "VALUES (?,?,?,?,?,?,?)",
            (
                "bundle-review-a",
                "bundle-a",
                "human:owner",
                "verified",
                "checked source anchors",
                "2026-08-27T01:03:00+00:00",
                "2026-08-27T01:03:00+00:00",
            ),
        )
        connection.commit()


def test_approval_without_verified_evidence_fails_closed(tmp_path: Path) -> None:
    db = _db(tmp_path)
    with pytest.raises(DistillationApprovalError, match="verified evidence"):
        approve_candidate(
            db,
            candidate_id="distill-a",
            review_id="review-a",
            reviewer_id="human:owner",
            evidence_bundle_id="missing",
            rationale="looks useful",
            reviewed_at="2026-08-27T01:04:00+00:00",
        )


def test_approval_creates_only_reversible_machine_candidate(tmp_path: Path) -> None:
    db = _db(tmp_path)
    _verified_bundle(db)
    result = approve_candidate(
        db,
        candidate_id="distill-a",
        review_id="review-a",
        reviewer_id="human:owner",
        evidence_bundle_id="bundle-a",
        rationale="anchors and tests agree",
        reviewed_at="2026-08-27T01:04:00+00:00",
    )

    assert result["distillation_status"] == "promoted"
    assert result["machine_candidate_status"] == "CANDIDATE"
    assert result["machine_verified"] is False

    revoked = revoke_promotion(
        db,
        candidate_id="distill-a",
        review_id="review-revoke-a",
        reviewer_id="human:owner",
        rationale="new conflicting evidence",
        reviewed_at="2026-08-27T01:05:00+00:00",
    )
    assert revoked["distillation_status"] == "reviewed"
    assert revoked["machine_candidate_status"] == "REVOKED"


def test_rejection_records_review_without_machine_candidate(tmp_path: Path) -> None:
    db = _db(tmp_path)
    result = reject_candidate(
        db,
        candidate_id="distill-a",
        review_id="review-reject-a",
        reviewer_id="human:owner",
        rationale="insufficient generalization",
        reviewed_at="2026-08-27T01:04:00+00:00",
    )
    assert result["distillation_status"] == "rejected"
    assert result["machine_candidate_status"] is None
