"""Tests for quiz + learning path (DeepTutor/OpenTutor/adaptive-KG absorption)."""
from __future__ import annotations

import pytest

from app.learning.quiz import QuizError, generate_quiz, grade_answer
from app.learning.learning_path import LearningPathError, build_path


# ── quiz ─────────────────────────────────────────────────────────────

def test_generate_quiz_recall_and_mcq():
    items = generate_quiz(concept="BKT", reference="BKT 是隐马尔可夫模型，含 guess 与 slip 参数",
                          key_terms=["guess", "slip"], other_concepts=["SRS", "IRT"])
    kinds = {item.kind for item in items}
    assert kinds == {"recall", "mcq"}
    mcq = next(i for i in items if i.kind == "mcq")
    assert mcq.answer in ("guess", "slip")
    assert len(mcq.distractors) >= 2


def test_quiz_requires_concept_and_reference():
    with pytest.raises(QuizError):
        generate_quiz(concept="", reference="x")
    with pytest.raises(QuizError):
        generate_quiz(concept="x", reference="")


def test_grade_recall_hit_and_miss():
    items = generate_quiz(concept="BKT", reference="BKT 是隐马尔可夫模型", key_terms=["隐马尔可夫"])
    recall = next(i for i in items if i.kind == "recall")
    hit = grade_answer(recall, "隐马尔可夫模型")
    assert hit.correct and hit.score == 1.0
    miss = grade_answer(recall, "我不知道")
    assert not miss.correct


def test_grade_mcq_exact_match():
    items = generate_quiz(concept="C", reference="核心术语是 alpha", key_terms=["alpha"],
                          other_concepts=["beta", "gamma"])
    mcq = next(i for i in items if i.kind == "mcq")
    assert grade_answer(mcq, "alpha").correct
    assert not grade_answer(mcq, "beta").correct


def test_grade_empty_answer():
    items = generate_quiz(concept="C", reference="x 是 y", key_terms=["x"])
    assert grade_answer(items[0], " ").score == 0.0


# ── learning path ─────────────────────────────────────────────────────

GRAPH = {
    "nodes": ["a", "b", "c", "d"],
    "edges": [("a", "b"), ("b", "c"), ("c", "d")],  # a→b→c→d prerequisites
}


def test_path_respects_prerequisites():
    path = build_path(goal="d", graph=GRAPH, mastery_map={"a": 0.9, "b": 0.2, "c": 0.3})
    concepts = [s.concept for s in path.steps]
    assert concepts == ["a", "b", "c", "d"]
    by_concept = {s.concept: s for s in path.steps}
    assert by_concept["a"].kind == "review"      # mastered
    assert by_concept["b"].kind == "must_learn"  # weak
    assert by_concept["d"].kind == "must_learn"  # goal


def test_path_flags_missing_mastery_as_gap():
    path = build_path(goal="c", graph=GRAPH, mastery_map={})
    gap = [s for s in path.steps if s.kind == "prerequisite_gap"]
    assert gap and gap[0].concept == "a"


def test_path_cycle_detected():
    cyclic = {"nodes": ["x", "y"], "edges": [("x", "y"), ("y", "x")]}
    with pytest.raises(LearningPathError, match="cycle"):
        build_path(goal="x", graph=cyclic)


def test_path_goal_missing():
    with pytest.raises(LearningPathError, match="not in graph"):
        build_path(goal="z", graph=GRAPH)
