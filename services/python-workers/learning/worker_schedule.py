"""FSRS scheduling worker (R05).

Single scheduling authority for review intervals: this worker reuses the
existing py-fsrs donor (``shared/learning_scheduler.py``) instead of the
temporary interval ladder that ``archeaxis_domain::learning::suggest_next_
interval`` still carries as a placeholder. The Rust Core remains the only
database writer; it asks this worker for the next due date and persists the
answer, so no second scheduling implementation is introduced.

Contract: one JSON request on stdin -> one JSON response on stdout.

Request::

    {"item_key": "card-1",
     "rating": 1..4,            # optional if "correct" is given
     "correct": true,           # optional convenience mapping
     "state": {"state": "review", "stability": 30.0, "difficulty": 5.0,
               "due": "2026-09-01T00:00:00+00:00",
               "last_review": "2026-08-01T00:00:00+00:00", "step": 0},
     "now": "2026-09-02T00:00:00+00:00"}

Response::

    {"item_key": "card-1", "authority": "fsrs", "next_review_days": 34,
     "due": "2026-10-06T00:00:00+00:00", "scheduled_days": 34,
     "state": "review", "stability": 34.2, "difficulty": 5.1,
     "step": null, "last_review": "2026-09-02T00:00:00+00:00"}

The response's state/step/stability/difficulty/due/last_review fields are the
lossless next request state. Display rounding belongs in the UI, never in the
persisted scheduler parameters. Learning and relearning steps survive restarts.

Failure is explicit and fail-closed::

    {"error": "...", "authority": "fsrs"}

An unavailable or unusable scheduler never falls back to the ladder - the
caller must record the missing schedule instead of inventing one.
"""

from __future__ import annotations

import contextlib
import json
import math
import sys
from datetime import datetime, timezone

__all__ = ["schedule", "parse_state", "rating_for"]

_RATING_NAMES = {"again": 1, "hard": 2, "good": 3, "easy": 4}


def rating_for(request: dict) -> int:
    """Resolve the FSRS rating (1..4) from the request, or raise ValueError."""
    rating = request.get("rating")
    if isinstance(rating, int) and not isinstance(rating, bool) and 1 <= rating <= 4:
        return rating
    if isinstance(rating, str) and rating.strip().lower() in _RATING_NAMES:
        return _RATING_NAMES[rating.strip().lower()]
    if "rating" in request:
        raise ValueError("rating must be 1..4 or again/hard/good/easy")
    correct = request.get("correct")
    if correct is True:
        return 3
    if correct is False:
        return 1
    raise ValueError("request needs rating 1..4 or a boolean correct")


def _parse_time(value: object, field: str) -> datetime | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{field} must be an ISO timestamp string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:  # pragma: no cover - defensive
        raise ValueError(f"{field} is not an ISO timestamp") from exc
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def parse_state(request: dict) -> dict:
    """Validate the persisted card fields carried by the request."""
    state = request.get("state")
    if state is None:
        state = {}
    if not isinstance(state, dict):
        raise ValueError("state must be an object")
    out: dict = {}
    for field in ("stability", "difficulty"):
        value = state.get(field)
        if value is not None:
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                raise ValueError(f"state.{field} must be a number")
            if not math.isfinite(value):
                raise ValueError(f"state.{field} must be finite")
            out[field] = float(value)
    step = state.get("step")
    if step is not None:
        if not isinstance(step, int) or isinstance(step, bool) or step < 0:
            raise ValueError("state.step must be a non-negative integer")
        out["step"] = step
    elif "step" in state:
        out["step"] = None
    name = state.get("state")
    if name is not None:
        if not isinstance(name, str):
            raise ValueError("state.state must be a string")
        out["state"] = name.strip().lower()
    out["due"] = _parse_time(state.get("due"), "state.due")
    out["last_review"] = _parse_time(state.get("last_review"), "state.last_review")
    return out


def _build_card(fields: dict):
    from fsrs import Card, State  # imported lazily so the module stays importable

    card = Card()
    if fields.get("stability") is not None:
        card.stability = fields["stability"]
    if fields.get("difficulty") is not None:
        card.difficulty = fields["difficulty"]
    if "step" in fields:
        card.step = fields["step"]
    if fields.get("due") is not None:
        card.due = fields["due"]
    if fields.get("last_review") is not None:
        card.last_review = fields["last_review"]
    name = fields.get("state")
    if name:
        for member in State:
            if member.name.strip().lower() == name:
                card.state = member
                break
        else:
            raise ValueError(f"unknown card state {name!r}")
    return card


def schedule(request: dict) -> dict:
    """Compute the next review with the reused FSRS scheduler."""
    if not isinstance(request, dict):
        raise ValueError("request must be an object")
    item_key = request.get("item_key")
    if not isinstance(item_key, str) or not item_key.strip():
        raise ValueError("item_key is required")
    rating_value = rating_for(request)
    fields = parse_state(request)
    now = _parse_time(request.get("now"), "now") or datetime.now(timezone.utc)

    from fsrs import Rating

    from shared.learning_scheduler import LearningScheduler, card_state_name

    card = _build_card(fields)
    # Deterministic scheduling: py-fsrs fuzzes intervals by default, which would
    # make the same card+rating return different due dates on replay/restart.
    scheduler = LearningScheduler(enable_fuzzing=False)
    updated, summary = scheduler.review(card, Rating(rating_value), now)
    scheduled_days = int(summary.get("scheduled_days") or 0)
    due = summary.get("due") or (updated.due.isoformat() if updated.due else None)
    if due is None:
        raise ValueError("scheduler returned no due date")
    return {
        "item_key": item_key,
        "authority": "fsrs",
        "next_review_days": scheduled_days,
        "scheduled_days": scheduled_days,
        "due": due,
        "state": summary.get("state") or card_state_name(updated),
        "stability": updated.stability,
        "difficulty": updated.difficulty,
        "step": updated.step,
        "last_review": updated.last_review.isoformat() if updated.last_review else None,
        "rating": rating_value,
        "reviewed_at": now.isoformat(),
    }


def main() -> int:
    with contextlib.suppress(Exception):
        sys.stdout.reconfigure(encoding="utf-8")
    raw = sys.stdin.read()
    try:
        request = json.loads(raw)
        response = schedule(request)
    except Exception as exc:  # noqa: BLE001 - explicit failure, never a ladder
        response = {"error": f"{type(exc).__name__}: {exc}", "authority": "fsrs"}
    print(json.dumps(response, ensure_ascii=False))
    return 1 if "error" in response else 0


if __name__ == "__main__":
    raise SystemExit(main())
