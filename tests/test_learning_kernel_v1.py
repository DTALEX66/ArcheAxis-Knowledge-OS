"""R6 A08 human learning kernel contract tests."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.contracts.learning_kernel_v1 import LearningKernelReceiptV1


def _payload(**overrides):
    payload = {
        "item_key": "card-1",
        "question_version": "q-2",
        "knowledge_version": "k-3",
        "source_anchor_ids": ["anc-1"],
        "exposure_id": "exposure-1",
        "client_event_id": "event-1",
        "correct": True,
        "rating": 3,
        "state_before": "learning",
        "state_after": "review",
        "due_before": "2026-09-19T00:00:00+00:00",
        "due_after": "2026-09-21T00:00:00+00:00",
        "scheduled_days": 2,
        "scheduler": "fsrs",
        "scheduler_version": "6",
        "restart_key": "event-1",
    }
    payload.update(overrides)
    return payload


def test_learning_receipt_binds_source_and_idempotent_review_ids():
    receipt = LearningKernelReceiptV1.model_validate(_payload())
    assert receipt.source_anchor_ids == ["anc-1"]
    assert receipt.restart_key == receipt.client_event_id


def test_incorrect_exposure_requires_again_rating():
    with pytest.raises(ValidationError, match="incorrect exposure"):
        LearningKernelReceiptV1.model_validate(_payload(correct=False, rating=2))
    failed = LearningKernelReceiptV1.model_validate(_payload(correct=False, rating=1, state_after="relearning"))
    assert failed.state_after == "relearning"


def test_correct_exposure_cannot_be_again_and_retry_key_cannot_drift():
    with pytest.raises(ValidationError, match="correct exposure"):
        LearningKernelReceiptV1.model_validate(_payload(rating=1))
    with pytest.raises(ValidationError, match="restart_key"):
        LearningKernelReceiptV1.model_validate(_payload(restart_key="new-event"))


def test_versioned_schema_is_present_and_requires_anchor_ids():
    import json
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    schema = json.loads((root / "packages/contracts/learning/v1/learning-kernel.schema.json").read_text(encoding="utf-8"))
    assert schema["properties"]["schema"]["const"] == "archeaxis.learning-kernel/v1"
    assert "source_anchor_ids" in schema["required"]
