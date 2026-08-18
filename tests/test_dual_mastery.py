"""Tests for the dual-mastery three-axis model (09 report §4.4-4.6)."""
from __future__ import annotations

import pytest

from app.knowledge.dual_mastery import (
    EvidenceMaturity,
    GapAction,
    HumanEvidence,
    HumanMasteryLevel,
    KnowledgeNodeState,
    MachineEvidence,
    MachineMasteryLevel,
    evaluate_node,
    evidence_maturity,
    human_mastery_level,
    machine_mastery_level,
    mastery_gap,
)


def test_human_level_progression():
    assert human_mastery_level(HumanEvidence()) == HumanMasteryLevel.M0_SEEN
    assert human_mastery_level(HumanEvidence(reviewed=True)) == HumanMasteryLevel.M1_RECOGNIZE
    assert human_mastery_level(HumanEvidence(reviewed=True, review_state="review", stability_days=10.0))         == HumanMasteryLevel.M2_RECALL
    assert human_mastery_level(HumanEvidence(reviewed=True, teach_back_score=0.85))         == HumanMasteryLevel.M3_EXPLAIN
    assert human_mastery_level(HumanEvidence(reviewed=True, quiz_pass=True))         == HumanMasteryLevel.M4_SOLVE
    assert human_mastery_level(HumanEvidence(reviewed=True, transfer_pass=True))         == HumanMasteryLevel.M5_TRANSFER
    assert human_mastery_level(HumanEvidence(reviewed=True, creation_evidence=True))         == HumanMasteryLevel.M6_CREATE
    assert human_mastery_level(HumanEvidence(reviewed=True, teaching_evidence=True))         == HumanMasteryLevel.M7_EXPERT


def test_machine_level_progression():
    assert machine_mastery_level(MachineEvidence()) == MachineMasteryLevel.K0_RAW
    assert machine_mastery_level(MachineEvidence(has_raw_source=True)) == MachineMasteryLevel.K1_INDEXED
    assert machine_mastery_level(MachineEvidence(has_raw_source=True, indexed=True))         == MachineMasteryLevel.K2_STRUCTURED
    full = MachineEvidence(has_raw_source=True, indexed=True, structured=True, reasoned=True,
                           procedural=True, callable=True, verified=True, adapted=True)
    assert machine_mastery_level(full) == MachineMasteryLevel.K8_TRANSFERABLE


def test_evidence_maturity_priority():
    # superseding wins over everything
    assert evidence_maturity(verified=True, valid_to=None, has_superseding=True,
                             has_contradiction=False, now="2026-08-18T00:00:00+00:00")         == "outdated"
    # expiry
    assert evidence_maturity(verified=True, valid_to="2026-08-01T00:00:00+00:00",
                             has_superseding=False, has_contradiction=False,
                             now="2026-08-18T00:00:00+00:00") == "outdated"
    # contradiction
    assert evidence_maturity(verified=True, valid_to=None, has_superseding=False,
                             has_contradiction=True, now="2026-08-18T00:00:00+00:00") == "contested"
    assert evidence_maturity(verified=False, valid_to=None, has_superseding=False,
                             has_contradiction=False, now="2026-08-18T00:00:00+00:00") == "unverified"
    assert evidence_maturity(verified=True, valid_to=None, has_superseding=False,
                             has_contradiction=False, now="2026-08-18T00:00:00+00:00") == "current"


def test_gap_actions():
    # machine > human → teach
    action, delta = mastery_gap(HumanMasteryLevel.M1_RECOGNIZE, MachineMasteryLevel.K6_VERIFIED, EvidenceMaturity.CURRENT)
    assert action == GapAction.TEACH_HUMAN and delta > 0
    # human > machine → distill
    action, delta = mastery_gap(HumanMasteryLevel.M7_EXPERT, MachineMasteryLevel.K2_STRUCTURED, EvidenceMaturity.CURRENT)
    assert action == GapAction.DISTILL_HUMAN and delta < 0
    # both strong → collaborate
    action, _ = mastery_gap(HumanMasteryLevel.M6_CREATE, MachineMasteryLevel.K6_VERIFIED, EvidenceMaturity.CURRENT)
    assert action == GapAction.COLLABORATE
    # stale evidence outranks everything
    action, _ = mastery_gap(HumanMasteryLevel.M7_EXPERT, MachineMasteryLevel.K8_TRANSFERABLE, EvidenceMaturity.OUTDATED)
    assert action == GapAction.REVIEW_EVIDENCE


def test_evaluate_node_three_axis():
    node = evaluate_node(
        "concept:photoshop-mask",
        HumanEvidence(reviewed=True, teach_back_score=0.9),
        MachineEvidence(has_raw_source=True, indexed=True, structured=True, reasoned=True,
                        procedural=True, callable=True, verified=True),
    )
    assert isinstance(node, KnowledgeNodeState)
    assert node.human_level == HumanMasteryLevel.M3_EXPLAIN
    assert node.machine_level == MachineMasteryLevel.K7_ADAPTIVE
    assert node.action == GapAction.TEACH_HUMAN
    display = node.to_display()
    assert display["action"] == "teach_human"
    assert display["evidence"] == "current"


def test_stale_evidence_reviewed_first():
    node = evaluate_node("x", HumanEvidence(), MachineEvidence(),
                         evidence_verified=True, has_superseding=True)
    assert node.action == GapAction.REVIEW_EVIDENCE
