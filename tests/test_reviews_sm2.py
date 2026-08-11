"""Tests for knowledge_base.reviews (SM-2 scheduling core)."""

from __future__ import annotations

from datetime import datetime, timedelta

import knowledge_base.reviews as reviews
from knowledge_base.reviews import (
    _sm2_interval,
    get_due_reviews,
    get_review_history,
    schedule_review,
)

# ── SM-2 algorithm (pure) ──


def test_sm2_quality_out_of_range() -> None:
    try:
        _sm2_interval(-1, 0, 2.5)
        assert False, "expected ValueError"
    except ValueError:
        pass
    try:
        _sm2_interval(6, 0, 2.5)
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_sm2_failure_resets_interval() -> None:
    interval, ease, next_date = _sm2_interval(2, 30, 2.5)
    assert interval == 1
    # ease decreases: 2.5 + (0.1 - 3*(0.08+3*0.02)) = 2.5 + (0.1-0.42) = 2.18
    assert round(ease, 2) == 2.18
    assert next_date > datetime.now()


def test_sm2_first_success_interval_one() -> None:
    interval, ease, _ = _sm2_interval(5, 0, 2.5)
    assert interval == 1
    # ease increases: 2.5 + (0.1 - 0*(...)) = 2.6
    assert round(ease, 2) == 2.6


def test_sm2_second_review_six_days() -> None:
    interval, _, _ = _sm2_interval(4, 1, 2.6)
    assert interval == 6


def test_sm2_growth_by_ease() -> None:
    interval, _, _ = _sm2_interval(5, 6, 2.6)
    assert interval == int(round(6 * 2.6))


def test_sm2_ease_min_floor() -> None:
    _, ease, _ = _sm2_interval(0, 1, 1.3)  # worst quality on low ease
    assert ease >= 1.3


# ── schedule_review (storage-backed) ──


def _patch_review_storage(monkeypatch) -> dict:
    state = {"reviews": [], "cards": {}, "inserted": []}

    def fake_select_all(table, limit=500, order=""):
        if table == "kb_reviews":
            rows = list(state["reviews"])
            if order == "created_at DESC":
                rows.sort(key=lambda r: r["created_at"], reverse=True)
            return rows[:limit]
        return list(state["cards"].values())[:limit]

    def fake_select_one(table, sid):
        return state["cards"].get(sid)

    def fake_insert(table, row):
        state["inserted"].append((table, row))
        if table == "kb_reviews":
            state["reviews"].append(row)
        elif table == "kb_cards":
            state["cards"][row["id"]] = row

    monkeypatch.setattr(reviews, "select_all", fake_select_all)
    monkeypatch.setattr(reviews, "select_one", fake_select_one)
    monkeypatch.setattr(reviews, "insert", fake_insert)
    return state


def test_schedule_review_first_review(monkeypatch) -> None:
    state = _patch_review_storage(monkeypatch)
    state["cards"] = {"card_1": {"id": "card_1", "title": "C", "content": "x", "review_status": "draft"}}
    review = schedule_review("card_1", quality=5)
    assert review["card_id"] == "card_1"
    assert review["interval_days"] == 1
    assert review["quality"] == 5
    # card status updated: draft + quality 5 → reviewing
    assert state["cards"]["card_1"]["review_status"] == "reviewing"
    assert state["inserted"][0][0] == "kb_reviews"


def test_schedule_review_mastered_transition(monkeypatch) -> None:
    state = _patch_review_storage(monkeypatch)
    state["cards"] = {"card_1": {"id": "card_1", "title": "C", "content": "x", "review_status": "reviewing"}}
    state["reviews"] = [
        {
            "id": "r0",
            "card_id": "card_1",
            "quality": 4,
            "interval_days": 1,
            "ease_factor": 2.5,
            "next_review_at": (datetime.now() - timedelta(days=1)).isoformat(),
            "created_at": (datetime.now() - timedelta(days=7)).isoformat(),
        }
    ]
    review = schedule_review("card_1", quality=5)
    assert review["interval_days"] == 6  # prev 1 → 6
    assert state["cards"]["card_1"]["review_status"] == "mastered"


def test_schedule_review_failure_struggling(monkeypatch) -> None:
    state = _patch_review_storage(monkeypatch)
    state["cards"] = {"card_1": {"id": "card_1", "title": "C", "content": "x", "review_status": "reviewing"}}
    state["reviews"] = [
        {
            "id": "r0",
            "card_id": "card_1",
            "quality": 5,
            "interval_days": 6,
            "ease_factor": 2.6,
            "next_review_at": datetime.now().isoformat(),
            "created_at": (datetime.now() - timedelta(days=6)).isoformat(),
        }
    ]
    review = schedule_review("card_1", quality=1)
    assert review["interval_days"] == 1  # reset
    assert state["cards"]["card_1"]["review_status"] == "struggling"


# ── get_due_reviews / get_review_history ──


def test_get_due_reviews_filters_future(monkeypatch) -> None:
    state = _patch_review_storage(monkeypatch)
    state["cards"] = {
        "c_due": {"id": "c_due", "title": "Due", "content": "x"},
        "c_future": {"id": "c_future", "title": "Future", "content": "y"},
    }
    state["reviews"] = [
        {"id": "r1", "card_id": "c_due", "next_review_at": "2000-01-01T00:00:00", "ease_factor": 2.5, "interval_days": 1, "created_at": "2000-01-01"},
        {"id": "r2", "card_id": "c_future", "next_review_at": "2999-01-01T00:00:00", "ease_factor": 2.5, "interval_days": 10, "created_at": "2000-01-02"},
    ]
    due = get_due_reviews()
    ids = [d["card_id"] for d in due]
    assert "c_due" in ids
    assert "c_future" not in ids
    assert due[0]["title"] == "Due"


def test_get_review_history_filters_by_card(monkeypatch) -> None:
    state = _patch_review_storage(monkeypatch)
    state["reviews"] = [
        {"id": "a1", "card_id": "c1", "created_at": "2026-01-01"},
        {"id": "a2", "card_id": "c1", "created_at": "2026-01-02"},
        {"id": "b1", "card_id": "c2", "created_at": "2026-01-03"},
    ]
    history = get_review_history("c1")
    assert len(history) == 2
    assert all(r["card_id"] == "c1" for r in history)
