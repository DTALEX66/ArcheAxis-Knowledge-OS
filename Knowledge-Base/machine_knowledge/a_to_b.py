"""A→B translation engine — human mastery → machine knowledge.

Phase 5: when a card reaches mastery criteria (≥3 reviews, no unresolved
mistakes, review_status='mastered'), it becomes a candidate for translation
into a machine knowledge unit.

Flow:
    Card mastered? → find_candidates() → translate() → publish() → machine_knowledge
"""

from __future__ import annotations

import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_PROJECT_ROOT))
sys.path.insert(0, str(_PROJECT_ROOT / "Knowledge-Base"))

from mistakes import get_mistakes_for_card  # noqa: E402

from machine_knowledge import create_unit  # noqa: E402
from shared.storage import insert, select_all, select_one  # noqa: E402

# ── Mastery criteria ────────────────────────────────────

MASTERY_THRESHOLD = 0.7
MIN_REVIEWS = 3


def _count_reviews(card_id: str) -> int:
    """Count reviews for a card."""
    rows = select_all("kb_reviews", limit=500)
    return sum(1 for r in rows if r.get("card_id") == card_id)


def _has_unresolved_mistakes(card_id: str) -> bool:
    """Check if card has unresolved mistakes."""
    mistakes = get_mistakes_for_card(card_id)
    return any(not m.get("resolved", False) for m in mistakes)


def _latest_review_ease(card_id: str) -> float:
    """Get the ease factor from the latest review."""
    rows = select_all("kb_reviews", limit=500, order="created_at DESC")
    for r in rows:
        if r.get("card_id") == card_id:
            return r.get("ease_factor", 2.5)
    return 2.5


# ── Candidate discovery ─────────────────────────────────


def find_mastered_cards(limit: int = 20) -> list[dict[str, Any]]:
    """Find cards that meet mastery criteria for A→B translation.

    Criteria:
        - review_status is 'mastered' or 'reviewing'
        - ≥ ``MIN_REVIEWS`` reviews
        - No unresolved mistakes
        - Ease factor ≥ ``MASTERY_THRESHOLD``
    """
    cards = select_all("kb_cards", limit=500)
    candidates = []

    for card in cards:
        status = card.get("review_status", "draft")
        if status not in ("mastered", "reviewing"):
            continue

        review_count = _count_reviews(card["id"])
        if review_count < MIN_REVIEWS:
            continue

        if _has_unresolved_mistakes(card["id"]):
            continue

        ease = _latest_review_ease(card["id"])
        if ease < MASTERY_THRESHOLD:
            continue

        candidates.append(
            {
                "card_id": card["id"],
                "title": card.get("title", ""),
                "content": card.get("content", ""),
                "review_count": review_count,
                "ease_factor": ease,
                "review_status": status,
            }
        )

    candidates.sort(key=lambda c: c["ease_factor"], reverse=True)
    return candidates[:limit]


# ── Translation ─────────────────────────────────────────


def translate_card(
    card_id: str,
    unit_type: str = "rule",
    override_title: str = "",
    override_content: str = "",
) -> dict[str, Any]:
    """Create an A→B candidate from a card.

    Args:
        card_id: the source card.
        unit_type: 'rule' | 'fact' | 'procedure' | 'constraint' | 'pattern'.
        override_title: if provided, use this instead of card title.
        override_content: if provided, use this instead of card content.

    Returns:
        The candidate dict, or error.
    """
    card = select_one("kb_cards", card_id)
    if not card:
        return {"error": "card not found"}

    now = datetime.now(timezone.utc).isoformat()
    candidate_id = f"ab_{uuid.uuid4().hex[:12]}"

    review_count = _count_reviews(card_id)
    ease = _latest_review_ease(card_id)

    candidate = {
        "id": candidate_id,
        "a_source_type": "card",
        "a_source_id": card_id,
        "a_title": card.get("title", ""),
        "a_content": card.get("content", ""),
        "a_review_count": review_count,
        "a_ease_factor": ease,
        "b_title": override_title or card.get("title", ""),
        "b_content": override_content or card.get("content", ""),
        "b_unit_type": unit_type,
        "status": "pending",
        "created_at": now,
        "updated_at": now,
    }

    # Check if candidate already exists for this card
    existing = select_all("a_to_b_candidates", limit=200)
    for ex in existing:
        if ex.get("a_source_id") == card_id:
            candidate["id"] = ex["id"]
            candidate["status"] = ex.get("status", "pending")
            break

    insert("a_to_b_candidates", candidate)
    return candidate


def publish_candidate(candidate_id: str, confidence: float = 0.7) -> dict[str, Any]:
    """Publish an A→B candidate as a machine knowledge unit.

    Args:
        candidate_id: the candidate to publish.
        confidence: confidence score for the machine unit (uses card's ease
            factor as default).

    Returns:
        Result dict with knowledge_id or error.
    """
    cand = select_one("a_to_b_candidates", candidate_id)
    if not cand:
        return {"error": "candidate not found"}

    if cand.get("status") == "published":
        return {"error": "already published"}

    # Use card's ease factor as confidence if not overridden
    if confidence == 0.7:
        ease = cand.get("a_ease_factor", 0.7)
        confidence = min(ease, 1.0)

    unit = create_unit(
        title=cand.get("b_title", ""),
        content=cand.get("b_content", ""),
        unit_type=cand.get("b_unit_type", "rule"),
        confidence=confidence,
        source_type="a_to_b",
        source_id=cand.get("a_source_id", ""),
    )

    # Mark candidate as published
    cand["status"] = "published"
    cand["knowledge_id"] = unit["id"]
    cand["updated_at"] = datetime.now(timezone.utc).isoformat()
    insert("a_to_b_candidates", cand)

    return {"knowledge_id": unit["id"], "status": "published", "unit": unit}


def list_candidates(status: str = "pending") -> list[dict[str, Any]]:
    """List A→B candidates by status."""
    rows = select_all("a_to_b_candidates", limit=500)
    candidates = [r for r in rows if r.get("status") == status]
    candidates.sort(key=lambda c: c.get("a_ease_factor", 0), reverse=True)
    return candidates
