"""Forgetting-aware learner state — D3 recommendation R1 (AI Learning OS).

Binds BKT posterior mastery with FSRS stability/recall into ONE knowledge
state that decays over time (report §3.5: "机器观察你的遗忘，反过来优化学习"):

    knowledge_state(bkt_posterior, stability_days, elapsed_days, review_count)
        → {mastery, recall_probability, forgetting_risk}

Pure calculation — no persistence. Mastery is a probability, never asserted
as verified truth (governance).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

# FSRS-style recall decay: R(t) = (1 + factor * t / S) ^ -decay
_DECAY = 0.9
_FACTOR = 19.0


@dataclass(frozen=True)
class KnowledgeState:
    mastery: float          # fused posterior P(L) in [0,1]
    recall_probability: float
    forgetting_risk: float  # 1 - recall_probability

    def as_dict(self) -> dict[str, float]:
        return {"mastery": round(self.mastery, 3),
                "recall_probability": round(self.recall_probability, 3),
                "forgetting_risk": round(self.forgetting_risk, 3)}


def recall_probability(stability_days: float, elapsed_days: float) -> float:
    """FSRS-style probability of recalling after elapsed_days since last review."""
    if stability_days <= 0:
        return 0.0
    if elapsed_days <= 0:
        return 1.0
    return float(max(0.0, min(1.0, (1.0 + _FACTOR * elapsed_days / stability_days) ** -_DECAY)))


def knowledge_state(
    *,
    bkt_posterior: float,
    stability_days: float,
    elapsed_days: float,
    review_count: int = 0,
) -> KnowledgeState:
    """Fuse BKT mastery with FSRS forgetting into one state."""
    if not 0.0 <= bkt_posterior <= 1.0:
        raise ValueError("bkt_posterior must be in [0,1]")
    if stability_days < 0 or elapsed_days < 0:
        raise ValueError("stability/elapsed days must be >= 0")
    recall = recall_probability(stability_days, elapsed_days)
    # fused mastery: BKT posterior tempered by recall decay; a never-reviewed
    # item (stability 0) has no recall evidence beyond BKT prior.
    if stability_days <= 0:
        mastery = bkt_posterior * 0.5
    else:
        mastery = bkt_posterior * recall
    return KnowledgeState(
        mastery=float(max(0.0, min(1.0, mastery))),
        recall_probability=recall,
        forgetting_risk=round(1.0 - recall, 3),
    )
