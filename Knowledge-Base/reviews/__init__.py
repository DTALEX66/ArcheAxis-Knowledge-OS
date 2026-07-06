"""Review scheduling — SM-2 spaced repetition for human learning.

Implements the SuperMemo-2 algorithm for scheduling card reviews.
Each review produces an ease factor and interval for the next review.

Reference: https://www.supermemo.com/en/archives1990-2015/english/ol/sm2
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_PROJECT_ROOT))
sys.path.insert(0, str(_PROJECT_ROOT / "Knowledge-Base"))

from shared.storage import insert, select_all, select_one, count  # noqa: E402

# ── SM-2 algorithm ──────────────────────────────────────


def _sm2_interval(
    quality: int,  # 0-5 scale
    prev_interval: int,
    prev_ease: float,
) -> tuple[int, float, datetime]:
    """SM-2 algorithm: compute next interval and ease factor.

    Args:
        quality: review quality (0-5).  0=complete blackout, 5=perfect.
        prev_interval: last interval in days.
        prev_ease: last ease factor (default 2.5).

    Returns:
        (next_interval_days, next_ease_factor, next_review_date)
    """
    if quality < 0 or quality > 5:
        raise ValueError("quality must be 0-5")

    if quality < 3:
        # Failed — reset interval
        new_interval = 1
    elif prev_interval == 0:
        new_interval = 1
    elif prev_interval == 1:
        new_interval = 6
    else:
        new_interval = int(round(prev_interval * prev_ease))

    # Update ease factor
    new_ease = prev_ease + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    new_ease = max(1.3, new_ease)  # minimum ease factor

    next_date = datetime.now() + timedelta(days=new_interval)
    return new_interval, round(new_ease, 2), next_date


# ── Review operations ───────────────────────────────────


def schedule_review(card_id: str, quality: int) -> dict[str, Any]:
    """Record a review for *card_id* and compute next schedule.

    Returns a dict with the review record + next review date.
    """
    import uuid

    # Get previous review (if any)
    prev_reviews = select_all("kb_reviews", limit=1, order="created_at DESC")
    prev = None
    for r in prev_reviews:
        if r.get("card_id") == card_id:
            prev = r
            break

    prev_interval = prev.get("interval_days", 0) if prev else 0
    prev_ease = prev.get("ease_factor", 2.5) if prev else 2.5

    new_interval, new_ease, next_date = _sm2_interval(
        quality, prev_interval, prev_ease
    )

    review = {
        "id": f"review_{uuid.uuid4().hex[:12]}",
        "card_id": card_id,
        "quality": quality,
        "interval_days": new_interval,
        "ease_factor": new_ease,
        "next_review_at": next_date.isoformat(),
        "created_at": datetime.now().isoformat(),
    }

    insert("kb_reviews", review)

    # Update card's review status
    _update_card_status(card_id, quality, next_date)

    return review


def get_due_reviews(limit: int = 20) -> list[dict[str, Any]]:
    """Return cards due for review (next_review_at <= now)."""
    now_iso = datetime.now().isoformat()
    all_reviews = select_all("kb_reviews", limit=500)
    all_cards = {c["id"]: c for c in select_all("kb_cards", limit=500)}

    # Find latest review per card
    latest_by_card: dict[str, dict] = {}
    for r in all_reviews:
        cid = r.get("card_id", "")
        if cid not in latest_by_card or r.get("created_at", "") > latest_by_card[cid].get("created_at", ""):
            latest_by_card[cid] = r

    due = []
    for cid, review in latest_by_card.items():
        next_at = review.get("next_review_at", "")
        if next_at and next_at <= now_iso:
            card = all_cards.get(cid, {})
            due.append({
                "card_id": cid,
                "title": card.get("title", ""),
                "content": card.get("content", ""),
                "next_review_at": next_at,
                "ease_factor": review.get("ease_factor", 2.5),
                "interval_days": review.get("interval_days", 0),
            })

    due.sort(key=lambda d: d["next_review_at"])
    return due[:limit]


def get_review_history(card_id: str, limit: int = 20) -> list[dict[str, Any]]:
    """Return review history for a card."""
    all_reviews = select_all("kb_reviews", limit=500, order="created_at DESC")
    return [r for r in all_reviews if r.get("card_id") == card_id][:limit]


def _update_card_status(card_id: str, quality: int, next_date: datetime) -> None:
    """Update card's review_status based on review quality."""
    card = select_one("kb_cards", card_id)
    if not card:
        return

    if quality >= 4:
        status = "mastered" if card.get("review_status") == "reviewing" else "reviewing"
    elif quality >= 2:
        status = "reviewing"
    else:
        status = "struggling"

    card["review_status"] = status
    insert("kb_cards", card)
