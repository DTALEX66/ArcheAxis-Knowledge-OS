"""AXW-050A: citation-grounded AI answers.

Every substantive statement in an AI answer must trace back to an
EvidenceAnchor. ``build_grounded_answer`` takes claim statements plus the
anchor ids they cite; each anchor is resolved against the anchor store
(fail-closed: unknown anchors are rejected, not silently dropped):

- all claims grounded  → ``grounded`` answer with per-claim anchors;
- some claims lack resolvable anchors → the answer is refused with the
  list of ungrounded claims (no pseudo-citations, no partial guessing);
- explicit uncertainty is allowed when the caller marks a claim
  ``uncertain`` — it is then rendered as a refusal-to-assert, never as a
  fact with a fake citation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.evidence.anchor import EvidenceAnchor, resolve_evidence_anchor


class GroundingError(ValueError):
    """Raised when a grounding request is structurally invalid."""


@dataclass(frozen=True)
class GroundedClaim:
    statement: str
    anchor_id: str
    uncertain: bool = False


@dataclass(frozen=True)
class GroundedAnswer:
    answer_text: str
    grounded: bool
    claims: list[dict[str, Any]] = field(default_factory=list)
    ungrounded: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "answer": self.answer_text,
            "grounded": self.grounded,
            "claims": self.claims,
            "ungrounded": self.ungrounded,
        }


def _render(claims: list[GroundedClaim], anchors: dict[str, EvidenceAnchor]) -> str:
    parts: list[str] = []
    for idx, claim in enumerate(claims, start=1):
        if claim.uncertain:
            parts.append(f"[{idx}] {claim.statement} (uncertain — no assertion made)")
            continue
        anchor = anchors.get(claim.anchor_id)
        assert anchor is not None  # resolved before rendering
        locator = anchor.locator
        page = locator.get("page_number") or locator.get("page_index")
        block = locator.get("block_id") or locator.get("kind")
        where = f"p{page}" if page is not None else (block or "source")
        parts.append(f"[{idx}] {claim.statement} [{where} | {anchor.raw_sha256[:8]}]")
    return "\n".join(parts)


def build_grounded_answer(
    *,
    db: str | Path,
    claims: list[GroundedClaim],
    fallback_text: str = "I cannot answer without grounded evidence.",
) -> GroundedAnswer:
    """Build a citation-grounded answer or refuse.

    Fail-closed: every non-uncertain claim must resolve to a stored anchor;
    otherwise the answer is refused (``grounded=False``) with the offending
    claims listed. ``uncertain`` claims never receive fabricated citations.
    """
    if not claims:
        raise GroundingError("at least one claim is required")

    resolved: dict[str, EvidenceAnchor] = {}
    ungrounded: list[str] = []
    for claim in claims:
        if not claim.statement.strip():
            raise GroundingError("claim statement must not be empty")
        if claim.uncertain:
            continue
        anchor = resolve_evidence_anchor(db, claim.anchor_id)
        if anchor is None:
            ungrounded.append(claim.statement)
        else:
            resolved[claim.anchor_id] = anchor

    if ungrounded:
        return GroundedAnswer(
            answer_text=fallback_text,
            grounded=False,
            claims=[
                {
                    "statement": c.statement,
                    "anchor_id": c.anchor_id,
                    "uncertain": c.uncertain,
                }
                for c in claims
            ],
            ungrounded=ungrounded,
        )

    rendered = _render(claims, resolved)
    claims_out = [
        {
            "statement": c.statement,
            "anchor_id": c.anchor_id,
            "uncertain": c.uncertain,
            "raw_sha256": resolved.get(c.anchor_id).raw_sha256 if c.anchor_id in resolved else None,
            "locator": resolved.get(c.anchor_id).locator if c.anchor_id in resolved else None,
        }
        for c in claims
    ]
    return GroundedAnswer(answer_text=rendered, grounded=True, claims=claims_out)


def answer_for_retrieval(
    *,
    db: str | Path,
    query: str,
    retrieved: list[dict[str, Any]],
) -> GroundedAnswer:
    """Convenience: build a grounded answer from retrieval results.

    Each retrieved item must carry ``statement`` + ``anchor_id``. Items
    without a resolvable anchor trigger refusal — retrieval alone is never
    a citation.
    """
    if not query.strip():
        raise GroundingError("query must not be empty")
    claims = [
        GroundedClaim(statement=item["statement"], anchor_id=item["anchor_id"])
        for item in retrieved
    ]
    return build_grounded_answer(db=db, claims=claims)
