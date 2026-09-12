"""R05 regression: review intervals come from the reused FSRS scheduler.

The point of these tests is that the scheduling authority is the existing
py-fsrs donor, not the temporary 1/2/4/7/14 ladder in
``archeaxis_domain::learning::suggest_next_interval``, and that an unusable
request fails closed instead of silently inventing an interval.
"""

from __future__ import annotations

import importlib.util
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

WORKER = Path(__file__).resolve().parents[1] / "services" / "python-workers" / "learning" / "worker_schedule.py"


def _load_worker():
    spec = importlib.util.spec_from_file_location("worker_schedule_under_test", WORKER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


worker = _load_worker()

NOW = datetime(2026, 9, 2, tzinfo=timezone.utc)

# A card with high stability: FSRS schedules it far beyond the ladder's 14-day
# ceiling, so the value itself proves which scheduler answered.
MATURE = {
    "state": "review",
    "stability": 42.0,
    "difficulty": 5.0,
    "due": (NOW - timedelta(days=1)).isoformat(),
    "last_review": (NOW - timedelta(days=30)).isoformat(),
    "step": 0,
}


class TestFsrsAuthority:
    def test_serialized_reviews_match_uninterrupted_fsrs_across_worker_restarts(self) -> None:
        import json
        import subprocess
        import sys

        from fsrs import Card, Rating, Scheduler

        scheduler = Scheduler(enable_fuzzing=False)
        expected = Card(due=NOW)
        persisted = {'due': NOW.isoformat()}
        instant = NOW
        for rating in (Rating.Good, Rating.Good, Rating.Again, Rating.Good):
            expected, _ = scheduler.review_card(expected, rating, review_datetime=instant)
            process = subprocess.run(
                [sys.executable, '-B', str(WORKER)],
                input=json.dumps({'item_key': 'restart-card', 'rating': int(rating),
                                  'state': persisted, 'now': instant.isoformat()}),
                capture_output=True, text=True, encoding='utf-8', timeout=30,
            )
            assert process.returncode == 0, process.stderr
            persisted = json.loads(process.stdout)
            assert persisted['due'] == expected.due.isoformat()
            assert persisted['state'] == expected.state.name.lower()
            instant = expected.due
        assert persisted['step'] == expected.step
        assert persisted['last_review'] == expected.last_review.isoformat()
        assert persisted['stability'] == expected.stability
        assert persisted['difficulty'] == expected.difficulty

    def test_persisted_parameters_are_not_rounded_for_display(self) -> None:
        from fsrs import Card, Rating, Scheduler, State

        card = Card(state=State.Review, stability=MATURE['stability'],
                    difficulty=MATURE['difficulty'],
                    due=datetime.fromisoformat(MATURE['due']),
                    last_review=datetime.fromisoformat(MATURE['last_review']))
        expected, _ = Scheduler(enable_fuzzing=False).review_card(
            card, Rating.Good, review_datetime=NOW)
        result = worker.schedule({'item_key': 'c', 'rating': 3,
                                  'state': MATURE, 'now': NOW.isoformat()})
        assert result['stability'] == expected.stability
        assert result['difficulty'] == expected.difficulty

    def test_mature_card_interval_exceeds_the_placeholder_ladder(self) -> None:
        result = worker.schedule({"item_key": "card-1", "rating": 3, "state": MATURE, "now": NOW.isoformat()})
        assert result["authority"] == "fsrs"
        assert result["next_review_days"] > 14, "the ladder caps at 14 days; FSRS must exceed it for a mature card"
        assert result["stability"] is not None and result["difficulty"] is not None
        assert result["due"]

    def test_rating_changes_the_interval(self) -> None:
        again = worker.schedule({"item_key": "c", "rating": 1, "state": MATURE, "now": NOW.isoformat()})
        easy = worker.schedule({"item_key": "c", "rating": 4, "state": MATURE, "now": NOW.isoformat()})
        assert easy["next_review_days"] > again["next_review_days"]

    def test_same_input_is_deterministic(self) -> None:
        first = worker.schedule({"item_key": "c", "rating": 3, "state": MATURE, "now": NOW.isoformat()})
        second = worker.schedule({"item_key": "c", "rating": 3, "state": MATURE, "now": NOW.isoformat()})
        assert first == second

    def test_correct_boolean_maps_to_a_rating(self) -> None:
        result = worker.schedule({"item_key": "c", "correct": True, "state": MATURE, "now": NOW.isoformat()})
        assert result["rating"] == 3
        assert result["next_review_days"] > 0


class TestFailClosed:
    @pytest.mark.parametrize('rating', [0, 5, True, None, 'typo'])
    def test_invalid_explicit_rating_cannot_fall_back_to_correct(self, rating):
        with pytest.raises(ValueError, match='rating'):
            worker.schedule({'item_key': 'c', 'rating': rating, 'correct': True, 'state': MATURE})

    @pytest.mark.parametrize('state', [[], False, 0, ''])
    def test_falsey_non_object_state_is_not_a_new_card(self, state):
        with pytest.raises(ValueError, match='state'):
            worker.parse_state({'state': state})

    @pytest.mark.parametrize('value', [float('nan'), float('inf'), -float('inf')])
    def test_non_finite_state_is_rejected(self, value):
        with pytest.raises(ValueError, match='finite'):
            worker.parse_state({'state': {'stability': value}})

    def test_missing_rating_and_correct_is_an_explicit_error(self) -> None:
        with pytest.raises(ValueError):
            worker.schedule({"item_key": "c", "state": MATURE, "now": NOW.isoformat()})

    def test_missing_item_key_is_an_explicit_error(self) -> None:
        with pytest.raises(ValueError):
            worker.schedule({"rating": 3, "state": MATURE})

    def test_unknown_card_state_is_rejected(self) -> None:
        with pytest.raises(ValueError):
            worker.schedule({"item_key": "c", "rating": 3, "state": {"state": "imaginary"}})

    def test_error_response_carries_no_interval(self) -> None:
        # main() turns a failing request into an explicit error object; it must
        # never emit a fabricated interval.
        import json
        import subprocess
        import sys

        proc = subprocess.run(
            [sys.executable, str(WORKER)],
            input=json.dumps({"item_key": "c", "state": MATURE}),
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        payload = json.loads(proc.stdout)
        assert proc.returncode == 1
        assert payload["authority"] == "fsrs"
        assert "error" in payload
        assert "next_review_days" not in payload
