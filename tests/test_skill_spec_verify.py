"""Tests for SKILL.md spec + refined verify gate (A4 absorption items)."""
from __future__ import annotations

import pytest

from app.knowledge.skill_spec import (
    SkillDoc,
    SkillSpecError,
    from_expert_rule,
    parse_skill_doc,
)
from app.knowledge.distillation import ExpertRule
from app.knowledge.skill_evolution import propose_patch, verify_patch


# ── skill spec ───────────────────────────────────────────────────────

def test_generate_and_parse_roundtrip():
    rule = ExpertRule(rule_id="rule_x", title="嵌入字体规则",
                      conditions=["pdf"], action={"embed": "fonts"},
                      principle_ids=["p1"], confidence=0.9)
    doc = from_expert_rule(rule, skill_name="print-preflight", version="1.0.0",
                           allowed_tasks=["preflight-check"], persona="严谨的印前专家")
    markdown = doc.to_markdown()
    assert markdown.startswith("---")
    assert "name: print-preflight" in markdown
    parsed = parse_skill_doc(markdown)
    assert parsed.name == "print-preflight"
    assert "Persona" in parsed.sections
    assert "Preflight" in parsed.sections or "preflight-check" in markdown


def test_parse_requires_frontmatter():
    with pytest.raises(SkillSpecError, match="frontmatter"):
        parse_skill_doc("# no frontmatter here")


def test_parse_requires_required_fields():
    with pytest.raises(SkillSpecError, match="missing"):
        parse_skill_doc("---\nname: x\n---\n## Rules\n- r\n")


def test_skill_doc_is_valid_markdown():
    rule = ExpertRule(rule_id="r", title="t", conditions=["c"],
                      action={"a": 1}, principle_ids=["p"], confidence=0.8)
    doc = from_expert_rule(rule, skill_name="s", version="0.1.0")
    assert isinstance(doc, SkillDoc)
    assert doc.risk_level == "low"


# ── verify gate regression ───────────────────────────────────────────

def test_verify_approves_without_regression(tmp_path):
    db = tmp_path / "se.sqlite"
    patch = propose_patch(db, skill_id="sk", analysis="a", payload={"fix": 1})
    status = verify_patch(db, patch.patch_id, test_results={
        "tests": [{"name": "t1", "passed": True}],
        "benchmark": {"accuracy": {"old": 0.8, "new": 0.85}},
    })
    assert status == "approved"


def test_verify_rejects_on_regression(tmp_path):
    db = tmp_path / "se2.sqlite"
    patch = propose_patch(db, skill_id="sk", analysis="a", payload={"fix": 1})
    status = verify_patch(db, patch.patch_id, test_results={
        "tests": [{"name": "t1", "passed": True}],
        "benchmark": {"accuracy": {"old": 0.8, "new": 0.7}},  # regressed 12.5%
    })
    assert status == "rejected"


def test_verify_rejects_within_tolerance(tmp_path):
    db = tmp_path / "se3.sqlite"
    patch = propose_patch(db, skill_id="sk", analysis="a", payload={"fix": 1})
    status = verify_patch(db, patch.patch_id, test_results={
        "tests": [{"name": "t1", "passed": True}],
        "benchmark": {"accuracy": {"old": 0.8, "new": 0.79}},  # -1.25% < tolerance
    })
    assert status == "approved"
