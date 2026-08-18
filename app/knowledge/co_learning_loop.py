"""Co-learning loop — the bidirectional closed loop of the 09 report.

Wires the engines into one orchestrator (report §4.6, §27):

    evaluate_node (dual_mastery)
        ├─ TEACH_HUMAN   → teach_plan()   (machine > human: machine teaches)
        ├─ DISTILL_HUMAN → run_distill()  (human > machine: human distills)
        ├─ COLLABORATE   → collaborative flag
        ├─ LEARN_FIRST   → both need learning
        └─ REVIEW_EVIDENCE → evidence flag (outranks everything)

run_distill  = distillation (principle → cases → verify → rule → skill proposal
               → skill-asset registration, low-risk, reviewed=0)
teach_plan   = from machine knowledge to a human learning plan: teach-back
               reference + key terms + quiz + transfer practice (M3/M4 evidence)

Governance: nothing auto-activates high-risk assets; skill registration stays
candidate (reviewed=0) until a human review; teach plans are suggestions, the
learner's human-truth feedback remains authoritative.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from app.knowledge.dual_mastery import (
    EvidenceMaturity,
    GapAction,
    HumanEvidence,
    HumanMasteryLevel,
    MachineEvidence,
    MachineMasteryLevel,
    evaluate_node,
)
from app.knowledge.distillation import (
    record_case,
    record_principle,
    verify_principle,
    promote_to_rule,
    propose_skill,
)
from app.knowledge.skill_assets import register_skill_asset


class CoLearningError(ValueError):
    """Raised when the co-learning loop receives invalid input."""


@dataclass(frozen=True)
class TeachPlan:
    """Machine → human: a concrete learning plan for one knowledge node."""

    concept: str
    teach_back_reference: str
    key_terms: list[str]
    quiz_item: str
    transfer_item: str
    source: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "concept": self.concept,
            "teach_back_reference": self.teach_back_reference,
            "key_terms": self.key_terms,
            "quiz_item": self.quiz_item,
            "transfer_item": self.transfer_item,
            "source": self.source,
        }


@dataclass(frozen=True)
class DistillReceipt:
    """Human → machine: receipt of the full distillation pipeline."""

    principle_id: str
    rule_id: str | None
    skill_asset_id: str | None
    verification_outcome: str
    status: str


def teach_plan(
    *,
    concept: str,
    reference: str,
    key_terms: list[str] | None = None,
    quiz_item: str | None = None,
    transfer_item: str | None = None,
    source: str = "machine-knowledge",
) -> TeachPlan:
    """Build a learning plan from machine knowledge (TEACH_HUMAN action)."""
    if not concept.strip() or not reference.strip():
        raise CoLearningError("teach plan requires concept and reference")
    return TeachPlan(
        concept=concept.strip(),
        teach_back_reference=reference.strip(),
        key_terms=[t.strip() for t in (key_terms or []) if t.strip()],
        quiz_item=quiz_item or f"用自己的话解释：{concept}",
        transfer_item=transfer_item or f"举一个新场景并说明如何应用：{concept}",
        source=source,
    )


def run_distill(
    db: str | Path,
    *,
    statement: str,
    source_kind: str,
    source_locator: str,
    cases: list[dict[str, str]],
    rule_title: str,
    conditions: list[str],
    action: dict[str, Any],
    skill_name: str,
    skill_version: str,
    allowed_tasks: list[str],
    forbidden_tasks: list[str] | None = None,
) -> DistillReceipt:
    """Full human→machine distillation: principle → cases → verify → rule → skill.

    The skill is registered as a low-risk candidate (reviewed=0) — activation
    still requires an explicit reviewed activation record (skill_assets gate).
    """
    if not cases or len(cases) < 1:
        raise CoLearningError("distillation requires at least one case")
    principle = record_principle(db, statement=statement, source_kind=source_kind,
                                 source_locator=source_locator)
    for i, case in enumerate(cases):
        outcome = str(case.get("outcome", "consistent"))
        context = str(case.get("context", f"case-{i}"))
        record_case(db, principle_id=principle.principle_id, outcome=outcome,  # type: ignore[arg-type]
                    context=context)
    verdict = verify_principle(db, principle.principle_id)
    if verdict.outcome != "promoted":
        return DistillReceipt(principle_id=principle.principle_id, rule_id=None,
                              skill_asset_id=None, verification_outcome=verdict.outcome,
                              status="not_promoted")
    rule = promote_to_rule(db, principle_id=principle.principle_id, title=rule_title,
                           conditions=conditions, action=action)
    proposal = propose_skill(rule, name=skill_name, version=skill_version,
                             allowed_tasks=allowed_tasks,
                             forbidden_tasks=list(forbidden_tasks or []),
                             source_url=f"distillation://{rule.rule_id}")
    asset = register_skill_asset(
        db, name=proposal.name, version=proposal.version,
        source_url=proposal.source_url, allowed_tasks=proposal.allowed_tasks,
        forbidden_tasks=proposal.forbidden_tasks, input_contract=proposal.input_contract,
        output_contract=proposal.output_contract, risk_level=proposal.risk_level,
        license=proposal.license, rollback_path=proposal.rollback_path,
    )
    return DistillReceipt(principle_id=principle.principle_id, rule_id=rule.rule_id,
                          skill_asset_id=asset.asset_id,
                          verification_outcome="promoted", status="skill_registered")


def bidirectional_tick(
    *,
    node_id: str,
    human: HumanEvidence,
    machine: MachineEvidence,
    distill_db: str | Path | None = None,
    teach: dict[str, Any] | None = None,
    evidence_verified: bool = True,
    valid_to: str | None = None,
    has_superseding: bool = False,
    has_contradiction: bool = False,
    now: str = "9999-12-31T00:00:00+00:00",
) -> dict[str, Any]:
    """Orchestrator: evaluate one node and dispatch by the gap action.

    Args:
        node_id: knowledge-node identifier.
        human/machine: evidence bundles for dual_mastery.
        distill_db: sqlite path for the distillation pipeline (required when the
                    action is DISTILL_HUMAN and automatic distillation is wanted).
        teach: teaching material {concept, reference, key_terms, quiz_item,
               transfer_item} required for TEACH_HUMAN.
        evidence_verified/valid_to/has_superseding/has_contradiction/now:
            evidence-maturity inputs (third axis; outranks mastery).

    Returns a dispatch record with the action, node state and payload.
    """
    node = evaluate_node(node_id, human, machine, evidence_verified=evidence_verified,
                         valid_to=valid_to, has_superseding=has_superseding,
                         has_contradiction=has_contradiction, now=now)
    result: dict[str, Any] = {"node_id": node_id, "action": node.action.value,
                              "state": node.to_display()}
    if node.action == GapAction.TEACH_HUMAN:
        if not teach:
            raise CoLearningError("TEACH_HUMAN requires teaching material")
        plan = teach_plan(concept=str(teach["concept"]), reference=str(teach["reference"]),
                          key_terms=teach.get("key_terms"), quiz_item=teach.get("quiz_item"),
                          transfer_item=teach.get("transfer_item"))
        result["payload"] = {"kind": "teach_plan", "plan": plan.as_dict()}
    elif node.action == GapAction.DISTILL_HUMAN:
        if distill_db is None:
            result["payload"] = {"kind": "distill_required",
                                 "reason": "human mastery exceeds machine mastery; run run_distill()"}
        else:
            result["payload"] = {"kind": "distill_required",
                                 "reason": "provide statement/source/cases to run_distill()"}
    elif node.action == GapAction.COLLABORATE:
        result["payload"] = {"kind": "collaborative_practice"}
    elif node.action == GapAction.REVIEW_EVIDENCE:
        result["payload"] = {"kind": "review_evidence",
                             "reason": "evidence is not current — outranks mastery"}
    else:
        result["payload"] = {"kind": "learn_first"}
    return result
