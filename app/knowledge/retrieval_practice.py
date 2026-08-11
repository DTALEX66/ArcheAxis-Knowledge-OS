"""AXW-025A: learning objectives and retrieval practice.

A LearningObjective states what a learner must be able to do. RetrievalPractice
pairs a prompt with an answer and an explicit scoring rationale. Scoring is
driven ONLY by the recorded answer vs the expected answer — never by a model's
self-reported confidence (which is not learning accuracy).
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LearningObjective:
    objective_id: str
    title: str
    statement: str


@dataclass(frozen=True)
class RetrievalPractice:
    practice_id: str
    objective_id: str
    prompt: str
    answer: str
    rationale: str


@dataclass(frozen=True)
class PracticeScore:
    correct: bool
    accuracy_from_answer: bool


def build_learning_objective(
    *, objective_id: str, title: str, statement: str
) -> LearningObjective:
    if not objective_id or not title or not statement:
        raise ValueError("learning objective requires id, title and statement")
    return LearningObjective(
        objective_id=objective_id, title=title, statement=statement
    )


def build_retrieval_practice(
    *,
    practice_id: str,
    objective_id: str,
    prompt: str,
    answer: str,
    rationale: str,
) -> RetrievalPractice:
    if not practice_id or not objective_id or not prompt:
        raise ValueError("retrieval practice requires id, objective and prompt")
    if not answer or not rationale:
        raise ValueError("retrieval practice requires an answer and rationale")
    return RetrievalPractice(
        practice_id=practice_id,
        objective_id=objective_id,
        prompt=prompt,
        answer=answer,
        rationale=rationale,
    )


def score_retrieval_practice(
    practice: RetrievalPractice,
    *,
    submitted_answer: str,
    model_confidence: float,
) -> PracticeScore:
    """Score a retrieval practice against the recorded answer.

    AXW-025A: the outcome is determined by the submitted answer, not by
    model_confidence. model_confidence is accepted (for logging) but never
    influences whether the answer is correct.
    """
    if not submitted_answer.strip():
        raise ValueError("submitted answer is required")
    correct = submitted_answer.strip().lower() == practice.answer.strip().lower()
    return PracticeScore(correct=correct, accuracy_from_answer=True)
