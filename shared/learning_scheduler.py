"""Learning scheduler (ADS-008: py-fsrs absorption).

Wraps the FSRS v6 algorithm (MIT, open-spaced-repetition/py-fsrs)
for evidence-anchored learning cards.

Each scheduled card MUST reference an EvidenceAnchor so the review
is always traceable to source content.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fsrs import Card, Rating, Scheduler, State

__all__ = [
    "LearningScheduler",
    "CardRating",
    "card_state_name",
]

# Re-export Rating enum for convenience
CardRating = Rating


def card_state_name(card: Card) -> str:
    """Human-readable card state."""
    return {
        State.Learning: "learning",
        State.Review: "review",
        State.Relearning: "relearning",
    }.get(card.state, "learning")  # default learning for new cards


class LearningScheduler:
    """FSRS-based spaced-repetition scheduler.

    Thread-safe: holds no mutable shared state beyond the Scheduler instance
    (which is stateless — state lives in Card objects).
    """

    def __init__(self) -> None:
        self._scheduler = Scheduler()

    def review(
        self,
        card: Card,
        rating: Rating,
        now: datetime | None = None,
    ) -> tuple[Card, dict[str, object]]:
        """Review a card and return updated Card + ReviewLog summary.

        The caller is responsible for persisting the updated Card fields
        (state, stability, difficulty, due, scheduled_days, last_review).
        """
        now = now or datetime.now(timezone.utc)
        updated_card, review_log = self._scheduler.review_card(
            card, rating, review_datetime=now
        )
        scheduled_days = 0
        if updated_card.last_review is not None and updated_card.due is not None:
            diff = updated_card.due - updated_card.last_review
            scheduled_days = max(0, int(diff.total_seconds() / 86400))
        summary: dict[str, object] = {
            "state": card_state_name(updated_card),
            "rating": int(rating),
            "stability": round(updated_card.stability, 2) if updated_card.stability else None,
            "difficulty": round(updated_card.difficulty, 2) if updated_card.difficulty else None,
            "due": updated_card.due.isoformat() if updated_card.due else None,
            "scheduled_days": scheduled_days,
        }
        return updated_card, summary

    def next_due(self, card: Card) -> datetime:
        """Return when the card is next due."""
        return card.due

    def is_due(self, card: Card, now: datetime | None = None) -> bool:
        """Check if the card is due for review."""
        now = now or datetime.now(timezone.utc)
        return card.due <= now
