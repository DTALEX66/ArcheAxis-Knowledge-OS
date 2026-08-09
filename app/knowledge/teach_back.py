"""AXW-025B: Teach-Back and transfer evidence.

Teach-Back captures a learner restating a concept in their own words. Transfer
items apply a concept to a new situation. Each result is traceable to its
source and records a human truth/prediction pair (the learner's self-assessed
prediction vs the graded human truth). Model confidence is never the learning
truth.
"""
from __future__ import annotations

from dataclasses import dataclass


class TeachBackError(ValueError):
    """Raised when a Teach-Back or transfer record is invalid."""


@dataclass(frozen=True)
class TeachBackRecord:
    record_id: str
    concept: str
    restatement: str
    source_locator: str


@dataclass(frozen=True)
class TransferItem:
    item_id: str
    concept: str
    prompt: str
    expected_answer: str
    source_locator: str


@dataclass(frozen=True)
class TeachBackOutcome:
    record_id: str
    learner_prediction: str
    human_truth: bool
    source_locator: str


def build_teach_back_record(
    *, record_id: str, concept: str, restatement: str, source_locator: str
) -> TeachBackRecord:
    if not record_id or not concept or not source_locator:
        raise TeachBackError("teach-back requires id, concept and source")
    if not restatement.strip():
        raise TeachBackError("restatement is required")
    return TeachBackRecord(
        record_id=record_id,
        concept=concept,
        restatement=restatement.strip(),
        source_locator=source_locator,
    )


def build_transfer_item(
    *, item_id: str, concept: str, prompt: str, expected_answer: str, source_locator: str
) -> TransferItem:
    if not item_id or not concept or not prompt or not source_locator:
        raise TeachBackError("transfer item requires id, concept, prompt and source")
    if not expected_answer.strip():
        raise TeachBackError("transfer item requires an expected answer")
    return TransferItem(
        item_id=item_id,
        concept=concept,
        prompt=prompt,
        expected_answer=expected_answer,
        source_locator=source_locator,
    )


def record_teach_back(
    record: TeachBackRecord,
    *,
    learner_self_assessment: str,
    graded_correct: bool,
) -> TeachBackOutcome:
    """Record a Teach-Back outcome with a human truth/prediction pair.

    The learner's self-assessment is a prediction; the graded_correct flag is
    the human truth. Both are preserved and tied to the record's source so the
    result is traceable.
    """
    if not learner_self_assessment:
        raise TeachBackError("learner self-assessment is required")
    return TeachBackOutcome(
        record_id=record.record_id,
        learner_prediction=learner_self_assessment,
        human_truth=graded_correct,
        source_locator=record.source_locator,
    )
