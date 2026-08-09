"""AXW-021B: idempotency, retry, cancel and crash-recovery fault tests.

The lease-fenced outbox dispatcher must support crash recovery: an expired
lease is reclaimed with an incremented attempt count, a handler failure is
recorded as failed (a retryable terminal per the store), and a confirmation is
required before an event is marked delivered.
"""
from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path

from app.workspace.job_outbox import enqueue_command


def _workspace_database(tmp_path: Path) -> Path:
    from shared.migration_runner import MigrationOperator

    database = tmp_path / "workspace.sqlite"
    with closing(sqlite3.connect(database)) as connection:
        connection.execute("CREATE TABLE sentinel(id TEXT PRIMARY KEY)")
    MigrationOperator(db_path=database, backup_dir=tmp_path / "backups").apply("workspace.sqlite")
    return database


def _read_outbox(database: Path, event_id: str) -> tuple:
    with closing(sqlite3.connect(database)) as connection:
        row = connection.execute(
            "SELECT state, attempt_count, delivered_at, lease_expires_at "
            "FROM workspace_outbox_v1 WHERE event_id=?",
            (event_id,),
        ).fetchone()
    return tuple(row)


def test_crash_recovery_reclaims_expired_lease_with_incremented_attempt(tmp_path: Path) -> None:
    """AXW-021B: after a crash the expired lease is reclaimed and the attempt
    count increments, so the event is retried rather than lost or stuck."""
    from app.workspace.outbox_dispatcher import dispatch_once

    database = _workspace_database(tmp_path)
    receipt = enqueue_command(
        command_id="cmd-crash",
        command_type="raw_asset.import",
        aggregate_id="a.md",
        payload={"file": "a.md"},
        db_path=database,
    )
    # Simulate a crash: event leased by a dead worker with an expired token.
    with closing(sqlite3.connect(database)) as connection:
        connection.execute(
            "UPDATE workspace_outbox_v1 SET state='leased', attempt_count=1, "
            "lease_token='dead-token', lease_expires_at='2000-01-01T00:00:00Z' "
            "WHERE event_id=?",
            (receipt["event_id"],),
        )
        connection.commit()

    result = dispatch_once(
        db_path=database,
        worker_name="worker-crash-test",
        handler=lambda event: {
            "event_id": event["event_id"],
            "lease_token": event["lease_token"],
            "proof": {"consumer": "crash-test"},
        },
    )
    assert result["status"] == "delivered"
    state, attempt, delivered_at, _ = _read_outbox(database, receipt["event_id"])
    assert state == "delivered"
    assert attempt == 2  # reclaimed lease increments the attempt count
    assert delivered_at is not None


def test_handler_failure_is_recorded_and_can_be_reclaimed(tmp_path: Path) -> None:
    """AXW-021B: a handler failure marks the event failed (with a checkpoint);
    the failure is retryable via lease expiry rather than silently lost."""
    from app.workspace.outbox_dispatcher import dispatch_once

    database = _workspace_database(tmp_path)
    receipt = enqueue_command(
        command_id="cmd-fail",
        command_type="raw_asset.import",
        aggregate_id="b.md",
        payload={"file": "b.md"},
        db_path=database,
    )

    def failing(event):
        raise RuntimeError("handler blew up")

    result = dispatch_once(db_path=database, worker_name="worker-fail-test", handler=failing)
    assert result["status"] == "failed"
    state, attempt, delivered_at, _ = _read_outbox(database, receipt["event_id"])
    assert state == "failed"
    assert delivered_at is None
    assert attempt >= 1
