"""Lease-fenced local dispatcher for Workspace outbox events."""
from __future__ import annotations

import json
import secrets
import sqlite3
from collections.abc import Callable
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

_LEASE_SECONDS = 30


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _timestamp(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def _require_schema(connection: sqlite3.Connection) -> None:
    tables = {
        str(row[0])
        for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }
    required = {"workspace_outbox_v1", "workspace_worker_checkpoints_v1"}
    if not required <= tables:
        raise RuntimeError("workspace outbox migration is pending")


def _claim_event(connection: sqlite3.Connection, *, now: datetime) -> dict[str, Any] | None:
    timestamp = _timestamp(now)
    row = connection.execute(
        "SELECT event_id, event_type, payload_json, attempt_count FROM workspace_outbox_v1 "
        "WHERE state='pending' OR (state='leased' AND lease_expires_at<=?) "
        "ORDER BY created_at, event_id LIMIT 1",
        (timestamp,),
    ).fetchone()
    if row is None:
        return None
    try:
        payload = json.loads(str(row["payload_json"]))
    except json.JSONDecodeError as exc:
        raise RuntimeError("workspace outbox payload is malformed") from exc
    if not isinstance(payload, dict):
        raise RuntimeError("workspace outbox payload is invalid")
    token = secrets.token_urlsafe(24)
    expires_at = _timestamp(now + timedelta(seconds=_LEASE_SECONDS))
    updated = connection.execute(
        "UPDATE workspace_outbox_v1 SET state='leased', attempt_count=attempt_count+1, "
        "lease_token=?, lease_expires_at=?, updated_at=? "
        "WHERE event_id=? AND (state='pending' OR (state='leased' AND lease_expires_at<=?))",
        (token, expires_at, timestamp, str(row["event_id"]), timestamp),
    ).rowcount
    if updated != 1:
        return None
    return {
        "event_id": str(row["event_id"]),
        "event_type": str(row["event_type"]),
        "payload": payload,
        "attempt": int(row["attempt_count"]) + 1,
        "lease_token": token,
    }


def _record_checkpoint(
    connection: sqlite3.Connection, *, worker_name: str, checkpoint: dict[str, Any], now: datetime
) -> None:
    connection.execute(
        "INSERT INTO workspace_worker_checkpoints_v1(worker_name, checkpoint_json, updated_at) "
        "VALUES (?, ?, ?) ON CONFLICT(worker_name) DO UPDATE SET "
        "checkpoint_json=excluded.checkpoint_json, updated_at=excluded.updated_at",
        (
            worker_name,
            json.dumps(checkpoint, ensure_ascii=True, separators=(",", ":"), sort_keys=True),
            _timestamp(now),
        ),
    )


def _confirmation_is_valid(claimed: dict[str, Any], confirmation: object) -> bool:
    return (
        isinstance(confirmation, dict)
        and confirmation.get("event_id") == claimed["event_id"]
        and confirmation.get("lease_token") == claimed["lease_token"]
        and isinstance(confirmation.get("proof"), dict)
        and bool(confirmation["proof"])
    )


def dispatch_once(
    *, db_path: str | Path, worker_name: str, handler: Callable[[dict[str, object]], object]
) -> dict[str, object]:
    """Deliver at most one pending or expired leased event through a lease-fenced handler."""

    if not worker_name:
        raise ValueError("workspace dispatcher requires a worker name")
    database = Path(db_path)
    with closing(sqlite3.connect(database, timeout=30.0)) as connection:
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout=30000")
        connection.execute("BEGIN IMMEDIATE")
        try:
            _require_schema(connection)
            claimed = _claim_event(connection, now=_now())
            connection.commit()
        except Exception:
            connection.rollback()
            raise
    if claimed is None:
        return {"status": "idle"}

    try:
        confirmation = handler(
            {
                "event_id": claimed["event_id"],
                "event_type": claimed["event_type"],
                "payload": claimed["payload"],
                "lease_token": claimed["lease_token"],
            }
        )
        if not _confirmation_is_valid(claimed, confirmation):
            raise RuntimeError("workspace handler confirmation is invalid")
    except Exception:
        final_state = "failed"
        delivered_at = None
    else:
        final_state = "delivered"
        delivered_at = _timestamp(_now())

    finished_at = _now()
    with closing(sqlite3.connect(database, timeout=30.0)) as connection:
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout=30000")
        connection.execute("BEGIN IMMEDIATE")
        try:
            _require_schema(connection)
            updated = connection.execute(
                "UPDATE workspace_outbox_v1 SET state=?, lease_token=NULL, "
                "lease_expires_at=NULL, delivered_at=?, updated_at=? "
                "WHERE event_id=? AND state='leased' AND lease_token=? AND lease_expires_at>?",
                (
                    final_state,
                    delivered_at,
                    _timestamp(finished_at),
                    claimed["event_id"],
                    claimed["lease_token"],
                    _timestamp(finished_at),
                ),
            ).rowcount
            if updated != 1:
                raise RuntimeError("workspace outbox lease was lost before delivery confirmation")
            _record_checkpoint(
                connection,
                worker_name=worker_name,
                checkpoint={"attempt": claimed["attempt"], "state": final_state},
                now=finished_at,
            )
            connection.commit()
        except Exception:
            connection.rollback()
            raise
    return {"status": final_state, "attempt": claimed["attempt"]}
