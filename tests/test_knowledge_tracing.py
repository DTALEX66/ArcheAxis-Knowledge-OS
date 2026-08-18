"""Tests for the BKT knowledge-tracing engine (absorbed from OATutor/pyBKT/pyKT)."""
from __future__ import annotations

import numpy as np
import pytest

from app.knowledge.knowledge_tracing import (
    BKTModel,
    BKTParameterError,
    estimate_mastery,
    fit_bkt,
)


def test_parameter_validation():
    with pytest.raises(BKTParameterError):
        BKTModel(skill_id="s", p_l0=1.5)
    with pytest.raises(BKTParameterError):
        BKTModel(skill_id="s", p_g=0.6, p_s=0.6)  # guess+slip >= 1


def test_correct_answer_increases_mastery():
    model = BKTModel(skill_id="s", p_l0=0.2, p_t=0.05, p_g=0.2, p_s=0.1)
    after = model.update(0.2, correct=True)
    assert after > 0.2


def test_incorrect_answer_decreases_mastery():
    model = BKTModel(skill_id="s", p_l0=0.5, p_t=0.0, p_g=0.1, p_s=0.2)
    after = model.update(0.5, correct=False)
    assert after < 0.5


def test_sequence_trajectory_is_monotone_given_perfect_performance():
    model = BKTModel(skill_id="s", p_l0=0.1, p_t=0.3, p_g=0.1, p_s=0.05)
    traj = model.predict_sequence([True, True, True, True, True])
    assert traj == sorted(traj, reverse=False)  # non-decreasing
    assert traj[-1] > 0.9


def test_probability_correct_is_sane():
    model = BKTModel(skill_id="s", p_l0=0.5, p_t=0.1, p_g=0.2, p_s=0.1)
    p = model.probability_correct(0.0)
    assert p == pytest.approx(0.2)  # pure guess when not learned
    p2 = model.probability_correct(1.0)
    assert p2 == pytest.approx(0.9)  # 1 - slip when learned


def test_fit_recovers_low_mastery_from_mostly_wrong():
    sequences = [[False, False, False, False], [False, False, False]]
    model = fit_bkt("hard-skill", sequences, max_iterations=300)
    assert estimate_mastery(model, [False, False, False]) < 0.5


def test_fit_recovers_high_mastery_from_mostly_correct():
    sequences = [[True, True, True, True], [True, True, True, True]]
    model = fit_bkt("easy-skill", sequences, max_iterations=300)
    assert estimate_mastery(model, [True, True, True]) > 0.5


def test_fit_converges_and_keeps_parameters_in_bounds():
    rng = np.random.default_rng(7)
    sequences = [[bool(rng.random() < 0.8) for _ in range(10)] for _ in range(8)]
    model = fit_bkt("noisy", sequences)
    for value in (model.p_l0, model.p_t, model.p_g, model.p_s):
        assert 0.0 < value < 1.0


def test_immutable_replace():
    model = BKTModel(skill_id="s")
    updated = model.replace(p_t=0.4)
    assert updated.p_t == pytest.approx(0.4)
    assert model.p_t == pytest.approx(0.1)
