"""Tests for the Human Knowledge Distillation Engine (colleague-skill absorption)."""
from __future__ import annotations

import pytest

from app.knowledge.distillation import (
    DistillationError,
    MIN_VERIFICATION_CASES,
    record_case,
    record_principle,
    promote_to_rule,
    propose_skill,
    verify_principle,
)


def test_principle_record_and_case_flow(tmp_path):
    db = tmp_path / "dist.sqlite"
    p = record_principle(db, statement="产品主体必须处于招商开屏广告的第一视觉层级",
                         source_kind="interview", source_locator="designer-alex/2026-08-18")
    assert p.status == "candidate"
    for i in range(MIN_VERIFICATION_CASES):
        record_case(db, principle_id=p.principle_id, outcome="consistent",
                    context=f"case-{i}: banner rejected because product was small")
    verdict = verify_principle(db, p.principle_id)
    assert verdict.outcome == "promoted"
    assert verdict.consistent_cases == MIN_VERIFICATION_CASES
    assert verdict.total_cases == MIN_VERIFICATION_CASES


def test_single_anecdote_is_not_a_rule(tmp_path):
    db = tmp_path / "dist.sqlite"
    p = record_principle(db, statement="任何海报都要用大字号",
                         source_kind="self_report", source_locator="user/note-1")
    record_case(db, principle_id=p.principle_id, outcome="consistent", context="one case")
    verdict = verify_principle(db, p.principle_id)
    assert verdict.outcome == "insufficient_evidence"


def test_contradicting_cases_block_promotion(tmp_path):
    db = tmp_path / "dist.sqlite"
    p = record_principle(db, statement="深色背景永远更好",
                         source_kind="analysis", source_locator="design-review/1")
    for i in range(MIN_VERIFICATION_CASES):
        record_case(db, principle_id=p.principle_id,
                    outcome="consistent" if i % 2 == 0 else "contradicts", context=f"c{i}")
    verdict = verify_principle(db, p.principle_id)
    assert verdict.outcome != "promoted"
    assert verdict.consistency < 0.8


def test_only_verified_principles_promote_to_rule(tmp_path):
    db = tmp_path / "dist.sqlite"
    p = record_principle(db, statement="未验证原则", source_kind="interview",
                         source_locator="s1")
    with pytest.raises(DistillationError, match="only verified"):
        promote_to_rule(db, principle_id=p.principle_id, title="t",
                        conditions=["c"], action={"do": "x"})


def test_promote_to_rule_and_skill_proposal(tmp_path):
    db = tmp_path / "dist.sqlite"
    p = record_principle(db, statement="印刷文件必须嵌入字体",
                         source_kind="interview", source_locator="print-expert")
    for i in range(MIN_VERIFICATION_CASES):
        record_case(db, principle_id=p.principle_id, outcome="consistent", context=f"job-{i}")
    assert verify_principle(db, p.principle_id).outcome == "promoted"
    rule = promote_to_rule(db, principle_id=p.principle_id, title="嵌入字体规则",
                           conditions=["pdf", "has text"], action={"embed": "fonts"})
    proposal = propose_skill(rule, name="print-preflight", version="1.0.0",
                             allowed_tasks=["preflight-check", "embed-fonts"],
                             forbidden_tasks=["auto-print"])
    assert proposal.risk_level == "low"
    assert "preflight-check" in proposal.allowed_tasks
    assert proposal.input_contract["rule_id"] == rule.rule_id


def test_validation_rules(tmp_path):
    db = tmp_path / "dist.sqlite"
    with pytest.raises(DistillationError):
        record_principle(db, statement="", source_kind="interview", source_locator="s")
    with pytest.raises(DistillationError):
        record_principle(db, statement="x", source_kind="bogus", source_locator="s")
    p = record_principle(db, statement="x", source_kind="interview", source_locator="s")
    with pytest.raises(DistillationError):
        record_case(db, principle_id="missing", outcome="consistent", context="c")
