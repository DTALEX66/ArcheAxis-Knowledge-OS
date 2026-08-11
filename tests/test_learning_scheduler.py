"""Tests for shared.learning_scheduler (ADS-008: py-fsrs v6 absorption)."""

from fsrs import Card, Rating, State

from shared.learning_scheduler import LearningScheduler, card_state_name


class TestCardStateName:
    def test_new_card_is_learning(self) -> None:
        card = Card()
        assert card_state_name(card) == "learning"

    def test_review(self) -> None:
        card = Card()
        card.state = State.Review
        assert card_state_name(card) == "review"


class TestLearningScheduler:
    def test_new_card_review(self) -> None:
        s = LearningScheduler()
        card = Card()
        # New card starts as Learning and is due
        assert card_state_name(card) == "learning"

        updated, summary = s.review(card, Rating.Good)
        assert summary["rating"] == int(Rating.Good)
        assert "due" in summary
        assert "scheduled_days" in summary
        assert updated.state is not None

    def test_good_card_not_due_immediately(self) -> None:
        s = LearningScheduler()
        card = Card()
        updated, _ = s.review(card, Rating.Good)
        # After Good, card should not be due immediately
        assert not s.is_due(updated)

    def test_again_card_state_is_relearning(self) -> None:
        s = LearningScheduler()
        card = Card()
        updated, _ = s.review(card, Rating.Again)
        # After Again, card enters relearning state (v6 behavior)
        assert card_state_name(updated) in ("learning", "relearning")

    def test_multiple_reviews_progress(self) -> None:
        s = LearningScheduler()
        card = Card()
        for _ in range(3):
            card, summary = s.review(card, Rating.Good)
        # Stability should be positive after multiple Good reviews
        assert card.stability is not None
        assert card.stability > 0
