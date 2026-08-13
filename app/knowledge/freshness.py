"""AXW-024D: freshness / scope / revoke projection for governed knowledge.

Records append-only freshness events (activate/revoke/supersede/revalidate)
for machine knowledge units and evidence-scoped knowledge, then projects the
*currently effective* set for AI retrieval and learning:

- ``freshness_status`` tells whether a unit is currently active, expired,
  revoked, or superseded at a given timestamp;
- ``project_active`` filters to units that are fresh, not revoked, not
  superseded, and scope-matching — projections can only ever read the
  effective set (GOV-001 / AXW-024D fail-closed).

Events are append-only: revoking then revalidating keeps the full history.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_SCHEMA = """
CREATE TABLE IF NOT EXISTS freshness_events (
    event_id TEXT PRIMARY KEY,
    unit_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    effective_from TEXT NOT NULL,
    effective_until TEXT,
    scope TEXT,
    actor TEXT NOT NULL,
    note TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_freshness_unit ON freshness_events(unit_id);
CREATE INDEX IF NOT EXISTS idx_freshness_scope ON freshness_events(scope);
"""

_VALID_EVENTS = frozenset({"activate", "revoke", "supersede", "revalidate"})


class FreshnessError(ValueError):
    """Raised when a freshness event or projection is invalid."""


@dataclass(frozen=True)
class FreshnessEvent:
    event_id: str
    unit_id: str
    event_type: str
    effective_from: str
    effective_until: str | None
    scope: str | None
    actor: str
    note: str | None
    created_at: str


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _connect(db: str | Path) -> sqlite3.Connection:
    conn = sqlite3.connect(Path(db))
    conn.executescript(_SCHEMA)
    return conn


def record_event(
    db: str | Path,
    *,
    unit_id: str,
    event_type: str,
    actor: str,
    scope: str | None = None,
    note: str | None = None,
    effective_until: str | None = None,
) -> FreshnessEvent:
    """Append one freshness event (never mutates history)."""
    if not unit_id:
        raise FreshnessError("unit_id is required")
    if event_type not in _VALID_EVENTS:
        raise FreshnessError(f"invalid event type: {event_type}")
    if not actor:
        raise FreshnessError("actor is required for audit")

    event_id = f"fx_{abs(hash((unit_id, event_type, _now(), actor))) % (10**12):012d}"
    created_at = _now()
    with _connect(db) as conn:
        conn.execute(
            "INSERT INTO freshness_events "
            "(event_id, unit_id, event_type, effective_from, effective_until, scope, actor, note, created_at) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (event_id, unit_id, event_type, created_at, effective_until, scope, actor, note, created_at),
        )
        conn.commit()
    return FreshnessEvent(
        event_id=event_id,
        unit_id=unit_id,
        event_type=event_type,
        effective_from=created_at,
        effective_until=effective_until,
        scope=scope,
        actor=actor,
        note=note,
        created_at=created_at,
    )


def _latest_event(conn: sqlite3.Connection, unit_id: str) -> sqlite3.Row | None:
    # rowid is the monotonic insertion order — created_at can collide within
    # the same millisecond and event_id is opaque, so rowid is authoritative.
    conn.row_factory = sqlite3.Row
    return conn.execute(
        "SELECT * FROM freshness_events WHERE unit_id=? ORDER BY rowid DESC LIMIT 1",
        (unit_id,),
    ).fetchone()


def freshness_status(
    db: str | Path, *, unit_id: str, at: str | None = None
) -> dict[str, Any]:
    """Current governance status for one unit at ``at`` (default now).

    Resolution order: latest event wins. ``supersede`` and ``revoke`` are
    terminal until a later ``revalidate``/``activate``; ``effective_until``
    expiry is checked against ``at``.
    """
    now = at or _now()
    with _connect(db) as conn:
        row = _latest_event(conn, unit_id)
        if row is None:
            return {"unit_id": unit_id, "status": "unknown", "at": now}
        event_type = row["event_type"]
        if event_type == "revoke":
            status = "revoked"
        elif event_type == "supersede":
            status = "superseded"
        elif event_type in ("activate", "revalidate"):
            if row["effective_until"] and row["effective_until"] < now:
                status = "expired"
            else:
                status = "active"
        else:  # pragma: no cover - _VALID_EVENTS guards
            status = "unknown"
        return {
            "unit_id": unit_id,
            "status": status,
            "scope": row["scope"],
            "event_type": event_type,
            "at": now,
        }


def project_active(
    db: str | Path,
    *,
    unit_ids: list[str],
    scope: str | None = None,
    at: str | None = None,
) -> list[str]:
    """Project the currently effective unit ids (fresh + scope-matching).

    Fail-closed: any unit whose status is not ``active`` (expired, revoked,
    superseded, unknown) is excluded from the projection, so AI retrieval
    and learning only ever read the effective set.
    """
    now = at or _now()
    result: list[str] = []
    with _connect(db) as conn:
        for unit_id in unit_ids:
            row = _latest_event(conn, unit_id)
            if row is None:
                continue  # unknown governance → excluded (fail-closed)
            if row["event_type"] not in ("activate", "revalidate"):
                continue
            if row["effective_until"] and row["effective_until"] < now:
                continue
            if scope is not None and row["scope"] is not None and row["scope"] != scope:
                continue  # scope mismatch → excluded
            result.append(unit_id)
    return result
