"""Tests for the capability registry + orchestrator (DeepTutor absorption)."""
from __future__ import annotations

import pytest

from app.knowledge.dual_mastery import (
    GapAction,
    HumanEvidence,
    KnowledgeNodeState,
    MachineEvidence,
    evaluate_node,
    human_mastery_level,
    machine_mastery_level,
)
from app.learning.capabilities import (
    Capability,
    CapabilityError,
    CapabilityRegistry,
    default_registry,
    mastery_gate,
)


def test_register_and_list():
    registry = CapabilityRegistry()
    registry.register(Capability("a", "desc", lambda p: {"ok": True}))
    assert [c["name"] for c in registry.list()] == ["a"]
    with pytest.raises(CapabilityError, match="already registered"):
        registry.register(Capability("a", "d", lambda p: {}))


def test_route_by_intent_keywords():
    registry = default_registry()
    assert registry.route("我想学 BKT").name == "learn"
    assert registry.route("来点测验").name == "quiz"
    assert registry.route("构建学习路径").name == "path"
    assert registry.route("我复述给你听").name == "teach_back"
    with pytest.raises(CapabilityError, match="no capability"):
        registry.route("zzz qqq")


def test_mastery_gate_orders_teaching():
    registry = default_registry()
    node = evaluate_node(
        "c1",
        HumanEvidence(reviewed=True),
        MachineEvidence(has_raw_source=True, indexed=True, structured=True,
                        reasoned=True, procedural=True, callable=True, verified=True),
        evidence_verified=True,
    )
    assert node.action == GapAction.TEACH_HUMAN
    order = mastery_gate(node, registry)
    assert order == ["learn", "quiz", "teach_back"]


def test_mastery_gate_distill_and_evidence():
    registry = default_registry()
    distill_node = evaluate_node("c2", HumanEvidence(reviewed=True, teaching_evidence=True),
                                 MachineEvidence(has_raw_source=True, indexed=True),
                                 evidence_verified=True)
    assert mastery_gate(distill_node, registry) == ["distill"]
    evidence_node = KnowledgeNodeState(
        node_id="c3", human_level=human_mastery_level(HumanEvidence(reviewed=True)),
        machine_level=machine_mastery_level(MachineEvidence(has_raw_source=True)),
        evidence="outdated", action=GapAction.REVIEW_EVIDENCE, delta=0)
    assert mastery_gate(evidence_node, registry) == ["evidence"]


def test_learn_capability_invokes_modules():
    registry = default_registry()
    result = registry.route("教我这个概念").invoke(
        {"concept": "BKT", "reference": "BKT 是隐马尔可夫模型，含 guess 与 slip 参数",
         "key_terms": ["guess", "slip"]})
    assert result["kind"] == "learn"
    assert result["quiz"]


def test_high_risk_blocked():
    with pytest.raises(ValueError, match="review"):
        Capability("x", "d", lambda p: {}, risk="high").invoke({})
