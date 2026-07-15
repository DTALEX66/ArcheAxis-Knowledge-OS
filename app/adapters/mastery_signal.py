"""Pure mastery calculation from Card, Review, and Mistake snapshots."""

from __future__ import annotations

from typing import Any

from app.contracts.v1 import CONTRACT_VERSION, MasterySignalV1


def from_learning_snapshots(
    card: dict[str, Any],
    reviews: list[dict[str, Any]],
    mistakes: list[dict[str, Any]],
) -> MasterySignalV1:
    """Calculate mastery without reading or mutating persistence state."""

    card_identity = card.get("card_id") or card.get("id")
    if card_identity is None:
        raise ValueError("card snapshot requires card_id or id")
    card_id = str(card_identity)
    card_reviews = [review for review in reviews if review.get("card_id") == card_id]
    card_reviews.sort(key=lambda review: str(review.get("created_at", "")))
    card_mistakes = [mistake for mistake in mistakes if mistake.get("card_id") == card_id]
    unresolved_ids = [
        str(mistake["id"]) for mistake in card_mistakes if not mistake.get("resolved", False)
    ]
    review_status = str(card.get("review_status", "draft"))
    review_count = len(card_reviews)
    latest_quality = int(card_reviews[-1]["quality"]) if card_reviews else None

    return MasterySignalV1(
        schema_version=CONTRACT_VERSION,
        calculation_version="review-outcome-v1",
        card_id=card_id,
        is_mastered=(
            review_count >= 3
            and not unresolved_ids
            and latest_quality is not None
            and latest_quality >= 4
        ),
        review_ids=[str(review["id"]) for review in card_reviews],
        mistake_ids=[str(mistake["id"]) for mistake in card_mistakes],
        review_count=review_count,
        unresolved_mistake_ids=unresolved_ids,
        latest_ease_factor=(float(card_reviews[-1]["ease_factor"]) if card_reviews else None),
        latest_review_quality=latest_quality,
        review_status=review_status,
    )
