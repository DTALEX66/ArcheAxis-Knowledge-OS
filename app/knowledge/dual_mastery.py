"""Dual Mastery model — the three-axis knowledge node from the 09 research report.

Axis 1  HUMAN MASTERY   M0..M7   (how well the person masters the node)
Axis 2  MACHINE MASTERY K0..K8   (how far the machine has proceduralised the node)
Axis 3  EVIDENCE MATURITY        (how current / verified the node's facts are)

Mastery Gap Engine: delta between machine and human mastery decides the next
action — teach the human (machine > human), distill the human (human > machine),
or collaborate (both strong). Outdated evidence outranks both.

Design rules:
    * pure calculation — no persistence, no provider calls
    * every level is derived from explicit evidence inputs, never asserted
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict


class HumanMasteryLevel(str, Enum):
    M0_SEEN = "M0"
    M1_RECOGNIZE = "M1"
    M2_RECALL = "M2"
    M3_EXPLAIN = "M3"
    M4_SOLVE = "M4"
    M5_TRANSFER = "M5"
    M6_CREATE = "M6"
    M7_EXPERT = "M7"


class MachineMasteryLevel(str, Enum):
    K0_RAW = "K0"
    K1_INDEXED = "K1"
    K2_STRUCTURED = "K2"
    K3_REASONABLE = "K3"
    K4_PROCEDURAL = "K4"
    K5_CALLABLE = "K5"
    K6_VERIFIED = "K6"
    K7_ADAPTIVE = "K7"
    K8_TRANSFERABLE = "K8"


class EvidenceMaturity(str, Enum):
    UNVERIFIED = "unverified"
    CURRENT = "current"
    CONTESTED = "contested"
    OUTDATED = "outdated"


class GapAction(str, Enum):
    TEACH_HUMAN = "teach_human"          # machine > human
    DISTILL_HUMAN = "distill_human"      # human > machine
    COLLABORATE = "collaborate"          # both strong
    LEARN_FIRST = "learn_first"          # neither strong
    REVIEW_EVIDENCE = "review_evidence"  # evidence not current


HUMAN_LEVEL_ORDER = [HumanMasteryLevel.M0_SEEN, HumanMasteryLevel.M1_RECOGNIZE,
                     HumanMasteryLevel.M2_RECALL, HumanMasteryLevel.M3_EXPLAIN,
                     HumanMasteryLevel.M4_SOLVE, HumanMasteryLevel.M5_TRANSFER,
                     HumanMasteryLevel.M6_CREATE, HumanMasteryLevel.M7_EXPERT]

MACHINE_LEVEL_ORDER = [MachineMasteryLevel.K0_RAW, MachineMasteryLevel.K1_INDEXED,
                       MachineMasteryLevel.K2_STRUCTURED, MachineMasteryLevel.K3_REASONABLE,
                       MachineMasteryLevel.K4_PROCEDURAL, MachineMasteryLevel.K5_CALLABLE,
                       MachineMasteryLevel.K6_VERIFIED, MachineMasteryLevel.K7_ADAPTIVE,
                       MachineMasteryLevel.K8_TRANSFERABLE]


# ── input evidence bundles ─────────────────────────────────────────

@dataclass(frozen=True)
class HumanEvidence:
    """Evidence used to place a learner on the M scale."""

    reviewed: bool = False
    review_state: str = "new"          # new / learning / review
    stability_days: float = 0.0
    bkt_mastery: float = 0.0           # posterior P(L) from knowledge tracing
    teach_back_score: float | None = None      # 0..1, M3
    quiz_pass: bool = False            # M4
    transfer_pass: bool = False        # M5
    creation_evidence: bool = False    # M6 (project / artefact)
    teaching_evidence: bool = False    # M6-M7 (taught it to the machine)


@dataclass(frozen=True)
class MachineEvidence:
    """Evidence used to place the machine knowledge on the K scale."""

    has_raw_source: bool = False       # K0
    indexed: bool = False              # K1
    structured: bool = False           # K2 (knowledge unit exists)
    reasoned: bool = False             # K3 (graph relations)
    procedural: bool = False           # K4 (procedure / workflow exists)
    callable: bool = False             # K5 (skill asset exists)
    verified: bool = False             # K6 (skill passed verification)
    adapted: bool = False              # K7 (skill updated from failure)
    transferable: bool = False         # K8 (used in >= 2 scopes)


# ── level calculators ───────────────────────────────────────────────

def human_mastery_level(evidence: HumanEvidence) -> HumanMasteryLevel:
    """Place the learner on M0..M7 from explicit evidence."""
    if not evidence.reviewed:
        return HumanMasteryLevel.M0_SEEN
    if evidence.teaching_evidence or evidence.creation_evidence:
        return HumanMasteryLevel.M6_CREATE if not evidence.teaching_evidence else HumanMasteryLevel.M7_EXPERT
    if evidence.transfer_pass:
        return HumanMasteryLevel.M5_TRANSFER
    if evidence.quiz_pass:
        return HumanMasteryLevel.M4_SOLVE
    if evidence.teach_back_score is not None and evidence.teach_back_score >= 0.7:
        return HumanMasteryLevel.M3_EXPLAIN
    if evidence.review_state == "review" and evidence.stability_days >= 7.0:
        return HumanMasteryLevel.M2_RECALL
    return HumanMasteryLevel.M1_RECOGNIZE


def machine_mastery_level(evidence: MachineEvidence) -> MachineMasteryLevel:
    """Place the machine knowledge on K0..K8 from explicit evidence."""
    if not evidence.has_raw_source:
        return MachineMasteryLevel.K0_RAW
    if not evidence.indexed:
        return MachineMasteryLevel.K1_INDEXED
    if not evidence.structured:
        return MachineMasteryLevel.K2_STRUCTURED
    if not evidence.reasoned:
        return MachineMasteryLevel.K3_REASONABLE
    if not evidence.procedural:
        return MachineMasteryLevel.K4_PROCEDURAL
    if not evidence.callable:
        return MachineMasteryLevel.K5_CALLABLE
    if not evidence.verified:
        return MachineMasteryLevel.K6_VERIFIED
    if not evidence.adapted:
        return MachineMasteryLevel.K7_ADAPTIVE
    return MachineMasteryLevel.K8_TRANSFERABLE


def evidence_maturity(*, verified: bool, valid_to: str | None, has_superseding: bool,
                      has_contradiction: bool, now: str) -> EvidenceMaturity:
    """Judge how current the node's facts are.

    Args:
        verified: whether the underlying fact passed verification.
        valid_to: ISO timestamp at which the fact expires (None = no expiry).
        has_superseding: a newer version supersedes this node.
        has_contradiction: a live contradiction exists.
        now: ISO timestamp of "today".
    """
    if has_superseding or (valid_to is not None and now >= valid_to):
        return EvidenceMaturity.OUTDATED
    if has_contradiction:
        return EvidenceMaturity.CONTESTED
    if not verified:
        return EvidenceMaturity.UNVERIFIED
    return EvidenceMaturity.CURRENT


def mastery_gap(human: HumanMasteryLevel, machine: MachineMasteryLevel,
                evidence: EvidenceMaturity) -> tuple[GapAction, int]:
    """Decide the next bidirectional action from the three axes.

    Returns (action, delta) where delta = machine_index - human_index.
    """
    if evidence != EvidenceMaturity.CURRENT:
        return GapAction.REVIEW_EVIDENCE, 0
    h = HUMAN_LEVEL_ORDER.index(human)
    k = MACHINE_LEVEL_ORDER.index(machine)
    delta = k - h
    if delta > 0:
        return GapAction.TEACH_HUMAN, delta
    if delta < 0:
        return GapAction.DISTILL_HUMAN, delta
    if k >= MACHINE_LEVEL_ORDER.index(MachineMasteryLevel.K6_VERIFIED) and             h >= HUMAN_LEVEL_ORDER.index(HumanMasteryLevel.M4_SOLVE):
        return GapAction.COLLABORATE, 0
    return GapAction.LEARN_FIRST, 0


# ── three-axis knowledge node ───────────────────────────────────────

class KnowledgeNodeState(BaseModel):
    """One knowledge node with its three-axis state (pure, JSON-safe)."""

    model_config = ConfigDict(extra="forbid")

    node_id: str
    human_level: HumanMasteryLevel
    machine_level: MachineMasteryLevel
    evidence: EvidenceMaturity
    action: GapAction
    delta: int

    def to_display(self) -> dict[str, object]:
        """Render the node for a dashboard (report §25)."""
        return {
            "node_id": self.node_id,
            "human": {"level": self.human_level.value,
                      "label": self.human_level.name.replace("_", " ")},
            "machine": {"level": self.machine_level.value,
                        "label": self.machine_level.name.replace("_", " ")},
            "evidence": self.evidence.value,
            "action": self.action.value,
            "delta": self.delta,
        }


def evaluate_node(node_id: str, human: HumanEvidence,
                  machine: MachineEvidence, *, evidence_verified: bool = True,
                  valid_to: str | None = None, has_superseding: bool = False,
                  has_contradiction: bool = False, now: str = "9999-12-31T00:00:00+00:00"
                  ) -> KnowledgeNodeState:
    """Evaluate one knowledge node on all three axes (pure function)."""
    h = human_mastery_level(human)
    k = machine_mastery_level(machine)
    e = evidence_maturity(verified=evidence_verified, valid_to=valid_to,
                          has_superseding=has_superseding,
                          has_contradiction=has_contradiction, now=now)
    action, delta = mastery_gap(h, k, e)
    return KnowledgeNodeState(node_id=node_id, human_level=h, machine_level=k,
                              evidence=e, action=action, delta=delta)
