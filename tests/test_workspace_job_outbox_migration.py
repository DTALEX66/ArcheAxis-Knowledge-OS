from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path

import pytest


def test_workspace_owner_applies_job_outbox_schema_and_rolls_back_safely(tmp_path: Path) -> None:
    from shared.migration_runner import MigrationOperator

    database = tmp_path / "workspace.sqlite"
    with closing(sqlite3.connect(database)) as connection:
        connection.execute("CREATE TABLE sentinel(id TEXT PRIMARY KEY)")
        connection.execute("INSERT INTO sentinel VALUES ('preserve')")
        connection.commit()

    operator = MigrationOperator(db_path=database, backup_dir=tmp_path / "backups")
    applied = operator.apply("workspace.sqlite")

    assert applied["state"] == "applied"
    assert applied["provenance"]["backup_sha256"]
    with closing(sqlite3.connect(database)) as connection:
        tables = {
            str(row[0])
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        assert {
            "workspace_jobs_v1",
            "workspace_outbox_v1",
            "workspace_command_receipts_v1",
            "workspace_worker_checkpoints_v1",
        } <= tables
        assert connection.execute("SELECT id FROM sentinel").fetchone()[0] == "preserve"

    rolled_back = operator.rollback("workspace.sqlite")

    assert rolled_back["state"] == "rolled_back"
    with closing(sqlite3.connect(database)) as connection:
        tables = {
            str(row[0])
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        assert "workspace_jobs_v1" not in tables
        assert "workspace_outbox_v1" not in tables
        assert "workspace_command_receipts_v1" not in tables
        assert "workspace_worker_checkpoints_v1" not in tables
        assert connection.execute("SELECT id FROM sentinel").fetchone()[0] == "preserve"


def test_workspace_schema_and_ledger_roll_back_when_operator_callback_fails(tmp_path: Path) -> None:
    from shared import workspace_migration

    database = tmp_path / "workspace.sqlite"
    with closing(sqlite3.connect(database)) as connection:
        connection.execute("CREATE TABLE sentinel(id TEXT PRIMARY KEY)")
        connection.commit()

    def fail_before_commit(_connection, _run) -> None:
        raise RuntimeError("injected operator ledger failure")

    with pytest.raises(RuntimeError, match="injected operator ledger failure"):
        workspace_migration.migrate(
            db_path=database,
            backup_dir=tmp_path / "backups",
            before_commit=fail_before_commit,
            backup_when_pending=False,
            _operator_capability=workspace_migration._OP_CAPABILITY,
        )

    with closing(sqlite3.connect(database)) as connection:
        tables = {
            str(row[0])
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        assert tables == {"sentinel"}


def test_workspace_backup_is_created_after_write_lock_blocks_concurrent_writers(
    monkeypatch, tmp_path: Path,
) -> None:
    from shared import workspace_migration

    database = tmp_path / "workspace.sqlite"
    with closing(sqlite3.connect(database)) as connection:
        connection.execute("CREATE TABLE sentinel(id TEXT PRIMARY KEY)")
        connection.commit()
    original_backup = workspace_migration.migration._create_backup
    writer_outcome = "backup hook was not called"

    def backup_after_lock(*args, **kwargs):
        nonlocal writer_outcome
        with closing(sqlite3.connect(database, timeout=0.0)) as writer:
            try:
                writer.execute("INSERT INTO sentinel VALUES ('late-writer')")
                writer.commit()
            except sqlite3.OperationalError as exc:
                writer_outcome = str(exc)
                writer.rollback()
            else:
                writer_outcome = "concurrent writer committed"
        return original_backup(*args, **kwargs)

    monkeypatch.setattr(workspace_migration.migration, "_create_backup", backup_after_lock)
    workspace_migration.migrate(
        db_path=database,
        backup_dir=tmp_path / "backups",
        _operator_capability=workspace_migration._OP_CAPABILITY,
    )

    assert "locked" in writer_outcome.lower(), writer_outcome
    with closing(sqlite3.connect(database)) as connection:
        assert connection.execute("SELECT COUNT(*) FROM sentinel").fetchone()[0] == 0


def test_workspace_owner_status_and_reapply_fail_closed_on_live_schema_drift(
    tmp_path: Path,
) -> None:
    from shared.migration_runner import MigrationOperator

    database = tmp_path / "workspace.sqlite"
    with closing(sqlite3.connect(database)) as connection:
        connection.execute("CREATE TABLE sentinel(id TEXT PRIMARY KEY)")
        connection.commit()
    operator = MigrationOperator(db_path=database, backup_dir=tmp_path / "backups")
    operator.apply("workspace.sqlite")
    with closing(sqlite3.connect(database)) as connection:
        connection.execute("DROP INDEX idx_workspace_outbox_state_v1")
        connection.commit()

    status = next(item for item in operator.status() if item["owner"] == "workspace.sqlite")
    assert status["state"] == "failed"
    assert status["provenance"]["reason"] == "live_schema_drift"
    with pytest.raises(RuntimeError, match="workspace|schema|drift"):
        operator.apply("workspace.sqlite")


def test_workspace_owner_rejects_malformed_unrecorded_owned_table(tmp_path: Path) -> None:
    from shared.migration_runner import MigrationOperator

    database = tmp_path / "workspace.sqlite"
    with closing(sqlite3.connect(database)) as connection:
        connection.execute("CREATE TABLE workspace_jobs_v1(job_id TEXT PRIMARY KEY)")
        connection.commit()
    operator = MigrationOperator(db_path=database, backup_dir=tmp_path / "backups")

    with pytest.raises(RuntimeError, match="workspace.*schema|schema.*workspace"):
        operator.apply("workspace.sqlite")

    with closing(sqlite3.connect(database)) as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE name='workspace_outbox_v1'"
        ).fetchone()[0] == 0
