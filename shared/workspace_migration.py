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


def _connect_readonly(path: Path) -> sqlite3.Connection:
    sidecars = [Path(f"{path}{suffix}") for suffix in ("-wal", "-shm")]
    present = [sidecar.name for sidecar in sidecars if sidecar.exists()]
    if present:
        raise RuntimeError(
            "read-only workspace access requires a checkpointed database without "
            f"SQLite sidecars: {', '.join(present)}"
        )
    uri = f"{path.resolve().as_uri()}?mode=ro&immutable=1"
    connection = sqlite3.connect(uri, uri=True, timeout=30.0)
    connection.execute("PRAGMA busy_timeout=30000")
    connection.execute("PRAGMA query_only=ON")
    connection.row_factory = sqlite3.Row
    return connection


def _table_exists(connection: sqlite3.Connection, name: str) -> bool:
    return migration._table_exists(connection, name)


def _normalize_schema_sql(sql: str) -> str:
    return " ".join(sql.replace("IF NOT EXISTS", "").split()).casefold()


def _expected_schema_objects() -> dict[str, tuple[str, str, str]]:
    names = WORKSPACE_TABLES + WORKSPACE_INDEXES
    with closing(sqlite3.connect(":memory:")) as connection:
        _apply_schema(connection)
        placeholders = ", ".join("?" for _ in names)
        rows = connection.execute(
            f"SELECT type, name, tbl_name, sql FROM sqlite_master WHERE name IN ({placeholders})",
            names,
        ).fetchall()
    return {
        str(row[1]): (str(row[0]), str(row[2]), _normalize_schema_sql(str(row[3] or "")))
        for row in rows
    }


def _actual_owned_schema_objects(
    connection: sqlite3.Connection,
    expected: dict[str, tuple[str, str, str]],
) -> dict[str, tuple[str, str, str]]:
    expected_names = tuple(expected)
    name_placeholders = ", ".join("?" for _ in expected_names)
    table_placeholders = ", ".join("?" for _ in WORKSPACE_TABLES)
    rows = connection.execute(
        "SELECT type, name, tbl_name, sql FROM sqlite_master "
        "WHERE sql IS NOT NULL AND "
        f"(name IN ({name_placeholders}) OR tbl_name IN ({table_placeholders}))",
        (*expected_names, *WORKSPACE_TABLES),
    ).fetchall()
    return {
        str(row["name"]): (
            str(row["type"]),
            str(row["tbl_name"]),
            _normalize_schema_sql(str(row["sql"])),
        )
        for row in rows
    }


def _workspace_schema_recorded(connection: sqlite3.Connection) -> bool:
    if not _table_exists(connection, "schema_migrations"):
        return False
    rows = connection.execute(
        "SELECT version, name FROM schema_migrations WHERE version=? OR name=?",
        (
            migration.WORKSPACE_SCHEMA_MIGRATION_VERSION,
            migration.WORKSPACE_SCHEMA_MIGRATION_NAME,
        ),
    ).fetchall()
    recorded = False
    for row in rows:
        version, name = int(row["version"]), str(row["name"])
        if (
            version == migration.WORKSPACE_SCHEMA_MIGRATION_VERSION
            and name == migration.WORKSPACE_SCHEMA_MIGRATION_NAME
        ):
            recorded = True
            continue
        raise RuntimeError("workspace migration version/name collision")
    return recorded


def _validate_recorded_schema(connection: sqlite3.Connection) -> None:
    expected = _expected_schema_objects()
    actual = _actual_owned_schema_objects(connection, expected)
    mismatches = sorted(
        {name for name, definition in expected.items() if actual.get(name) != definition}
        | (set(actual) - set(expected))
    )
    if mismatches:
        raise RuntimeError(
            "recorded workspace migration schema mismatch; objects: " + ", ".join(mismatches)
        )


def _validate_unrecorded_schema(connection: sqlite3.Connection) -> None:
    expected = _expected_schema_objects()
    actual = _actual_owned_schema_objects(connection, expected)
    mismatches = sorted(
        {name for name, definition in actual.items() if expected.get(name) != definition}
        | (set(actual) - set(expected))
    )
    if mismatches:
        raise RuntimeError(
            "unrecorded workspace migration schema mismatch; objects: " + ", ".join(mismatches)
        )


def _pending(connection: sqlite3.Connection) -> bool:
    recorded = _workspace_schema_recorded(connection)
    if recorded:
        _validate_recorded_schema(connection)
        return False
    _validate_unrecorded_schema(connection)
    return True


def _require_applied_connection(connection: sqlite3.Connection, path: Path) -> None:
    if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
        raise RuntimeError(f"SQLite integrity check failed for {path}")
    if _pending(connection):
        raise RuntimeError("workspace job/outbox schema migration is pending")


def _apply_schema(connection: sqlite3.Connection) -> None:
    for statement in WORKSPACE_SCHEMA_SQL.split(";"):
        sql = statement.strip()
        if sql:
            connection.execute(sql)


def status(*, db_path: str | Path) -> dict[str, object]:
    database = Path(db_path)
    if not database.is_file():
        return {"pending": True, "tables": []}
    with closing(_connect_readonly(database)) as connection:
        pending = _pending(connection)
        return {
            "pending": pending,
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
        connection.execute("BEGIN IMMEDIATE")
        try:
            backup = (
                migration._create_backup(
                    database,
                    Path(backup_dir),
                    migration.WORKSPACE_SCHEMA_MIGRATION_NAME,
                    operator_run_id=operator_run_id,
                )
                if backup_when_pending
                else None
            )
            connection.execute(migration.MIGRATIONS_TABLE)
            _apply_schema(connection)
            connection.execute(
                "INSERT INTO schema_migrations(version, name) VALUES (?, ?)",
                (migration.WORKSPACE_SCHEMA_MIGRATION_VERSION, migration.WORKSPACE_SCHEMA_MIGRATION_NAME),
            )
            _validate_recorded_schema(connection)
            run = migration.MigrationRun((migration.WORKSPACE_SCHEMA_MIGRATION_NAME,), backup)
            if before_commit is not None:
                before_commit(connection, run)
            connection.commit()
            return run
        except Exception:
            connection.rollback()
            raise
