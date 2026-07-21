from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path


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
