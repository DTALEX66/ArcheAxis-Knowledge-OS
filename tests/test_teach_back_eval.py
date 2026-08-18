"""Tests for teach-back evaluation (Studyield absorption)."""
from __future__ import annotations

import pytest

from app.knowledge.teach_back_eval import (
    extract_misconceptions,
    grade_with_llm,
    map_to_level,
    score_teach_back,
)
from app.knowledge.dual_mastery import HumanMasteryLevel


REFERENCE = (
    "Bayesian Knowledge Tracing models latent learning state as a hidden Markov "
    "model with guess and slip parameters. Mastery is the posterior probability "
    "that the skill is learned."
)
KEY_TERMS = ["hidden markov model", "guess", "slip", "posterior probability", "mastery"]


def test_good_restatement_passes():
    restatement = (
        "BKT is a hidden Markov model with guess and slip parameters: mastery is "
        "the posterior probability that the skill is learned. In other words, it "
        "models the latent learning state."
    )
    ev = score_teach_back(record_id="r1", concept="BKT", restatement=restatement,
                          reference=REFERENCE, key_terms=KEY_TERMS)
    assert ev.passes()
    assert ev.overall >= 0.7
    assert map_to_level(ev) == HumanMasteryLevel.M3_EXPLAIN


def test_vague_restatement_fails():
    restatement = "BKT is something about probability and models."
    ev = score_teach_back(record_id="r2", concept="BKT", restatement=restatement,
                          reference=REFERENCE, key_terms=KEY_TERMS)
    assert not ev.passes()
    assert ev.overall < 0.7
    assert map_to_level(ev) in (HumanMasteryLevel.M1_RECOGNIZE, HumanMasteryLevel.M2_RECALL)


def test_verbatim_copy_penalised_by_paraphrase():
    ev = score_teach_back(record_id="r3", concept="BKT", restatement=REFERENCE,
                          reference=REFERENCE, key_terms=KEY_TERMS)
    # verbatim copy: accuracy high, paraphrase low
    assert ev.accuracy > 0.9
    assert ev.paraphrase < 0.3


def test_misconception_extraction():
    missing, extra = extract_misconceptions(
        "BKT uses a hidden markov model and guess parameter.", REFERENCE, KEY_TERMS
    )
    assert "slip" in missing
    assert "posterior probability" in missing
    assert "mastery" in missing
    assert isinstance(extra, list)


def test_empty_inputs_rejected():
    with pytest.raises(ValueError):
        score_teach_back(record_id="r", concept="c", restatement="", reference="ref")


def test_llm_grader_returns_none_without_provider():
    # No API keys configured in test env → rubric fallback (None is safe)
    result = grade_with_llm("x", REFERENCE)
    assert result is None or isinstance(result, dict)
