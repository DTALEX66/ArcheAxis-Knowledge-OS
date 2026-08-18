"""Prerequisite-aware path recommender — D3 recommendation R3.

Scores the next learning node from three signals (report §9.3, KnowLP /
knowledge-spaces direction):

    readiness  — prerequisite mastery shortfall (want: low mastery → learn next)
    forgetting — forgetting risk from learner_state (want: high risk → review)
    prereq_ok  — all prerequisites mastered (hard gate; nodes with unmet
                 prerequisites are deferred)

    score = 0.50 * mastery_shortfall + 0.30 * forgetting_risk + 0.20 * prereq_ready

Pure calculation over a plain graph + mastery/forgetting maps — persistence
lives in callers (learning-path API / co-learning loop).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

DEFAULT_MASTERY_THRESHOLD = 0.6


class RecommenderError(ValueError):
    """Raised when the recommender receives invalid input."""


@dataclass(frozen=True)
class Recommendation:
    node: str
    score: float
    reasons: list[str]

    def as_dict(self) -> dict[str, Any]:
        return {"node": self.node, "score": round(self.score, 3), "reasons": self.reasons}


def _validate(graph: dict[str, Any]) -> tuple[list[str], dict[str, list[str]]]:
    nodes = list(graph.get("nodes", []))
    if not nodes:
        raise RecommenderError("graph requires at least one node")
    node_set = set(nodes)
    prereqs: dict[str, list[str]] = {n: [] for n in nodes}
    for src, tgt in graph.get("edges", []):
        if src not in node_set or tgt not in node_set:
            raise RecommenderError(f"edge references unknown node: ({src}, {tgt})")
        prereqs[tgt].append(src)
    return nodes, prereqs


def recommend_next(
    *,
    graph: dict[str, Any],
    mastery_map: dict[str, Any],
    forgetting_map: dict[str, Any] | None = None,
    current: str | None = None,
    top_k: int = 1,
    mastery_threshold: float = DEFAULT_MASTERY_THRESHOLD,
) -> list[Recommendation]:
    """Recommend the next node(s) to learn.

    Deferred: nodes whose prerequisites are not all mastered (unless they have
    no prerequisites). Skipped: nodes already mastered at/above the threshold.
    """
    if top_k < 1:
        raise RecommenderError("top_k must be >= 1")
    if not 0.0 < mastery_threshold <= 1.0:
        raise RecommenderError("mastery_threshold must be in (0,1]")
    nodes, prereqs = _validate(graph)
    forgetting_map = forgetting_map or {}

    def mastery(node: str) -> float:
        try:
            return float(mastery_map.get(node, 0.0))
        except (TypeError, ValueError):
            return 0.0

    def forgetting(node: str) -> float:
        try:
            return float(forgetting_map.get(node, 0.0))
        except (TypeError, ValueError):
            return 0.0

    scored: list[Recommendation] = []
    for node in nodes:
        if node == current:
            continue
        node_mastery = mastery(node)
        if node_mastery >= mastery_threshold:
            continue
        node_prereqs = prereqs.get(node, [])
        prereq_ready = all(mastery(p) >= mastery_threshold for p in node_prereqs) if node_prereqs else True
        if not prereq_ready:
            continue
        shortfall = 1.0 - node_mastery
        risk = forgetting(node)
        score = round(0.50 * shortfall + 0.30 * risk + 0.20 * (1.0 if prereq_ready else 0.0), 3)
        reasons = [f"mastery {node_mastery:.2f} (shortfall {shortfall:.2f})"]
        if risk > 0:
            reasons.append(f"forgetting risk {risk:.2f}")
        if node_prereqs:
            reasons.append(f"prerequisites ready ({len(node_prereqs)})")
        scored.append(Recommendation(node=node, score=score, reasons=reasons))

    scored.sort(key=lambda r: r.score, reverse=True)
    return scored[:top_k]
