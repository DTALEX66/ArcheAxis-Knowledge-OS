"""Tests for the co-learning loop (bidirectional closed loop)."""
from __future__ import annotations

import pytest

from app.knowledge.co_learning_loop import (
    CoLearningError,
    DistillReceipt,
    TeachPlan,
    bidirectional_tick,
    run_distill,
    teach_plan,
)
from app.knowledge.dual_mastery import HumanEvidence, MachineEvidence
from app.knowledge.skill_assets import register_skill_asset


def test_teach_plan_builds_practice_items():
    plan = teach_plan(concept="BKT", reference="BKT 是隐马尔可夫模型",
                      key_terms=["hidden markov model", "slip"])
    assert isinstance(plan, TeachPlan)
    assert "BKT" in plan.quiz_item
    assert "BKT" in plan.transfer_item
    assert plan.key_terms == ["hidden markov model", "slip"]


def test_teach_plan_requires_concept_and_reference():
    with pytest.raises(CoLearningError):
        teach_plan(concept="", reference="x")
    with pytest.raises(CoLearningError):
        teach_plan(concept="x", reference="")


def test_bidirectional_tick_teach_human():
    result = bidirectional_tick(
        node_id="c1",
        human=HumanEvidence(reviewed=True),
        machine=MachineEvidence(has_raw_source=True, indexed=True, structured=True,
                                reasoned=True, procedural=True, callable=True,
                                verified=True),
        teach={"concept": "BKT", "reference": "BKT 是隐马尔可夫模型"},
    )
    assert result["action"] == "teach_human"
    assert result["payload"]["kind"] == "teach_plan"


def test_bidirectional_tick_teach_requires_material():
    with pytest.raises(CoLearningError):
        bidirectional_tick(
            node_id="c1",
            human=HumanEvidence(reviewed=True),
            machine=MachineEvidence(has_raw_source=True, indexed=True, structured=True,
                                    reasoned=True, procedural=True, callable=True,
                                    verified=True),
            teach=None,
        )


def test_bidirectional_tick_distill_human():
    result = bidirectional_tick(
        node_id="c2",
        human=HumanEvidence(reviewed=True, teaching_evidence=True),  # M7 expert
        machine=MachineEvidence(has_raw_source=True, indexed=True),   # K2
    )
    assert result["action"] == "distill_human"
    assert result["payload"]["kind"] == "distill_required"


def test_bidirectional_tick_review_evidence_outranks():
    # superseded evidence must win over a big mastery gap
    result = bidirectional_tick(
        node_id="c3",
        human=HumanEvidence(reviewed=True, teaching_evidence=True),
        machine=MachineEvidence(has_raw_source=True, indexed=True, structured=True,
                                reasoned=True, procedural=True, callable=True,
                                verified=True, adapted=True),
        has_superseding=True,
    )
    assert result["action"] == "review_evidence"


def test_run_distill_full_pipeline(tmp_path):
    db = tmp_path / "cl.sqlite"
    receipt = run_distill(
        db,
        statement="产品主体必须处于招商开屏广告的第一视觉层级",
        source_kind="interview", source_locator="designer-alex/2026-08-18",
        cases=[{"outcome": "consistent", "context": f"case-{i}"} for i in range(3)],
        rule_title="招商开屏视觉层级规则",
        conditions=["招商开屏广告", "产品识别"],
        action={"ensure": "product first visual layer"},
        skill_name="launch-banner-preflight", skill_version="1.0.0",
        allowed_tasks=["preflight-banner", "check-visual-hierarchy"],
        forbidden_tasks=["auto-print"],
    )
    assert isinstance(receipt, DistillReceipt)
    assert receipt.verification_outcome == "promoted"
    assert receipt.status == "skill_registered"
    assert receipt.rule_id is not None
    assert receipt.skill_asset_id is not None
    # skill is registered as candidate (reviewed=0) — activation still gated
    import sqlite3
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT reviewed, risk_level FROM skill_assets WHERE asset_id=?",
                       (receipt.skill_asset_id,)).fetchone()
    conn.close()
    assert row["reviewed"] == 0
    assert row["risk_level"] == "low"


def test_run_distill_not_promoted_with_single_case(tmp_path):
    db = tmp_path / "cl2.sqlite"
    receipt = run_distill(
        db,
        statement="单案例不能成为规则",
        source_kind="self_report", source_locator="user/1",
        cases=[{"outcome": "consistent", "context": "one"}],
        rule_title="t", conditions=["c"], action={"x": 1},
        skill_name="s", skill_version="1.0.0",
        allowed_tasks=["a"],
    )
    assert receipt.status == "not_promoted"
    assert receipt.rule_id is None
