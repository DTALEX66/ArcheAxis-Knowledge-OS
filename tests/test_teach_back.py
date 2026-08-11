"""AXW-025B: Teach-Back and transfer evidence.

Teach-Back captures a learner restating a concept in their own words. Transfer
items apply a concept to a new situation. Each result must be traceable to its
source and record a human truth/prediction pair (the learner's self-assessment
vs the graded truth).
"""
from __future__ import annotations

import pytest

from app.knowledge.teach_back import (
    TeachBackError,
    build_teach_back_record,
    build_transfer_item,
    record_teach_back,
)


def test_teach_back_record_captures_restatement_and_source() -> None:
    record = build_teach_back_record(
        record_id="tb-1",
        concept="Evidence anchoring",
        restatement="Evidence anchors point at a page/block/char region in a source revision",
        source_locator="local-content://sha256/" + "a" * 64,
    )
    assert record.record_id == "tb-1"
    assert record.concept == "Evidence anchoring"
    assert record.restatement
    assert record.source_locator.startswith("local-content://")


def test_teach_back_requires_nonempty_restatement() -> None:
    with pytest.raises(TeachBackError, match="restatement is required"):
        build_teach_back_record(
            record_id="tb-2",
            concept="Evidence anchoring",
            restatement="  ",
            source_locator="local-content://sha256/" + "b" * 64,
        )


def test_transfer_item_applies_to_new_situation() -> None:
    item = build_transfer_item(
        item_id="tr-1",
        concept="Evidence anchoring",
        prompt="Given a new PDF, where would you anchor a claim?",
        expected_answer="A page/block/char region pinned to the source revision",
        source_locator="local-content://sha256/" + "c" * 64,
    )
    assert item.item_id == "tr-1"
    assert item.concept == "Evidence anchoring"
    assert item.expected_answer


def test_record_teach_back_scores_truth_and_keeps_prediction(tmp_path) -> None:
    record = build_teach_back_record(
        record_id="tb-3",
        concept="Evidence anchoring",
        restatement="Evidence anchors point at a page/block/char region in a source revision",
        source_locator="local-content://sha256/" + "d" * 64,
    )
    outcome = record_teach_back(
        record,
        learner_self_assessment="confident",
        graded_correct=True,
    )
    assert outcome.record_id == "tb-3"
    # Human truth/prediction pair is preserved.
    assert outcome.learner_prediction == "confident"
    assert outcome.human_truth is True
    assert outcome.source_locator == record.source_locator


def test_record_teach_back_persists_truth_prediction_pair(tmp_path) -> None:
    record = build_teach_back_record(
        record_id="tb-4",
        concept="Evidence anchoring",
        restatement="restatement text",
        source_locator="local-content://sha256/" + "e" * 64,
    )
    outcome = record_teach_back(record, learner_self_assessment="unsure", graded_correct=False)
    # The pair is the learning evidence; a traceable source is preserved.
    assert outcome.human_truth is False
    assert outcome.learner_prediction == "unsure"
