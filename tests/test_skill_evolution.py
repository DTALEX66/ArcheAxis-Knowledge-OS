"""Tests for the skill evolution loop (Hermes Self-Evolution / SkillRL absorption)."""
from __future__ import annotations

import pytest

from app.knowledge.skill_evolution import (
    MIN_EVALUATION_USAGES,
    SkillEvolutionError,
    apply_patch,
    evaluate_skill,
    propose_patch,
    record_usage,
    verify_patch,
)


def _populate(db, skill_id: str, *, successes: int, failures: int):
    for _ in range(successes):
        record_usage(db, skill_id=skill_id, task="t", outcome="success")
    for i in range(failures):
        record_usage(db, skill_id=skill_id, task="t", outcome="failure",
                     failure_analysis=f"analysis-{i}")


def test_insufficient_data_until_min_usages(tmp_path):
    db = tmp_path / "se.sqlite"
    record_usage(db, skill_id="sk1", task="t", outcome="success")
    assert evaluate_skill(db, "sk1").verdict == "insufficient_data"


def test_keep_when_mostly_successful(tmp_path):
    db = tmp_path / "se.sqlite"
    _populate(db, "sk-good", successes=8, failures=1)
    ev = evaluate_skill(db, "sk-good")
    assert ev.verdict == "keep"
    assert ev.success_rate >= 0.8


def test_needs_patch_when_flaky(tmp_path):
    db = tmp_path / "se.sqlite"
    _populate(db, "sk-flaky", successes=4, failures=4)
    assert evaluate_skill(db, "sk-flaky").verdict == "needs_patch"


def test_retire_when_broken(tmp_path):
    db = tmp_path / "se.sqlite"
    _populate(db, "sk-broken", successes=1, failures=6)
    assert evaluate_skill(db, "sk-broken").verdict == "retire"


def test_patch_gate_requires_passing_tests(tmp_path):
    db = tmp_path / "se.sqlite"
    patch = propose_patch(db, skill_id="sk1", analysis="fails on empty input",
                          payload={"precondition": "non-empty"})
    assert patch.status == "proposed"
    with pytest.raises(SkillEvolutionError, match="non-empty tests"):
        verify_patch(db, patch.patch_id, test_results={"tests": []})
    rejected = verify_patch(db, patch.patch_id, test_results={
        "tests": [{"name": "t1", "passed": False}]})
    assert rejected == "rejected"
    # re-propose and pass
    patch2 = propose_patch(db, skill_id="sk1", analysis="a2", payload={"fix": 1})
    approved = verify_patch(db, patch2.patch_id, test_results={
        "tests": [{"name": "t1", "passed": True}, {"name": "t2", "passed": True}]})
    assert approved == "approved"


def test_apply_only_after_approval(tmp_path):
    db = tmp_path / "se.sqlite"
    patch = propose_patch(db, skill_id="sk1", analysis="a", payload={"fix": 1})
    with pytest.raises(SkillEvolutionError, match="approved"):
        apply_patch(db, patch.patch_id, new_version="2.0.0")
    verify_patch(db, patch.patch_id, test_results={"tests": [{"name": "t", "passed": True}]})
    result = apply_patch(db, patch.patch_id, new_version="2.0.0")
    assert result["version"] == "2.0.0"
    assert result["supersedes"] == "sk1"
    assert result["payload"] == {"fix": 1}


def test_high_risk_and_oversize_patches_rejected(tmp_path):
    db = tmp_path / "se.sqlite"
    with pytest.raises(SkillEvolutionError, match="high-risk"):
        propose_patch(db, skill_id="sk-hi", analysis="a", payload={"x": 1}, risk_level="high")
    with pytest.raises(SkillEvolutionError, match="size limit"):
        propose_patch(db, skill_id="sk-big", analysis="a", payload={"blob": "x" * (70 * 1024)})
