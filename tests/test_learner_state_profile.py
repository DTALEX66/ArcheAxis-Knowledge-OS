"""Tests for learner state + profile (D3 R1/R2)."""
from __future__ import annotations

import pytest

from app.knowledge.learner_state import KnowledgeState, knowledge_state, recall_probability
from app.knowledge.learner_profile import LearnerProfile


def test_recall_decays_over_time():
    assert recall_probability(stability_days=21.0, elapsed_days=0) == pytest.approx(1.0)
    r7 = recall_probability(21.0, 7.0)
    r30 = recall_probability(21.0, 30.0)
    assert 0.0 < r30 < r7 < 1.0


def test_knowledge_state_fuses_bkt_and_recall():
    state = knowledge_state(bkt_posterior=0.8, stability_days=21.0, elapsed_days=0)
    assert isinstance(state, KnowledgeState)
    assert state.mastery == pytest.approx(0.8)
    decayed = knowledge_state(bkt_posterior=0.8, stability_days=21.0, elapsed_days=30.0)
    assert decayed.mastery < state.mastery
    assert decayed.forgetting_risk > state.forgetting_risk


def test_knowledge_state_unreviewed():
    state = knowledge_state(bkt_posterior=0.6, stability_days=0.0, elapsed_days=0.0)
    assert state.mastery == pytest.approx(0.3)  # half-tempered prior


def test_knowledge_state_validation():
    with pytest.raises(ValueError):
        knowledge_state(bkt_posterior=2.0, stability_days=1.0, elapsed_days=0.0)


def test_profile_tracks_accuracy_and_calibration():
    profile = LearnerProfile()
    # confident and correct → well calibrated
    for _ in range(5):
        profile.update("bkt", confidence=0.9, correct=True)
    assert profile.calibration_error("bkt") < 0.15
    # overconfident → big calibration error
    for _ in range(5):
        profile.update("fsrs", confidence=0.9, correct=False)
    assert profile.calibration_error("fsrs") > 0.5


def test_profile_summary_rows():
    profile = LearnerProfile()
    profile.update("a", confidence=0.5, correct=True)
    rows = profile.summary()
    assert len(rows) == 1
    assert rows[0]["concept"] == "a"
    assert rows[0]["accuracy"] == 1.0


def test_profile_validation():
    profile = LearnerProfile()
    with pytest.raises(ValueError):
        profile.update("x", confidence=2.0, correct=True)
