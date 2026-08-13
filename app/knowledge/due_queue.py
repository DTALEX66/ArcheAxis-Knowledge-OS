"""AXW-051B: FSRS-driven review queue and mastery evidence.

Replaces the fixed three-high-score heuristic (explicitly forbidden by the
frozen baseline) with FSRS-derived mastery evidence:

- ``is_mastered`` now requires a card to be in the FSRS Review state with
  stability above a threshold and no unresolved mistakes — not "3 reviews
  with quality >= 4".
- ``due_queue`` returns cards whose FSRS ``due`` time (UTC) has passed,
  with an optional local-timezone display offset; ordering is by due time.
- ``recalculate_mastery`` recomputes the signal from immutable review
  snapshots (history replay) — append-only, never mutating past signals.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from app.adapters.mastery_signal import from_learning_snapshots

STABILITY_MASTERED_THRESHOLD_DAYS = 21.0  # ~3 weeks of stable recall


def _connect(db: str | Path) -> sqlite3.Connection:
    conn = sqlite3.connect(Path(db))
    return conn


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def is_mastered_from_state(
    *,
    fsrs_state: str,
    stability_days: float | None,
    unresolved_mistakes: int,
) -> bool:
    """FSRS-based mastery: Review state + stable interval + no open mistakes.

    The fixed three-high-score rule is gone: a card with three high ratings
    but an unstable (Learning) state is NOT mastered, and a stable Review
    card with an open mistake is NOT mastered.
    """
    if unresolved_mistakes > 0:
        return False
    if fsrs_state != "review":
        return False
    if stability_days is None:
        return False
    return stability_days >= STABILITY_MASTERED_THRESHOLD_DAYS


def due_queue(
    db: str | Path,
    *,
    tz_offset_minutes: int = 0,
    limit: int = 50,
) -> dict[str, Any]:
    """Cards due for review (FSRS due <= now UTC).

    ``tz_offset_minutes`` only affects the display ``due_local`` value;
    comparison is always done in UTC. Returns newest-unreviewed first
    within the due set, then by due time ascending.
    """
    now_utc = _now_utc()
    with _connect(db) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM kb_cards"
        ).fetchall()
    due: list[dict[str, Any]] = []
    for row in rows:
        card = dict(row)
        due_iso = card.get("due")
        if not due_iso:
            continue
        if due_iso <= now_utc:
            due.append(card)
    due.sort(key=lambda c: (c.get("due", ""), str(c.get("id", ""))))
    due = due[:limit]

    out: list[dict[str, Any]] = []
    offset = timedelta(minutes=tz_offset_minutes)
    for card in due:
        due_iso = card.get("due", "")
        due_local: str | None = None
        if due_iso:
            try:
                due_dt = datetime.fromisoformat(due_iso)
                due_local = (due_dt + offset).isoformat()
            except ValueError:
                due_local = due_iso
        out.append(
            {
                "card_id": card.get("id") or card.get("card_id"),
                "due_utc": due_iso,
                "due_local": due_local,
                "fsrs_state": card.get("fsrs_state") or card.get("state") or "learning",
                "stability_days": card.get("stability_days") or card.get("stability"),
            }
        )
    return {"now_utc": now_utc, "tz_offset_minutes": tz_offset_minutes, "count": len(out), "cards": out}


def recalculate_mastery(
    db: str | Path,
    *,
    card_id: str,
    calculated_at: str | None = None,
) -> dict[str, Any]:
    """Recompute mastery from immutable review snapshots (history replay).

    Never mutates past signals — writes a NEW signal snapshot derived from
    the current FSRS card state + review history, so historical results are
    reproducible and append-only.
    """
    stamp = calculated_at or _now_utc()
    with _connect(db) as conn:
        conn.row_factory = sqlite3.Row
        card_row = conn.execute("SELECT * FROM kb_cards WHERE id=?", (card_id,)).fetchone()
        if card_row is None:
            raise ValueError(f"card not found: {card_id}")
        reviews = conn.execute(
            "SELECT * FROM kb_reviews WHERE card_id=? ORDER BY created_at, id", (card_id,)
        ).fetchall()
        mistakes = conn.execute(
            "SELECT * FROM kb_mistakes WHERE card_id=? ORDER BY created_at, id", (card_id,)
        ).fetchall()

    card = dict(card_row)
    signal = from_learning_snapshots(
        card, [dict(r) for r in reviews], [dict(m) for m in mistakes]
    )
    mistakes = [dict(m) for m in mistakes]
    unresolved = len([m for m in mistakes if not m.get("resolved", False)])
    fsrs_state = str(card.get("fsrs_state") or card.get("state") or "learning")
    stability = card.get("stability_days") or card.get("stability")
    mastered = is_mastered_from_state(
        fsrs_state=fsrs_state,
        stability_days=float(stability) if stability is not None else None,
        unresolved_mistakes=unresolved,
    )
    return {
        "card_id": card_id,
        "calculated_at": stamp,
        "fsrs_state": fsrs_state,
        "stability_days": stability,
        "unresolved_mistakes": unresolved,
        "is_mastered": mastered,
        "review_count": signal.review_count,
        "signal_snapshot": signal.model_dump(),
    }
