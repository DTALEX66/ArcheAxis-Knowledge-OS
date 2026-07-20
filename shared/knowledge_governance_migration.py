"""Owner-bound SQLite schema for Research-to-Knowledge candidate governance."""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from contextlib import closing
from pathlib import Path

from shared import migration

KNOWLEDGE_GOVERNANCE_MIGRATION_VERSION = 5
KNOWLEDGE_GOVERNANCE_MIGRATION_NAME = "phase5_knowledge_candidate_governance_v1"
KNOWLEDGE_GOVERNANCE_TABLES = (
    "knowledge_candidate_promotions_v1",
    "knowledge_candidate_units_v1",
    "knowledge_candidate_relations_v1",
)
_OPERATOR_CAPABILITY = object()

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS knowledge_candidate_promotions_v1 (
    id TEXT PRIMARY KEY,
    package_id TEXT NOT NULL UNIQUE,
    approval_id TEXT NOT NULL UNIQUE,
    reviewer_id TEXT NOT NULL,
    decision TEXT NOT NULL CHECK(decision IN ('approved', 'rejected', 'deprecated')),
    rationale TEXT NOT NULL,
    reviewed_at TEXT NOT NULL,
    candidate_fingerprint TEXT NOT NULL,
    lifecycle_status TEXT NOT NULL CHECK(lifecycle_status IN ('candidate', 'rejected', 'deprecated')),
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS knowledge_candidate_units_v1 (
    id TEXT PRIMARY KEY,
    promotion_id TEXT NOT NULL,
    package_id TEXT NOT NULL,
    unit_type TEXT NOT NULL,
    properties_json TEXT NOT NULL,
    graph_name TEXT NOT NULL,
    lifecycle_status TEXT NOT NULL CHECK(lifecycle_status IN ('candidate', 'deprecated')),
    provenance_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(promotion_id) REFERENCES knowledge_candidate_promotions_v1(id)
);
CREATE INDEX IF NOT EXISTS idx_knowledge_candidate_units_promotion_v1
ON knowledge_candidate_units_v1(promotion_id);
CREATE TABLE IF NOT EXISTS knowledge_candidate_relations_v1 (
    id TEXT PRIMARY KEY,
    promotion_id TEXT NOT NULL,
    source_unit_id TEXT NOT NULL,
    target_unit_id TEXT NOT NULL,
    relation_type TEXT NOT NULL,
    weight REAL NOT NULL,
    graph_name TEXT NOT NULL,
    lifecycle_status TEXT NOT NULL CHECK(lifecycle_status IN ('candidate', 'deprecated')),
    provenance_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(promotion_id) REFERENCES knowledge_candidate_promotions_v1(id)
);
CREATE INDEX IF NOT EXISTS idx_knowledge_candidate_relations_promotion_v1
ON knowledge_candidate_relations_v1(promotion_id);
"""


def _connect(path: Path, *, readonly: bool = False) -> sqlite3.Connection:
    if not readonly:
        path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(str(path), timeout=30.0)
    else:
        sidecars = [Path(f"{path}{suffix}") for suffix in ("-wal", "-shm")]
        if any(path.exists() for path in sidecars):
            raise RuntimeError("knowledge governance read requires checkpointed database")
        connection = sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro&immutable=1", uri=True, timeout=30.0)
        connection.execute("PRAGMA query_only=ON")
    connection.execute("PRAGMA busy_timeout=30000")
    connection.row_factory = sqlite3.Row
    return connection


def _recorded(connection: sqlite3.Connection) -> bool:
    if not migration._table_exists(connection, "schema_migrations"):
        return False
    rows = connection.execute(
        "SELECT version, name FROM schema_migrations WHERE version=? OR name=?",
        (KNOWLEDGE_GOVERNANCE_MIGRATION_VERSION, KNOWLEDGE_GOVERNANCE_MIGRATION_NAME),
    ).fetchall()
    for row in rows:
        if int(row["version"]) == KNOWLEDGE_GOVERNANCE_MIGRATION_VERSION and str(row["name"]) == KNOWLEDGE_GOVERNANCE_MIGRATION_NAME:
            return True
        raise RuntimeError("knowledge governance migration version/name collision")
    return False


def _pending(connection: sqlite3.Connection) -> tuple[str, ...]:
    recorded = _recorded(connection)
    existing = {name for name in KNOWLEDGE_GOVERNANCE_TABLES if migration._table_exists(connection, name)}
    if recorded:
        if existing != set(KNOWLEDGE_GOVERNANCE_TABLES):
            raise RuntimeError("knowledge governance schema drift")
        return ()
    if existing:
        raise RuntimeError("unrecorded knowledge governance schema mismatch")
    return (KNOWLEDGE_GOVERNANCE_MIGRATION_NAME,)


def _apply(connection: sqlite3.Connection) -> None:
    for statement in SCHEMA_SQL.split(";"):
        if statement.strip():
            connection.execute(statement)


def migrate(*, db_path: str | Path, backup_dir: str | Path, before_commit: Callable[[sqlite3.Connection, migration.MigrationRun], None] | None = None, backup_when_pending: bool = False, operator_run_id: str | None = None, _operator_capability: object | None = None) -> migration.MigrationRun:
    if _operator_capability is not _OPERATOR_CAPABILITY:
        raise RuntimeError("knowledge governance migration must be driven by MigrationOperator")
    database, backups = Path(db_path), Path(backup_dir)
    existed = database.is_file()
    if existed:
        migration._validate_database(database)
    backup_path: Path | None = None
    with closing(_connect(database)) as connection:
        try:
            connection.execute("BEGIN IMMEDIATE")
            pending = _pending(connection)
            if not pending:
                connection.commit()
                return migration.MigrationRun(applied=(), backup_path=None)
            if existed and backup_when_pending:
                backup_path = migration._create_backup(database, backups, KNOWLEDGE_GOVERNANCE_MIGRATION_NAME, operator_run_id=operator_run_id)
            connection.execute(migration.MIGRATIONS_TABLE)
            _apply(connection)
            connection.execute(
                "INSERT INTO schema_migrations(version, name) VALUES (?, ?)",
                (KNOWLEDGE_GOVERNANCE_MIGRATION_VERSION, KNOWLEDGE_GOVERNANCE_MIGRATION_NAME),
            )
            _pending(connection)
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
        return {"total": 1, "applied": 0, "pending": [f"005_{KNOWLEDGE_GOVERNANCE_MIGRATION_NAME}"], "applied_list": []}
    with closing(_connect(database, readonly=True)) as connection:
        if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise RuntimeError("knowledge governance database integrity check failed")
        pending = _pending(connection)
    return {"total": 1, "applied": 0 if pending else 1, "pending": [f"005_{item}" for item in pending], "applied_list": [] if pending else [f"005_{KNOWLEDGE_GOVERNANCE_MIGRATION_NAME}"]}


def require_applied(*, db_path: str | Path) -> None:
    state = status(db_path=db_path)
    if state["pending"]:
        raise RuntimeError("phase5 knowledge governance schema migration is pending")
