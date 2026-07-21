"""Atomic local Workspace command receipts, jobs, and outbox events."""
from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _canonical_json(value: dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True)


def command_request_fingerprint(
    *,
    command_type: str,
    aggregate_id: str,
    payload: dict[str, Any],
    job_state: str,
    event_type: str,
) -> str:
    """Return the canonical semantic fingerprint shared by command writes and strict reads."""
    return sha256(
        _canonical_json(
            {
                "aggregate_id": aggregate_id,
                "command_type": command_type,
                "event_type": event_type,
                "job_state": job_state,
                "payload": payload,
            }
        ).encode("utf-8")
    ).hexdigest()


def _require_schema(connection: sqlite3.Connection) -> None:
    tables = {
        str(row[0])
        for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }
    required = {
        "workspace_jobs_v1",
        "workspace_outbox_v1",
        "workspace_command_receipts_v1",
    }
    if not required <= tables:
        raise RuntimeError("workspace job/outbox migration is pending")


def record_command_in_transaction(
    connection: sqlite3.Connection,
    *,
    command_id: str,
    command_type: str,
    aggregate_id: str,
    payload: dict[str, Any],
    job_state: str,
    event_type: str,
) -> dict[str, str]:
    """Write a command receipt, job, and outbox event without committing the caller's transaction."""

    if not command_id or not command_type or not aggregate_id:
        raise ValueError("workspace command requires id, type, and aggregate")
    if job_state not in {"queued", "succeeded"}:
        raise ValueError("workspace command has an invalid initial job state")
    _require_schema(connection)
    request_json = _canonical_json(payload)
    request_fingerprint = command_request_fingerprint(
        command_type=command_type,
        aggregate_id=aggregate_id,
        payload=payload,
        job_state=job_state,
        event_type=event_type,
    )
    job_id = "job_" + sha256(command_id.encode("utf-8")).hexdigest()[:24]
    event_id = "outbox_" + sha256(command_id.encode("utf-8")).hexdigest()[:24]
    timestamp = _now()
    result = {"command_id": command_id, "event_id": event_id, "job_id": job_id}
    existing = connection.execute(
        "SELECT request_fingerprint, result_json "
        "FROM workspace_command_receipts_v1 WHERE command_id=?",
        (command_id,),
    ).fetchone()
    if existing is not None:
        if existing["request_fingerprint"] != request_fingerprint:
            raise RuntimeError("command id conflicts with recorded request")
        stored_result = json.loads(existing["result_json"])
        if stored_result != result:
            raise RuntimeError("recorded workspace command receipt is invalid")
        return stored_result
    connection.execute(
        "INSERT INTO workspace_jobs_v1("
        "job_id, command_id, job_type, aggregate_id, state, payload_json, "
        "correlation_id, causation_id, created_at, updated_at"
        ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            job_id,
            command_id,
            command_type,
            aggregate_id,
            job_state,
            request_json,
            command_id,
            command_id,
            timestamp,
            timestamp,
        ),
    )
    connection.execute(
        "INSERT INTO workspace_outbox_v1("
        "event_id, job_id, event_type, payload_json, state, created_at, updated_at"
        ") VALUES (?, ?, ?, ?, 'pending', ?, ?)",
        (event_id, job_id, event_type, request_json, timestamp, timestamp),
    )
    connection.execute(
        "INSERT INTO workspace_command_receipts_v1("
        "command_id, command_type, request_fingerprint, job_id, result_json, created_at"
        ") VALUES (?, ?, ?, ?, ?, ?)",
        (command_id, command_type, request_fingerprint, job_id, _canonical_json(result), timestamp),
    )
    return result


def record_completed_command(
    connection: sqlite3.Connection,
    *,
    command_id: str,
    command_type: str,
    aggregate_id: str,
    payload: dict[str, Any],
) -> dict[str, str]:
    """Record a synchronously completed Workspace command in the caller's transaction."""

    return record_command_in_transaction(
        connection,
        command_id=command_id,
        command_type=command_type,
        aggregate_id=aggregate_id,
        payload=payload,
        job_state="succeeded",
        event_type=command_type + ".succeeded",
    )


def enqueue_command(
    *,
    command_id: str,
    command_type: str,
    aggregate_id: str,
    payload: dict[str, Any],
    db_path: str | Path,
) -> dict[str, str]:
    """Atomically write one command receipt, queued job, and pending outbox event."""

    database = Path(db_path)
    with closing(sqlite3.connect(database)) as connection:
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout=30000")
        connection.execute("BEGIN IMMEDIATE")
        try:
            result = record_command_in_transaction(
                connection,
                command_id=command_id,
                command_type=command_type,
                aggregate_id=aggregate_id,
                payload=payload,
                job_state="queued",
                event_type=command_type + ".queued",
            )
            connection.commit()
        except Exception:
            connection.rollback()
            raise
    return result
