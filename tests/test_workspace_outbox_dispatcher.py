from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path


def _workspace_database(tmp_path: Path) -> Path:
    from shared.migration_runner import MigrationOperator

    database = tmp_path / "workspace.sqlite"
    with closing(sqlite3.connect(database)) as connection:
        connection.execute("CREATE TABLE sentinel(id TEXT PRIMARY KEY)")
        connection.commit()
    MigrationOperator(db_path=database, backup_dir=tmp_path / "backups").apply("workspace.sqlite")
    return database


def test_dispatch_once_delivers_one_pending_event_and_records_worker_checkpoint(tmp_path: Path) -> None:
    from app.workspace.job_outbox import enqueue_command
    from app.workspace.outbox_dispatcher import dispatch_once

    database = _workspace_database(tmp_path)
    receipt = enqueue_command(
        command_id="cmd-dispatch-001",
        command_type="intake.research",
        aggregate_id="package-001",
        payload={"package_id": "package-001"},
        db_path=database,
    )
    received: list[dict[str, object]] = []

    result = dispatch_once(
        db_path=database,
        worker_name="workspace-outbox-test",
        handler=received.append,
    )

    assert result == {"status": "delivered", "attempt": 1}
    assert received == [
        {
            "event_type": "intake.research.queued",
            "payload": {"package_id": "package-001"},
        }
    ]
    with closing(sqlite3.connect(database)) as connection:
        event = connection.execute(
            "SELECT state, attempt_count, lease_token, lease_expires_at, delivered_at "
            "FROM workspace_outbox_v1 WHERE event_id=?",
            (receipt["event_id"],),
        ).fetchone()
        checkpoint = connection.execute(
            "SELECT checkpoint_json FROM workspace_worker_checkpoints_v1 WHERE worker_name=?",
            ("workspace-outbox-test",),
        ).fetchone()
    assert event is not None
    assert event[:4] == ("delivered", 1, None, None)
    assert event[4]
    assert checkpoint is not None


def test_dispatch_once_marks_handler_failure_as_failed_with_a_checkpoint(tmp_path: Path) -> None:
    from app.workspace.job_outbox import enqueue_command
    from app.workspace.outbox_dispatcher import dispatch_once

    database = _workspace_database(tmp_path)
    receipt = enqueue_command(
        command_id="cmd-dispatch-failure",
        command_type="intake.research",
        aggregate_id="package-failure",
        payload={"package_id": "package-failure"},
        db_path=database,
    )

    def fail(_: dict[str, object]) -> None:
        raise RuntimeError("delivery unavailable")

    result = dispatch_once(
        db_path=database,
        worker_name="workspace-outbox-test",
        handler=fail,
    )

    assert result == {"status": "failed", "attempt": 1}
    with closing(sqlite3.connect(database)) as connection:
        event = connection.execute(
            "SELECT state, attempt_count, lease_token, lease_expires_at, delivered_at "
            "FROM workspace_outbox_v1 WHERE event_id=?",
            (receipt["event_id"],),
        ).fetchone()
        checkpoint = connection.execute(
            "SELECT checkpoint_json FROM workspace_worker_checkpoints_v1 WHERE worker_name=?",
            ("workspace-outbox-test",),
        ).fetchone()
    assert event == ("failed", 1, None, None, None)
    assert checkpoint is not None


def test_dispatch_once_reclaims_an_expired_lease_before_delivery(tmp_path: Path) -> None:
    from app.workspace.job_outbox import enqueue_command
    from app.workspace.outbox_dispatcher import dispatch_once

    database = _workspace_database(tmp_path)
    receipt = enqueue_command(
        command_id="cmd-dispatch-expired",
        command_type="intake.research",
        aggregate_id="package-expired",
        payload={"package_id": "package-expired"},
        db_path=database,
    )
    with closing(sqlite3.connect(database)) as connection:
        connection.execute(
            "UPDATE workspace_outbox_v1 SET state='leased', attempt_count=4, "
            "lease_token='expired-token', lease_expires_at='2000-01-01T00:00:00Z' "
            "WHERE event_id=?",
            (receipt["event_id"],),
        )
        connection.commit()

    result = dispatch_once(
        db_path=database,
        worker_name="workspace-outbox-test",
        handler=lambda _: None,
    )

    assert result == {"status": "delivered", "attempt": 5}
    with closing(sqlite3.connect(database)) as connection:
        event = connection.execute(
            "SELECT state, attempt_count, lease_token, lease_expires_at FROM workspace_outbox_v1 "
            "WHERE event_id=?",
            (receipt["event_id"],),
        ).fetchone()
    assert event == ("delivered", 5, None, None)
