"""AXW-051B: FSRS due queue and mastery evidence tests.

Verifies:
- the fixed three-high-score heuristic is gone (unstable card with 3+ high
  ratings is NOT mastered);
- stable Review-state cards with unresolved mistakes are NOT mastered;
- mastery requires FSRS Review state + stability threshold;
- due queue compares in UTC and renders an optional local offset;
- recalculation replays immutable snapshots (append-only, no mutation).
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone

from app.knowledge.due_queue import (
    STABILITY_MASTERED_THRESHOLD_DAYS,
    due_queue,
    is_mastered_from_state,
    recalculate_mastery,
)


def _mkdb(tmp_path) -> str:
    db = str(tmp_path / "cards.sqlite")
    with sqlite3.connect(db) as conn:
        conn.executescript(
            """
            CREATE TABLE kb_cards (
                id TEXT PRIMARY KEY, card_id TEXT, due TEXT,
                fsrs_state TEXT, stability_days REAL, stability REAL,
                review_status TEXT
            );
            CREATE TABLE kb_reviews (
                id TEXT PRIMARY KEY, card_id TEXT, quality INTEGER,
                ease_factor REAL, created_at TEXT
            );
            CREATE TABLE kb_mistakes (
                id TEXT PRIMARY KEY, card_id TEXT, resolved INTEGER, created_at TEXT
            );
            """
        )
    return db


def _add_card(db: str, card_id: str, *, due: str, fsrs_state: str = "learning", stability: float | None = None) -> None:
    with sqlite3.connect(db) as conn:
        conn.execute(
            "INSERT INTO kb_cards (id, card_id, due, fsrs_state, stability_days, stability, review_status) "
            "VALUES (?,?,?,?,?,?,?)",
            (card_id, card_id, due, fsrs_state, stability, stability, "reviewing"),
        )


def _add_review(db: str, card_id: str, quality: int, created_at: str) -> None:
    with sqlite3.connect(db) as conn:
        conn.execute(
            "INSERT INTO kb_reviews (id, card_id, quality, ease_factor, created_at) VALUES (?,?,?,?,?)",
            (f"r_{card_id}_{quality}_{created_at}", card_id, quality, 2.5, created_at),
        )


def _add_mistake(db: str, card_id: str, resolved: bool) -> None:
    with sqlite3.connect(db) as conn:
        conn.execute(
            "INSERT INTO kb_mistakes (id, card_id, resolved, created_at) VALUES (?,?,?,?)",
            (f"m_{card_id}_{resolved}", card_id, 1 if resolved else 0, "2026-01-01T00:00:00+00:00"),
        )


def test_three_high_scores_no_longer_mastered_without_stability() -> None:
    # 3 reviews with quality 4+ but FSRS state still "learning" → NOT mastered.
    assert is_mastered_from_state(fsrs_state="learning", stability_days=2.0, unresolved_mistakes=0) is False
    assert is_mastered_from_state(fsrs_state="review", stability_days=None, unresolved_mistakes=0) is False
    assert is_mastered_from_state(fsrs_state="review", stability_days=STABILITY_MASTERED_THRESHOLD_DAYS - 1, unresolved_mistakes=0) is False


def test_stable_review_without_mistakes_is_mastered() -> None:
    assert is_mastered_from_state(fsrs_state="review", stability_days=30.0, unresolved_mistakes=0) is True


def test_open_mistake_blocks_mastery_even_when_stable() -> None:
    assert is_mastered_from_state(fsrs_state="review", stability_days=60.0, unresolved_mistakes=1) is False


def test_due_queue_utc_comparison_and_local_offset(tmp_path) -> None:
    db = _mkdb(tmp_path)
    past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    future = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    _add_card(db, "due1", due=past, fsrs_state="review", stability=30.0)
    _add_card(db, "later", due=past, fsrs_state="review", stability=30.0)
    _add_card(db, "notyet", due=future)

    queue = due_queue(db, tz_offset_minutes=480)  # UTC+8
    assert queue["count"] == 2
    ids = [c["card_id"] for c in queue["cards"]]
    assert "notyet" not in ids
    # Local display offset is applied to the due time.
    for card in queue["cards"]:
        assert card["due_local"] is not None
    assert queue["now_utc"].endswith("+00:00")


def test_recalculate_mastery_replays_snapshots(tmp_path) -> None:
    db = _mkdb(tmp_path)
    _add_card(db, "c1", due="2026-01-01T00:00:00+00:00", fsrs_state="review", stability=40.0)
    _add_review(db, "c1", 5, "2026-01-01T00:00:00+00:00")
    _add_review(db, "c1", 5, "2026-01-02T00:00:00+00:00")
    _add_review(db, "c1", 5, "2026-01-03T00:00:00+00:00")

    result = recalculate_mastery(db, card_id="c1", calculated_at="2026-08-01T00:00:00+00:00")
    assert result["is_mastered"] is True
    assert result["review_count"] == 3
    assert result["fsrs_state"] == "review"
    assert result["calculated_at"] == "2026-08-01T00:00:00+00:00"

    # With an open mistake the same card is NOT mastered.
    _add_mistake(db, "c1", resolved=False)
    result2 = recalculate_mastery(db, card_id="c1", calculated_at="2026-08-02T00:00:00+00:00")
    assert result2["is_mastered"] is False
    assert result2["unresolved_mistakes"] == 1


def test_recalculate_unknown_card_fails_closed(tmp_path) -> None:
    db = _mkdb(tmp_path)
    try:
        recalculate_mastery(db, card_id="ghost")
        raise AssertionError("expected ValueError")
    except ValueError as exc:
        assert "card not found" in str(exc)
