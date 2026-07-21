"""Operator-owned SQLite schema for durable Sleep Loop execution leases."""

from __future__ import annotations

import sqlite3
from collections.abc import Callable, Iterator
from contextlib import closing
from pathlib import Path

from shared import migration

SLEEP_LOOP_MIGRATION_VERSION = migration.SLEEP_LOOP_MIGRATION_VERSION
SLEEP_LOOP_MIGRATION_NAME = migration.SLEEP_LOOP_MIGRATION_NAME
SLEEP_LOOP_TABLES = (
    "sleep_loop_runs",
    "sleep_loop_tasks",
    "sleep_loop_attempts",
    "sleep_loop_events",
)
SLEEP_LOOP_INDEXES = (
    "idx_sleep_loop_tasks_run_status",
    "idx_sleep_loop_tasks_parent",
    "idx_sleep_loop_tasks_idempotency",
    "idx_sleep_loop_tasks_lease_expiry",
    "idx_sleep_loop_attempts_run_status",
    "idx_sleep_loop_events_run_created",
)
_OPERATOR_CAPABILITY = object()

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS sleep_loop_runs (
    id TEXT PRIMARY KEY,
    status TEXT NOT NULL DEFAULT 'idle',
    goal TEXT NOT NULL DEFAULT '',
    cycle_no INTEGER NOT NULL DEFAULT 0,
    failure_streak INTEGER NOT NULL DEFAULT 0,
    next_cycle_at TEXT,
    started_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    stopped_at TEXT,
    stop_reason TEXT NOT NULL DEFAULT '',
    config_json TEXT NOT NULL DEFAULT '{}',
    seed_tasks_json TEXT NOT NULL DEFAULT '[]'
);
CREATE TABLE IF NOT EXISTS sleep_loop_tasks (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    parent_id TEXT NOT NULL DEFAULT '',
    cycle_no INTEGER NOT NULL DEFAULT 0,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    priority INTEGER NOT NULL DEFAULT 100,
    executor TEXT NOT NULL DEFAULT 'kb_search',
    payload_json TEXT NOT NULL DEFAULT '{}',
    dependencies_json TEXT NOT NULL DEFAULT '[]',
    retries INTEGER NOT NULL DEFAULT 0,
    max_retries INTEGER NOT NULL DEFAULT 3,
    derived_count INTEGER NOT NULL DEFAULT 0,
    risk_level TEXT NOT NULL DEFAULT 'low',
    result_json TEXT NOT NULL DEFAULT '{}',
    error TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    started_at TEXT,
    finished_at TEXT,
    idempotency_key TEXT NOT NULL DEFAULT '',
    request_fingerprint TEXT NOT NULL DEFAULT '',
    attempt_no INTEGER NOT NULL DEFAULT 0 CHECK(attempt_no >= 0),
    lease_owner TEXT NOT NULL DEFAULT '',
    lease_token TEXT NOT NULL DEFAULT '',
    lease_expires_at TEXT,
    heartbeat_at TEXT,
    next_attempt_at TEXT,
    terminal_trace_id TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_sleep_loop_tasks_run_status
ON sleep_loop_tasks(run_id, status, priority, created_at);
CREATE INDEX IF NOT EXISTS idx_sleep_loop_tasks_parent
ON sleep_loop_tasks(parent_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_sleep_loop_tasks_idempotency
ON sleep_loop_tasks(run_id, idempotency_key) WHERE idempotency_key <> '';
CREATE INDEX IF NOT EXISTS idx_sleep_loop_tasks_lease_expiry
ON sleep_loop_tasks(run_id, status, lease_expires_at);
CREATE TABLE IF NOT EXISTS sleep_loop_attempts (
    id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    run_id TEXT NOT NULL,
    attempt_no INTEGER NOT NULL CHECK(attempt_no > 0),
    lease_owner TEXT NOT NULL,
    lease_token TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'running',
    trace_id TEXT NOT NULL DEFAULT '',
    result_json TEXT NOT NULL DEFAULT '{}',
    error TEXT NOT NULL DEFAULT '',
    started_at TEXT NOT NULL,
    heartbeat_at TEXT,
    finished_at TEXT,
    UNIQUE(task_id, attempt_no)
);
CREATE INDEX IF NOT EXISTS idx_sleep_loop_attempts_run_status
ON sleep_loop_attempts(run_id, status, started_at);
CREATE TABLE IF NOT EXISTS sleep_loop_events (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL DEFAULT '',
    task_id TEXT NOT NULL DEFAULT '',
    level TEXT NOT NULL DEFAULT 'info',
    event_type TEXT NOT NULL,
    message TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_sleep_loop_events_run_created
ON sleep_loop_events(run_id, created_at DESC);
"""

LEGACY_SCHEMA_SQL = """
CREATE TABLE sleep_loop_runs (
    id TEXT PRIMARY KEY, status TEXT NOT NULL DEFAULT 'idle', goal TEXT NOT NULL DEFAULT '',
    cycle_no INTEGER NOT NULL DEFAULT 0, failure_streak INTEGER NOT NULL DEFAULT 0,
    next_cycle_at TEXT, started_at TEXT NOT NULL, updated_at TEXT NOT NULL, stopped_at TEXT,
    stop_reason TEXT NOT NULL DEFAULT '', config_json TEXT NOT NULL DEFAULT '{}',
    seed_tasks_json TEXT NOT NULL DEFAULT '[]'
);
CREATE TABLE sleep_loop_tasks (
    id TEXT PRIMARY KEY, run_id TEXT NOT NULL, parent_id TEXT NOT NULL DEFAULT '',
    cycle_no INTEGER NOT NULL DEFAULT 0, title TEXT NOT NULL, content TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending', priority INTEGER NOT NULL DEFAULT 100,
    executor TEXT NOT NULL DEFAULT 'kb_search', payload_json TEXT NOT NULL DEFAULT '{}',
    dependencies_json TEXT NOT NULL DEFAULT '[]', retries INTEGER NOT NULL DEFAULT 0,
    max_retries INTEGER NOT NULL DEFAULT 3, derived_count INTEGER NOT NULL DEFAULT 0,
    risk_level TEXT NOT NULL DEFAULT 'low', result_json TEXT NOT NULL DEFAULT '{}',
    error TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL, started_at TEXT, finished_at TEXT
);
CREATE INDEX idx_sleep_loop_tasks_run_status
ON sleep_loop_tasks(run_id, status, priority, created_at);
CREATE INDEX idx_sleep_loop_tasks_parent ON sleep_loop_tasks(parent_id);
CREATE TABLE sleep_loop_events (
    id TEXT PRIMARY KEY, run_id TEXT NOT NULL DEFAULT '', task_id TEXT NOT NULL DEFAULT '',
    level TEXT NOT NULL DEFAULT 'info', event_type TEXT NOT NULL, message TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}', created_at TEXT NOT NULL
);
CREATE INDEX idx_sleep_loop_events_run_created
ON sleep_loop_events(run_id, created_at DESC);
"""

_LEGACY_TASK_COLUMNS = (
    "id",
    "run_id",
    "parent_id",
    "cycle_no",
    "title",
    "content",
    "status",
    "priority",
    "executor",
    "payload_json",
    "dependencies_json",
    "retries",
    "max_retries",
    "derived_count",
    "risk_level",
    "result_json",
    "error",
    "created_at",
    "started_at",
    "finished_at",
)


def _connect(path: Path, *, readonly: bool = False) -> sqlite3.Connection:
    if readonly:
        sidecars = [Path(f"{path}{suffix}") for suffix in ("-wal", "-shm")]
        if any(item.exists() for item in sidecars):
            raise RuntimeError("sleep loop status requires a checkpointed database")
        connection = sqlite3.connect(
            f"{path.resolve().as_uri()}?mode=ro&immutable=1", uri=True, timeout=30.0
        )
        connection.execute("PRAGMA query_only=ON")
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(str(path), timeout=30.0)
    connection.execute("PRAGMA busy_timeout=30000")
    connection.row_factory = sqlite3.Row
    return connection


def _statements(script: str) -> Iterator[str]:
    buffer = ""
    for line in script.splitlines(keepends=True):
        buffer += line
        if sqlite3.complete_statement(buffer):
            statement = buffer.strip()
            buffer = ""
            if statement:
                yield statement
    if buffer.strip():
        raise RuntimeError("sleep loop schema contains an incomplete SQL statement")


def _apply_schema(connection: sqlite3.Connection) -> None:
    for statement in _statements(SCHEMA_SQL):
        connection.execute(statement)


def _normalize_sql(sql: str) -> str:
    return " ".join(sql.replace("IF NOT EXISTS", "").split()).casefold()


def _expected_objects() -> dict[str, tuple[str, str, str]]:
    names = SLEEP_LOOP_TABLES + SLEEP_LOOP_INDEXES
    with closing(sqlite3.connect(":memory:")) as connection:
        _apply_schema(connection)
        placeholders = ", ".join("?" for _ in names)
        rows = connection.execute(
            f"SELECT type, name, tbl_name, sql FROM sqlite_master WHERE name IN ({placeholders})",
            names,
        ).fetchall()
    return {
        str(row[1]): (str(row[0]), str(row[2]), _normalize_sql(str(row[3] or "")))
        for row in rows
    }


def _legacy_expected_objects() -> dict[str, tuple[str, str, str]]:
    with closing(sqlite3.connect(":memory:")) as connection:
        connection.row_factory = sqlite3.Row
        for statement in _statements(LEGACY_SCHEMA_SQL):
            connection.execute(statement)
        placeholders = ", ".join("?" for _ in SLEEP_LOOP_TABLES)
        rows = connection.execute(
            "SELECT type, name, tbl_name, sql FROM sqlite_master WHERE sql IS NOT NULL AND "
            f"(name IN ({placeholders}) OR tbl_name IN ({placeholders}))",
            (*SLEEP_LOOP_TABLES, *SLEEP_LOOP_TABLES),
        ).fetchall()
    return {
        str(row["name"]): (
            str(row["type"]),
            str(row["tbl_name"]),
            _normalize_sql(str(row["sql"])),
        )
        for row in rows
    }


def _actual_objects(
    connection: sqlite3.Connection, expected: dict[str, tuple[str, str, str]]
) -> dict[str, tuple[str, str, str]]:
    names = tuple(expected)
    name_placeholders = ", ".join("?" for _ in names)
    table_placeholders = ", ".join("?" for _ in SLEEP_LOOP_TABLES)
    rows = connection.execute(
        "SELECT type, name, tbl_name, sql FROM sqlite_master WHERE sql IS NOT NULL AND "
        f"(name IN ({name_placeholders}) OR tbl_name IN ({table_placeholders}))",
        (*names, *SLEEP_LOOP_TABLES),
    ).fetchall()
    return {
        str(row["name"]): (
            str(row["type"]),
            str(row["tbl_name"]),
            _normalize_sql(str(row["sql"])),
        )
        for row in rows
    }


def _recorded(connection: sqlite3.Connection) -> bool:
    if not migration._table_exists(connection, "schema_migrations"):
        return False
    rows = connection.execute(
        "SELECT version, name FROM schema_migrations WHERE version=? OR name=?",
        (SLEEP_LOOP_MIGRATION_VERSION, SLEEP_LOOP_MIGRATION_NAME),
    ).fetchall()
    if not rows:
        return False
    if len(rows) != 1 or tuple(rows[0]) != (
        SLEEP_LOOP_MIGRATION_VERSION,
        SLEEP_LOOP_MIGRATION_NAME,
    ):
        raise RuntimeError("sleep loop migration version/name collision")
    return True


def _validate_schema(connection: sqlite3.Connection) -> None:
    expected = _expected_objects()
    actual = _actual_objects(connection, expected)
    if actual != expected:
        mismatches = sorted(
            {name for name, definition in expected.items() if actual.get(name) != definition}
            | (set(actual) - set(expected))
        )
        raise RuntimeError("sleep loop recorded schema drift: " + ", ".join(mismatches))


def _pending(connection: sqlite3.Connection) -> tuple[str, ...]:
    if _recorded(connection):
        _validate_schema(connection)
        return ()
    expected = _expected_objects()
    actual = _actual_objects(connection, expected)
    if actual and actual not in (expected, _legacy_expected_objects()):
        raise RuntimeError("unrecorded sleep loop schema drift")
    return (SLEEP_LOOP_MIGRATION_NAME,)


def _upgrade_schema(connection: sqlite3.Connection) -> None:
    expected = _expected_objects()
    actual = _actual_objects(connection, expected)
    if not actual:
        _apply_schema(connection)
        return
    if actual == expected:
        return
    if actual != _legacy_expected_objects():
        raise RuntimeError("unrecorded sleep loop schema drift")
    connection.execute("DROP INDEX idx_sleep_loop_tasks_run_status")
    connection.execute("DROP INDEX idx_sleep_loop_tasks_parent")
    connection.execute("ALTER TABLE sleep_loop_tasks RENAME TO sleep_loop_tasks_legacy")
    _apply_schema(connection)
    columns = ", ".join(_LEGACY_TASK_COLUMNS)
    connection.execute(
        f"INSERT INTO sleep_loop_tasks({columns}) "
        f"SELECT {columns} FROM sleep_loop_tasks_legacy"
    )
    connection.execute(
        "UPDATE sleep_loop_tasks SET status='pending', retries=retries+1, "
        "error='legacy_running_requeued', started_at=NULL, next_attempt_at=CURRENT_TIMESTAMP "
        "WHERE status='running' AND executor IN ('file_read', 'kb_search', 'mk_search')"
    )
    connection.execute(
        "UPDATE sleep_loop_tasks SET status='blocked', retries=retries+1, "
        "error='unknown_outcome_requires_reconciliation', finished_at=CURRENT_TIMESTAMP "
        "WHERE status='running'"
    )
    connection.execute("DROP TABLE sleep_loop_tasks_legacy")


def migrate(
    *,
    db_path: str | Path,
    backup_dir: str | Path,
    before_commit: Callable[[sqlite3.Connection, migration.MigrationRun], None] | None = None,
    backup_when_pending: bool = False,
    operator_run_id: str | None = None,
    _operator_capability: object | None = None,
) -> migration.MigrationRun:
    if _operator_capability is not _OPERATOR_CAPABILITY:
        raise RuntimeError("sleep loop migration must be driven by MigrationOperator")
    database = Path(db_path)
    backups = Path(backup_dir)
    database_existed = database.is_file()
    if database_existed:
        migration._validate_database(database)
    backup_path: Path | None = None
    with closing(_connect(database)) as connection:
        try:
            connection.execute("BEGIN IMMEDIATE")
            pending = _pending(connection)
            if not pending:
                connection.commit()
                return migration.MigrationRun(applied=(), backup_path=None)
            if database_existed and backup_when_pending:
                backup_path = migration._create_backup(
                    database,
                    backups,
                    SLEEP_LOOP_MIGRATION_NAME,
                    operator_run_id=operator_run_id,
                )
            connection.execute(migration.MIGRATIONS_TABLE)
            _upgrade_schema(connection)
            connection.execute(
                "INSERT INTO schema_migrations(version, name) VALUES (?, ?)",
                (SLEEP_LOOP_MIGRATION_VERSION, SLEEP_LOOP_MIGRATION_NAME),
            )
            _validate_schema(connection)
            run = migration.MigrationRun(applied=pending, backup_path=backup_path)
            if before_commit is not None:
                before_commit(connection, run)
            connection.commit()
        except Exception:
            connection.rollback()
            raise
    migration._validate_database(database)
    return run


def status(*, db_path: str | Path) -> dict[str, object]:
    database = Path(db_path)
    if not database.is_file():
        pending = (SLEEP_LOOP_MIGRATION_NAME,)
    else:
        with closing(_connect(database, readonly=True)) as connection:
            pending = _pending(connection)
    applied = not pending
    label = f"{SLEEP_LOOP_MIGRATION_VERSION:03d}_{SLEEP_LOOP_MIGRATION_NAME}"
    return {
        "total": 1,
        "applied": 1 if applied else 0,
        "pending": [] if applied else [label],
        "applied_list": [label] if applied else [],
    }


def require_applied(*, db_path: str | Path) -> None:
    database = Path(db_path)
    if not database.is_file():
        raise RuntimeError("sleep loop schema migration is pending")
    with closing(_connect(database)) as connection:
        connection.execute("PRAGMA query_only=ON")
        if _pending(connection):
            raise RuntimeError("sleep loop schema migration is pending")
