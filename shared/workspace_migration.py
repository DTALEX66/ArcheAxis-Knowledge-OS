"""Formal SQLite migration for Workspace jobs, outbox, and recovery receipts."""
from __future__ import annotations

import sqlite3
from collections.abc import Callable
from contextlib import closing
from pathlib import Path

from shared import migration

WORKSPACE_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS workspace_jobs_v1 (
    job_id TEXT PRIMARY KEY,
    command_id TEXT NOT NULL UNIQUE,
    job_type TEXT NOT NULL,
    aggregate_id TEXT NOT NULL,
    state TEXT NOT NULL CHECK(state IN ('queued', 'leased', 'succeeded', 'failed')),
    attempt_count INTEGER NOT NULL DEFAULT 0 CHECK(attempt_count >= 0),
    lease_token TEXT,
    lease_expires_at TEXT,
    payload_json TEXT NOT NULL,
    correlation_id TEXT NOT NULL,
    causation_id TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_workspace_jobs_state_v1
ON workspace_jobs_v1(state, created_at);

CREATE TABLE IF NOT EXISTS workspace_outbox_v1 (
    event_id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL UNIQUE REFERENCES workspace_jobs_v1(job_id),
    event_type TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    state TEXT NOT NULL CHECK(state IN ('pending', 'leased', 'delivered', 'failed')),
    attempt_count INTEGER NOT NULL DEFAULT 0 CHECK(attempt_count >= 0),
    lease_token TEXT,
    lease_expires_at TEXT,
    delivered_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_workspace_outbox_state_v1
ON workspace_outbox_v1(state, created_at);

CREATE TABLE IF NOT EXISTS workspace_command_receipts_v1 (
    command_id TEXT PRIMARY KEY,
    command_type TEXT NOT NULL,
    request_fingerprint TEXT NOT NULL,
    job_id TEXT NOT NULL UNIQUE REFERENCES workspace_jobs_v1(job_id),
    result_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS workspace_worker_checkpoints_v1 (
    worker_name TEXT PRIMARY KEY,
    checkpoint_json TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""

WORKSPACE_TABLES = (
    "workspace_jobs_v1",
    "workspace_outbox_v1",
    "workspace_command_receipts_v1",
    "workspace_worker_checkpoints_v1",
)
WORKSPACE_INDEXES = ("idx_workspace_jobs_state_v1", "idx_workspace_outbox_state_v1")
_OP_CAPABILITY = object()


def _connect(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(str(path), timeout=30.0)
    connection.execute("PRAGMA busy_timeout=30000")
    connection.row_factory = sqlite3.Row
    return connection


def _table_exists(connection: sqlite3.Connection, name: str) -> bool:
    return migration._table_exists(connection, name)


def _pending(connection: sqlite3.Connection) -> bool:
    if not all(_table_exists(connection, name) for name in WORKSPACE_TABLES):
        return True
    if not _table_exists(connection, "schema_migrations"):
        return True
    row = connection.execute(
        "SELECT name FROM schema_migrations WHERE version=?", (migration.WORKSPACE_SCHEMA_MIGRATION_VERSION,)
    ).fetchone()
    return row is None or str(row[0]) != migration.WORKSPACE_SCHEMA_MIGRATION_NAME


def status(*, db_path: str | Path) -> dict[str, object]:
    database = Path(db_path)
    if not database.is_file():
        return {"pending": True, "tables": []}
    with closing(_connect(database)) as connection:
        return {
            "pending": _pending(connection),
            "tables": [name for name in WORKSPACE_TABLES if _table_exists(connection, name)],
        }


def migrate(
    *,
    db_path: str | Path,
    backup_dir: str | Path,
    before_commit: Callable[[sqlite3.Connection, migration.MigrationRun], None] | None = None,
    backup_when_pending: bool = True,
    operator_run_id: str | None = None,
    _operator_capability: object | None = None,
) -> migration.MigrationRun:
    if _operator_capability is not _OP_CAPABILITY:
        raise RuntimeError("workspace migration requires MigrationOperator")
    database = Path(db_path)
    if not database.is_file():
        raise FileNotFoundError(f"SQLite database not found: {database}")
    with closing(_connect(database)) as connection:
        if not _pending(connection):
            return migration.MigrationRun((), None)
        backup = (
            migration._create_backup(
                database, Path(backup_dir), migration.WORKSPACE_SCHEMA_MIGRATION_NAME,
                operator_run_id=operator_run_id,
            )
            if backup_when_pending
            else None
        )
        connection.execute("BEGIN IMMEDIATE")
        try:
            connection.execute(migration.MIGRATIONS_TABLE)
            connection.executescript(WORKSPACE_SCHEMA_SQL)
            connection.execute(
                "INSERT INTO schema_migrations(version, name) VALUES (?, ?)",
                (migration.WORKSPACE_SCHEMA_MIGRATION_VERSION, migration.WORKSPACE_SCHEMA_MIGRATION_NAME),
            )
            run = migration.MigrationRun((migration.WORKSPACE_SCHEMA_MIGRATION_NAME,), backup)
            if before_commit is not None:
                before_commit(connection, run)
            connection.commit()
            return run
        except Exception:
            connection.rollback()
            raise
