"""AXW-050B: fail-safe boundaries for grounded AI answers.

Wraps the grounded-answer path with explicit failure semantics so every
failure mode degrades to a safe, honest outcome instead of a hallucinated
or over-privileged one:

- provider unavailable / network error        → ``failed`` (no answer, no cache hit)
- context insufficient (score too low)        → ``insufficient_context``
- conflicting evidence (active supports+refutes) → ``conflict`` (human adjudication required)
- expired / revoked evidence                  → ``stale`` (explicit, not silent)
- out-of-scope request                        → ``forbidden`` (scope gate)
- ungrounded claims                           → ``refused`` (never pseudo-cite)

``answer_with_boundaries`` returns a structured verdict; the caller must
never fall back to an ungrounded completion on any non-success verdict.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.answer.grounded import GroundedAnswer, build_grounded_answer
from app.evidence.relations import active_relations, has_conflict
from app.knowledge.freshness import project_active


class BoundaryError(ValueError):
    """Raised when the boundary wrapper is misconfigured (not a model failure)."""


@dataclass(frozen=True)
class AnswerVerdict:
    status: str  # success | failed | insufficient_context | conflict | stale | forbidden | refused
    answer: GroundedAnswer | None = None
    reasons: list[str] = field(default_factory=list)
    detail: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "answer": self.answer.as_dict() if self.answer else None,
            "reasons": self.reasons,
            "detail": self.detail,
        }


def answer_with_boundaries(
    *,
    evidence_db: str,
    freshness_db: str,
    relation_db: str,
    claim_id: str,
    scope: str | None,
    claims: list[Any],
    context_score: float | None = None,
    min_context_score: float = 0.3,
    provider_available: bool = True,
) -> AnswerVerdict:
    """Answer with every AXW-050B boundary checked, in fail-safe order.

    Order matters: scope → freshness → conflict → context → grounding →
    provider. Each gate returns a safe verdict; the grounded answer is only
    produced when every gate passes.
    """
    if not claim_id:
        raise BoundaryError("claim_id is required")

    reasons: list[str] = []

    # 1. Provider unavailable → fail closed (no cached/hallucinated answer).
    if not provider_available:
        return AnswerVerdict(status="failed", reasons=["provider_unavailable"], detail="AI provider unavailable; no answer produced.")

    # 2. Freshness gate first: expired/revoked/superseded units are stale
    #    regardless of scope — a revoked unit must never be answered.
    active_any_scope = project_active(freshness_db, unit_ids=[claim_id], scope=None)
    if claim_id not in active_any_scope:
        return AnswerVerdict(status="stale", reasons=["evidence_not_active"], detail="evidence is expired, revoked, or superseded.")

    # 3. Scope gate: request must match the unit's scope.
    if scope is not None:
        active_ids = project_active(freshness_db, unit_ids=[claim_id], scope=scope)
        if claim_id not in active_ids:
            return AnswerVerdict(status="forbidden", reasons=["scope_mismatch"], detail=f"request scope '{scope}' not granted for this knowledge.")

    # 4. Conflict gate: active supports+refutes requires human adjudication.
    if has_conflict(relation_db, claim_id=claim_id):
        relations = active_relations(relation_db, claim_id=claim_id)
        return AnswerVerdict(
            status="conflict",
            reasons=[f"active_relations={len(relations)}", "mixed_support_refute"],
            detail="conflicting evidence requires human adjudication before answering.",
        )

    # 5. Context sufficiency gate.
    if context_score is not None and context_score < min_context_score:
        return AnswerVerdict(
            status="insufficient_context",
            reasons=[f"context_score={context_score:.2f}<{min_context_score}"],
            detail="retrieved context is insufficient to answer.",
        )

    # 6. Grounding gate: every claim must resolve to a stored anchor.
    try:
        grounded = build_grounded_answer(db=evidence_db, claims=claims)
    except ValueError as exc:
        return AnswerVerdict(status="failed", reasons=["grounding_error"], detail=str(exc))
    if not grounded.grounded:
        return AnswerVerdict(
            status="refused",
            reasons=["ungrounded_claims"],
            detail="refused: " + "; ".join(grounded.ungrounded[:3]),
        )

    reasons.append(f"grounded_claims={len(grounded.claims)}")
    return AnswerVerdict(status="success", answer=grounded, reasons=reasons)
