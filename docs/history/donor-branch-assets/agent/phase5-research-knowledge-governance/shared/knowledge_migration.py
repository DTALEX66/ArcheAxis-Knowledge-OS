"""Operator-only SQLite schema for governed Phase 5 knowledge candidates."""
from __future__ import annotations

import sqlite3
from collections.abc import Callable
from contextlib import closing
from pathlib import Path

from shared import migration

KNOWLEDGE_SCHEMA_MIGRATION_VERSION = 5
KNOWLEDGE_SCHEMA_MIGRATION_NAME = "phase5_knowledge_governance_v1"
KNOWLEDGE_TABLES = (
    "knowledge_review_decisions_v1",
    "knowledge_materializations_v1",
    "knowledge_units_v1",
    "knowledge_relations_v1",
)
KNOWLEDGE_INDEXES = (
    "idx_knowledge_decisions_package_v1",
    "idx_knowledge_materializations_package_v1",
    "idx_knowledge_units_materialization_v1",
    "idx_knowledge_relations_materialization_v1",
)
KNOWLEDGE_TRIGGERS = (
    "trg_knowledge_review_decisions_no_update_v1",
    "trg_knowledge_review_decisions_no_delete_v1",
)
_OPERATOR_CAPABILITY = object()

KNOWLEDGE_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS knowledge_review_decisions_v1 (
    decision_id TEXT PRIMARY KEY,
    package_id TEXT NOT NULL,
    package_fingerprint TEXT NOT NULL,
    decision_type TEXT NOT NULL CHECK(decision_type IN ('approved', 'rejected', 'deprecated')),
    decision_request_id TEXT NOT NULL,
    reviewer_principal TEXT NOT NULL,
    actor_kind TEXT NOT NULL CHECK(actor_kind = 'human'),
    reason TEXT NOT NULL,
    reviewed_at TEXT NOT NULL,
    supersedes_decision_id TEXT,
    UNIQUE(package_id, decision_request_id)
);
CREATE INDEX IF NOT EXISTS idx_knowledge_decisions_package_v1
ON knowledge_review_decisions_v1(package_id);

CREATE TABLE IF NOT EXISTS knowledge_materializations_v1 (
    materialization_id TEXT PRIMARY KEY,
    package_id TEXT NOT NULL,
    approval_decision_id TEXT NOT NULL UNIQUE,
    transformer_version TEXT NOT NULL,
    lifecycle_status TEXT NOT NULL CHECK(lifecycle_status IN ('candidate', 'deprecated')),
    package_snapshot_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    deprecated_by_decision_id TEXT,
    UNIQUE(package_id, approval_decision_id, transformer_version),
    FOREIGN KEY(approval_decision_id) REFERENCES knowledge_review_decisions_v1(decision_id)
);
CREATE INDEX IF NOT EXISTS idx_knowledge_materializations_package_v1
ON knowledge_materializations_v1(package_id);

CREATE TABLE IF NOT EXISTS knowledge_units_v1 (
    unit_id TEXT PRIMARY KEY,
    materialization_id TEXT NOT NULL,
    package_id TEXT NOT NULL,
    approval_decision_id TEXT NOT NULL,
    claim_id TEXT NOT NULL DEFAULT '',
    unit_type TEXT NOT NULL,
    properties_json TEXT NOT NULL,
    graph_name TEXT NOT NULL,
    lifecycle_status TEXT NOT NULL CHECK(lifecycle_status IN ('candidate', 'deprecated')),
    requires_human_review INTEGER NOT NULL CHECK(requires_human_review = 1),
    source_record_ids_json TEXT NOT NULL,
    evidence_ids_json TEXT NOT NULL,
    finding_ids_json TEXT NOT NULL,
    source_group_ids_json TEXT NOT NULL,
    package_fingerprint TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(materialization_id) REFERENCES knowledge_materializations_v1(materialization_id)
);
CREATE INDEX IF NOT EXISTS idx_knowledge_units_materialization_v1
ON knowledge_units_v1(materialization_id);

CREATE TABLE IF NOT EXISTS knowledge_relations_v1 (
    relation_id TEXT PRIMARY KEY,
    materialization_id TEXT NOT NULL,
    package_id TEXT NOT NULL,
    approval_decision_id TEXT NOT NULL,
    source_unit_id TEXT NOT NULL,
    target_unit_id TEXT NOT NULL,
    relation_type TEXT NOT NULL,
    weight REAL NOT NULL,
    graph_name TEXT NOT NULL,
    lifecycle_status TEXT NOT NULL CHECK(lifecycle_status IN ('candidate', 'deprecated')),
    requires_human_review INTEGER NOT NULL CHECK(requires_human_review = 1),
    claim_id TEXT NOT NULL DEFAULT '',
    source_record_ids_json TEXT NOT NULL,
    evidence_ids_json TEXT NOT NULL,
    finding_ids_json TEXT NOT NULL,
    source_group_ids_json TEXT NOT NULL,
    package_fingerprint TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(materialization_id) REFERENCES knowledge_materializations_v1(materialization_id)
);
CREATE INDEX IF NOT EXISTS idx_knowledge_relations_materialization_v1
ON knowledge_relations_v1(materialization_id);
"""

KNOWLEDGE_TRIGGER_SQL = (
    "CREATE TRIGGER IF NOT EXISTS trg_knowledge_review_decisions_no_update_v1 "
    "BEFORE UPDATE ON knowledge_review_decisions_v1 "
    "BEGIN SELECT RAISE(ABORT, 'knowledge review decisions are immutable'); END",
    "CREATE TRIGGER IF NOT EXISTS trg_knowledge_review_decisions_no_delete_v1 "
    "BEFORE DELETE ON knowledge_review_decisions_v1 "
    "BEGIN SELECT RAISE(ABORT, 'knowledge review decisions are immutable'); END",
)


def _schema_statements() -> tuple[str, ...]:
    return tuple(statement for statement in KNOWLEDGE_SCHEMA_SQL.split(";") if statement.strip()) + KNOWLEDGE_TRIGGER_SQL


def _connect(path: Path, *, readonly: bool = False) -> sqlite3.Connection:
    if readonly:
        uri = f"{path.resolve().as_uri()}?mode=ro&immutable=1"
        connection = sqlite3.connect(uri, uri=True, timeout=30.0)
        connection.execute("PRAGMA query_only=ON")
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(str(path), timeout=30.0)
    connection.execute("PRAGMA busy_timeout=30000")
    connection.row_factory = sqlite3.Row
    return connection


def _normalize(sql: str) -> str:
    return " ".join(sql.replace("IF NOT EXISTS", "").split()).casefold()


def _expected_schema() -> dict[str, tuple[str, str, str]]:
    names = KNOWLEDGE_TABLES + KNOWLEDGE_INDEXES + KNOWLEDGE_TRIGGERS
    with closing(sqlite3.connect(":memory:")) as connection:
        for statement in _schema_statements():
            connection.execute(statement)
        placeholders = ", ".join("?" for _ in names)
        rows = connection.execute(
            f"SELECT type, name, tbl_name, sql FROM sqlite_master WHERE name IN ({placeholders})", names
        ).fetchall()
    return {str(row[1]): (str(row[0]), str(row[2]), _normalize(str(row[3] or ""))) for row in rows}


def _actual_schema(connection: sqlite3.Connection, expected: dict[str, tuple[str, str, str]]) -> dict[str, tuple[str, str, str]]:
    names = tuple(expected)
    tables = KNOWLEDGE_TABLES
    rows = connection.execute(
        "SELECT type, name, tbl_name, sql FROM sqlite_master WHERE sql IS NOT NULL "
        f"AND (name IN ({', '.join('?' for _ in names)}) OR tbl_name IN ({', '.join('?' for _ in tables)}))",
        (*names, *tables),
    ).fetchall()
    return {str(row['name']): (str(row['type']), str(row['tbl_name']), _normalize(str(row['sql'] or ''))) for row in rows}


def _recorded(connection: sqlite3.Connection) -> bool:
    if not migration._table_exists(connection, "schema_migrations"):
        return False
    rows = connection.execute(
        "SELECT version, name FROM schema_migrations WHERE version=? OR name=?",
        (KNOWLEDGE_SCHEMA_MIGRATION_VERSION, KNOWLEDGE_SCHEMA_MIGRATION_NAME),
    ).fetchall()
    if not rows:
        return False
    if len(rows) != 1 or int(rows[0]["version"]) != KNOWLEDGE_SCHEMA_MIGRATION_VERSION or str(rows[0]["name"]) != KNOWLEDGE_SCHEMA_MIGRATION_NAME:
        raise RuntimeError("knowledge migration version/name collision")
    return True


def _pending(connection: sqlite3.Connection) -> tuple[str, ...]:
    expected = _expected_schema()
    actual = _actual_schema(connection, expected)
    if _recorded(connection):
        if actual != expected:
            raise RuntimeError("recorded knowledge migration schema mismatch")
        return ()
    if actual:
        raise RuntimeError("unrecorded knowledge migration schema mismatch")
    return (KNOWLEDGE_SCHEMA_MIGRATION_NAME,)


def _apply_schema(connection: sqlite3.Connection) -> None:
    for statement in _schema_statements():
        connection.execute(statement)


def migrate(*, db_path: str | Path, backup_dir: str | Path, before_commit: Callable[[sqlite3.Connection, migration.MigrationRun], None] | None = None, backup_when_pending: bool = False, operator_run_id: str | None = None, _operator_capability: object | None = None) -> migration.MigrationRun:
    if _operator_capability is not _OPERATOR_CAPABILITY:
        raise RuntimeError("knowledge schema migration must be driven by MigrationOperator")
    database = Path(db_path)
    existed = database.is_file()
    if existed:
        migration._validate_database(database)
    with closing(_connect(database)) as connection:
        try:
            connection.execute("BEGIN IMMEDIATE")
            pending = _pending(connection)
            if not pending:
                connection.commit()
                return migration.MigrationRun(applied=(), backup_path=None)
            backup = migration._create_backup(database, Path(backup_dir), KNOWLEDGE_SCHEMA_MIGRATION_NAME, operator_run_id=operator_run_id) if existed and backup_when_pending else None
            connection.execute(migration.MIGRATIONS_TABLE)
            _apply_schema(connection)
            if _actual_schema(connection, _expected_schema()) != _expected_schema():
                raise RuntimeError("knowledge schema failed validation before recording")
            connection.execute(
                "INSERT INTO schema_migrations(version, name) VALUES (?, ?)",
                (KNOWLEDGE_SCHEMA_MIGRATION_VERSION, KNOWLEDGE_SCHEMA_MIGRATION_NAME),
            )
            run = migration.MigrationRun(applied=pending, backup_path=backup)
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
        return {"total": 1, "applied": 0, "pending": [f"{KNOWLEDGE_SCHEMA_MIGRATION_VERSION:03d}_{KNOWLEDGE_SCHEMA_MIGRATION_NAME}"], "applied_list": []}
    with closing(_connect(database, readonly=True)) as connection:
        if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise RuntimeError(f"SQLite integrity check failed for {database}")
        pending = _pending(connection)
    return {"total": 1, "applied": 0 if pending else 1, "pending": [f"{KNOWLEDGE_SCHEMA_MIGRATION_VERSION:03d}_{name}" for name in pending], "applied_list": [] if pending else [f"{KNOWLEDGE_SCHEMA_MIGRATION_VERSION:03d}_{KNOWLEDGE_SCHEMA_MIGRATION_NAME}"]}


def require_applied(*, db_path: str | Path) -> None:
    state = status(db_path=db_path)
    if state["pending"]:
        raise RuntimeError("phase5 knowledge governance schema migration is pending")
