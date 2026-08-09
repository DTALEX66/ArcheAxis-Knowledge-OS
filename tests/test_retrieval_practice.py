"""AXW-025A: learning objectives and retrieval practice.

An objective states what a learner must be able to do. Retrieval practice
pairs a prompt with an answer and an explicit scoring rationale. Model
confidence is never treated as learning accuracy — only the recorded answer
and rationale drive the outcome.
"""
from __future__ import annotations

import pytest

from app.knowledge.retrieval_practice import (
    build_learning_objective,
    build_retrieval_practice,
    score_retrieval_practice,
)


def test_learning_objective_captures_goal_and_success() -> None:
    obj = build_learning_objective(
        objective_id="obj-1",
        title="PDF evidence anchoring",
        statement="Learner can extract a page-level evidence anchor from a PDF",
    )
    assert obj.objective_id == "obj-1"
    assert obj.title == "PDF evidence anchoring"
    assert obj.statement


def test_retrieval_practice_has_answer_and_rationale() -> None:
    practice = build_retrieval_practice(
        practice_id="pr-1",
        objective_id="obj-1",
        prompt="Where does an EvidenceAnchor point?",
        answer="A page/block/char region within a source revision",
        rationale="Anchors must pin to a source version, not just text",
    )
    assert practice.practice_id == "pr-1"
    assert practice.objective_id == "obj-1"
    assert practice.prompt
    assert practice.answer
    assert practice.rationale


def test_scoring_uses_answer_not_model_confidence() -> None:
    """AXW-025A: learning accuracy comes from the recorded answer vs the
    expected answer, never from a model's self-reported confidence."""
    practice = build_retrieval_practice(
        practice_id="pr-2",
        objective_id="obj-1",
        prompt="What is the closed loop?",
        answer="Source to evidence to learning to AI reuse",
        rationale="The loop must close from source to governed AI assets",
    )
    # A learner gives a correct answer but the model reported low confidence.
    result = score_retrieval_practice(
        practice,
        submitted_answer="Source to evidence to learning to AI reuse",
        model_confidence=0.2,  # must not lower the score
    )
    assert result.correct is True
    assert result.accuracy_from_answer is True

    # A wrong answer with high model confidence must still be wrong.
    wrong = score_retrieval_practice(
        practice,
        submitted_answer="Random text",
        model_confidence=0.99,
    )
    assert wrong.correct is False


def test_scoring_rejects_missing_answer() -> None:
    practice = build_retrieval_practice(
        practice_id="pr-3",
        objective_id="obj-1",
        prompt="p",
        answer="a",
        rationale="r",
    )
    with pytest.raises(ValueError, match="submitted answer is required"):
        score_retrieval_practice(practice, submitted_answer="", model_confidence=0.5)
