"""TP-20260819 federation knowledge API tests (AA-P0-002 / AA-P1-001)."""
from __future__ import annotations

import pytest

from app.contracts.federation_v1 import (
    CandidateSubmissionV1,
    CandidateSubmissionItemV1,
    ExternalAssetRecordV1,
    KnowledgeQueryV1,
    ReviewDecisionV1,
)
from app.federation import service


def _submission(key: str = "sub-1") -> CandidateSubmissionV1:
    return CandidateSubmissionV1(
        idempotency_key=key,
        submitter="worklab-agent",
        items=[
            CandidateSubmissionItemV1(
                item_key="a", claim="费曼技巧四步法：目标、教学、回顾、简化",
                source_ref="provenance://worklab/rules/001", confidence=0.8, kind="rule",
            ),
            CandidateSubmissionItemV1(
                item_key="b", claim="间隔重复比集中学习记忆保持更久（FSRS 支持）",
                source_ref="provenance://ceshi/pdf/oxford-logic", confidence=0.6, kind="fact",
            ),
        ],
    )


def test_submit_receipt_and_hash_readback(tmp_path):
    db = tmp_path / "fed.sqlite"
    result = service.submit_candidates(db, _submission())
    assert result.duplicate is False
    assert result.receipt.status == "accepted"
    assert result.receipt.accepted == 2
    assert len(result.receipt.items_hash) == 64

    # receipt readback
    receipt = service.get_receipt(db, result.receipt.submission_id)
    assert receipt.items_hash == result.receipt.items_hash


def test_idempotency_duplicate(tmp_path):
    db = tmp_path / "fed.sqlite"
    first = service.submit_candidates(db, _submission("idem-1"))
    second = service.submit_candidates(db, _submission("idem-1"))
    assert second.duplicate is True
    assert second.receipt.submission_id == first.receipt.submission_id


def test_verified_query_and_promotion_gate(tmp_path):
    db = tmp_path / "fed.sqlite"
    res = service.submit_candidates(db, _submission("sub-q"))
    # candidate query first (no verified yet)
    cand = service.query_verified(db, KnowledgeQueryV1(query="费曼", kind="candidate"))
    assert cand.total == 1
    assert cand.items[0]["status"] == "candidate"
    # verified query empty before promotion
    verified = service.query_verified(db, KnowledgeQueryV1(query="费曼", kind="verified"))
    assert verified.total == 0

    # human-governed promotion (never auto)
    with pytest.raises(service.FederationError):
        service.promote_to_verified(db, "no-such-id", reviewer="reviewer-1")
    rows = None
    import sqlite3
    with sqlite3.connect(db) as conn:
        rows = conn.execute("SELECT id FROM federation_candidates_v1 WHERE item_key='a'").fetchone()
    service.promote_to_verified(db, rows[0], reviewer="reviewer-1")
    verified = service.query_verified(db, KnowledgeQueryV1(query="费曼", kind="verified"))
    assert verified.total == 1
    assert verified.items[0]["reviewer"] == "reviewer-1"


def test_pagination(tmp_path):
    db = tmp_path / "fed.sqlite"
    for i in range(3):
        sub = _submission(f"page-{i}")
        sub.items = sub.items[:1]
        sub.items[0].item_key = f"k{i}"
        sub.items[0].claim = f"记忆宫殿方法要点 {i}"
        service.submit_candidates(db, sub)
    p1 = service.query_verified(db, KnowledgeQueryV1(query="记忆宫殿", kind="all", page=1, page_size=2))
    assert p1.total == 3
    assert len(p1.items) == 2
    p2 = service.query_verified(db, KnowledgeQueryV1(query="记忆宫殿", kind="all", page=2, page_size=2))
    assert len(p2.items) == 1


def test_external_asset_record(tmp_path):
    db = tmp_path / "fed.sqlite"
    record = ExternalAssetRecordV1(
        asset_id="asset-1", uri="file:///D:/shared/design/method-card.svg",
        hash="deadbeef0123", media_type="image/svg+xml", source="designlab",
        rights="internal-use", extraction={"engine": "svg-parser", "version": "1"},
        derived_ids=["knowledge-1"],
    )
    service.register_external_asset(db, record)
    assets = service.list_external_assets(db)
    assert len(assets) == 1
    assert assets[0]["uri"].endswith("method-card.svg")
    assert assets[0]["hash"] == "deadbeef0123"
    assert assets[0]["derived_ids"] == ["knowledge-1"]


def test_review_is_versioned_idempotent_and_append_only(tmp_path):
    db = tmp_path / "fed.sqlite"
    service.submit_candidates(db, _submission("review-idem"))
    import sqlite3

    with sqlite3.connect(db) as conn:
        candidate_id = conn.execute(
            "SELECT id FROM federation_candidates_v1 WHERE item_key='a'"
        ).fetchone()[0]

    decision = ReviewDecisionV1(
        decision="verified",
        reviewer_id="reviewer-1",
        rationale="anchor and source were reviewed",
        expected_version=1,
        idempotency_key="review-1",
    )
    first = service.review_candidate(db, candidate_id, decision)
    second = service.review_candidate(db, candidate_id, decision)
    assert first == {"candidate_id": candidate_id, "status": "verified", "version": 2, "duplicate": False}
    assert second == {"candidate_id": candidate_id, "status": "verified", "version": 2, "duplicate": True}
    with sqlite3.connect(db) as conn:
        events = conn.execute(
            "SELECT decision, version FROM federation_candidate_events_v1 "
            "WHERE candidate_id=? ORDER BY version", (candidate_id,)
        ).fetchall()
    assert events == [("candidate", 1), ("verified", 2)]

    with pytest.raises(service.FederationError, match="version conflict"):
        service.review_candidate(
            db,
            candidate_id,
            decision.model_copy(update={"decision": "revoked", "idempotency_key": "review-2"}),
        )


def test_external_asset_rejects_conflicting_reuse_of_identity(tmp_path):
    db = tmp_path / "fed.sqlite"
    source = ExternalAssetRecordV1(
        asset_id="asset-1", uri="file:///source-a", hash="a", source="designlab"
    )
    service.register_external_asset(db, source)
    with pytest.raises(service.FederationError, match="different content"):
        service.register_external_asset(
            db, source.model_copy(update={"hash": "different"})
        )
