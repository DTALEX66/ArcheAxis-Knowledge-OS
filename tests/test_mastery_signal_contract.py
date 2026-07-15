from __future__ import annotations

import pytest
from pydantic import ValidationError

MASTERY_SIGNAL_SCHEMA_ID = "https://cognitive-loop-os.local/contracts/v1/mastery-signal.schema.json"


def test_mastery_signal_v1_schema_requires_explicit_calculation_version():
    from app.contracts.v1 import MasterySignalV1

    payload = {
        "schema_version": "1.0.0",
        "calculation_version": "review-outcome-v1",
        "card_id": "card-schema",
        "is_mastered": False,
        "review_ids": [],
        "mistake_ids": [],
        "review_count": 0,
        "unresolved_mistake_ids": [],
        "latest_ease_factor": None,
        "latest_review_quality": None,
        "review_status": "draft",
    }

    assert MasterySignalV1.model_json_schema()["$id"] == MASTERY_SIGNAL_SCHEMA_ID
    with pytest.raises(ValidationError):
        MasterySignalV1(
            **{key: value for key, value in payload.items() if key != "calculation_version"}
        )
    with pytest.raises(ValidationError):
        MasterySignalV1(**{**payload, "calculation_version": "ease-threshold-v0"})
    with pytest.raises(ValidationError):
        MasterySignalV1(**{**payload, "invented": "forbidden"})


def test_mastery_signal_rejects_inconsistent_evidence_counts():
    from app.contracts.v1 import MasterySignalV1

    with pytest.raises(ValidationError, match="review_count must match review_ids"):
        MasterySignalV1(
            schema_version="1.0.0",
            calculation_version="review-outcome-v1",
            card_id="card-inconsistent",
            is_mastered=False,
            review_ids=["review-1"],
            mistake_ids=[],
            review_count=2,
            unresolved_mistake_ids=[],
            latest_ease_factor=2.5,
            latest_review_quality=3,
            review_status="reviewing",
        )


def test_mastery_signal_rejects_unbound_unresolved_mistakes():
    from app.contracts.v1 import MasterySignalV1

    with pytest.raises(ValidationError, match="unresolved mistakes must be present"):
        MasterySignalV1(
            schema_version="1.0.0",
            calculation_version="review-outcome-v1",
            card_id="card-inconsistent",
            is_mastered=False,
            review_ids=[],
            mistake_ids=[],
            review_count=0,
            unresolved_mistake_ids=["mistake-missing"],
            latest_ease_factor=None,
            latest_review_quality=None,
            review_status="draft",
        )


def test_mastery_signal_preserves_snapshot_evidence_for_a_mastered_card():
    from app.adapters.mastery_signal import from_learning_snapshots
    from app.contracts.v1 import MasterySignalV1

    card = {
        "card_id": "card-001",
        "title": "SM-2",
        "content": "Spaced repetition scheduling",
        "source_ids": ["source-001"],
        "tags": ["learning"],
        "review_status": "mastered",
    }
    reviews = [
        {
            "id": f"review-{index}",
            "card_id": "card-001",
            "quality": 4,
            "interval_days": index,
            "ease_factor": ease,
            "next_review_at": f"2026-07-{index + 10:02d}T00:00:00",
            "created_at": f"2026-07-{index:02d}T00:00:00",
        }
        for index, ease in ((1, 2.3), (2, 2.2), (3, 2.1))
    ]
    mistakes = [
        {
            "id": "mistake-001",
            "card_id": "card-001",
            "error_type": "recall_failure",
            "detail": "Forgot once",
            "source_topic": "SM-2",
            "resolved": True,
            "created_at": "2026-07-01T12:00:00",
        }
    ]

    signal = from_learning_snapshots(card, reviews, mistakes)

    assert isinstance(signal, MasterySignalV1)
    assert signal.card_id == "card-001"
    assert signal.is_mastered is True
    assert signal.review_ids == ["review-1", "review-2", "review-3"]
    assert signal.mistake_ids == ["mistake-001"]
    assert signal.review_count == 3
    assert signal.unresolved_mistake_ids == []
    assert signal.latest_ease_factor == 2.1
    assert signal.latest_review_quality == 4
    assert signal.review_status == "mastered"


def test_mastery_is_derived_from_review_outcome_not_status_or_ease_threshold():
    from app.adapters.mastery_signal import from_learning_snapshots

    reviews = [
        {
            "id": f"review-{index}",
            "card_id": "card-002",
            "quality": quality,
            "ease_factor": ease,
            "created_at": f"2026-07-{index:02d}T00:00:00",
        }
        for index, quality, ease in (
            (1, 4, 2.2),
            (2, 4, 2.0),
            (3, 4, 0.4),
        )
    ]

    grounded = from_learning_snapshots(
        {"card_id": "card-002", "review_status": "reviewing"}, reviews, []
    )
    latest_failed = from_learning_snapshots(
        {"card_id": "card-002", "review_status": "mastered"},
        [
            {**review, "quality": 2, "ease_factor": 3.0} if review["id"] == "review-3" else review
            for review in reviews
        ],
        [],
    )

    assert grounded.is_mastered is True
    assert grounded.latest_ease_factor == 0.4
    assert grounded.review_status == "reviewing"
    assert latest_failed.is_mastered is False
    assert latest_failed.latest_review_quality == 2


def test_contracts_facade_exports_mastery_signal_calculator():
    from app.adapters.mastery_signal import from_learning_snapshots
    from app.contracts.v1 import MasterySignalV1
    from app.facades import contracts

    assert contracts.MasterySignalV1 is MasterySignalV1
    assert contracts.from_learning_snapshots is from_learning_snapshots


def test_sqlite_card_snapshot_keeps_only_card_bound_unresolved_evidence():
    from app.adapters.mastery_signal import from_learning_snapshots

    card = {"id": "card-row-001", "review_status": "mastered"}
    reviews = [
        {
            "id": f"review-row-{index}",
            "card_id": "card-row-001",
            "quality": 5,
            "ease_factor": 2.5,
            "created_at": f"2026-07-{index:02d}T00:00:00",
        }
        for index in range(1, 4)
    ] + [
        {
            "id": "review-other",
            "card_id": "card-other",
            "quality": 5,
            "ease_factor": 2.5,
            "created_at": "2026-07-04T00:00:00",
        }
    ]
    mistakes = [
        {"id": "mistake-open", "card_id": "card-row-001", "resolved": False},
        {"id": "mistake-other", "card_id": "card-other", "resolved": False},
    ]

    signal = from_learning_snapshots(card, reviews, mistakes)

    assert signal.is_mastered is False
    assert signal.review_count == 3
    assert signal.review_ids == ["review-row-1", "review-row-2", "review-row-3"]
    assert signal.mistake_ids == ["mistake-open"]
    assert signal.unresolved_mistake_ids == ["mistake-open"]
