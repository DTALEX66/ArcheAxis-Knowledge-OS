"""Owner-bound SQLite schema for Research-to-Knowledge candidate governance."""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from contextlib import closing
from pathlib import Path

from shared import migration

KNOWLEDGE_GOVERNANCE_MIGRATION_VERSION = 5
KNOWLEDGE_GOVERNANCE_MIGRATION_NAME = "phase5_knowledge_candidate_governance_v1"
KNOWLEDGE_GOVERNANCE_EVENT_MIGRATION_VERSION = 6
KNOWLEDGE_GOVERNANCE_EVENT_MIGRATION_NAME = "phase5_knowledge_candidate_governance_events_v1"
KNOWLEDGE_VERSIONING_MIGRATION_VERSION = 7
KNOWLEDGE_VERSIONING_MIGRATION_NAME = "phase5_knowledge_candidate_versioning_v1"
KNOWLEDGE_LEARNING_ARTIFACT_MIGRATION_VERSION = 8
KNOWLEDGE_LEARNING_ARTIFACT_MIGRATION_NAME = "phase5_knowledge_candidate_learning_artifacts_v1"
LEARNING_APPROVAL_EVENT_MIGRATION_VERSION = 9
LEARNING_APPROVAL_EVENT_MIGRATION_NAME = "phase5_learning_approval_events_v1"
KNOWLEDGE_GOVERNANCE_MIGRATIONS = {
    KNOWLEDGE_GOVERNANCE_MIGRATION_VERSION: KNOWLEDGE_GOVERNANCE_MIGRATION_NAME,
    KNOWLEDGE_GOVERNANCE_EVENT_MIGRATION_VERSION: KNOWLEDGE_GOVERNANCE_EVENT_MIGRATION_NAME,
    KNOWLEDGE_VERSIONING_MIGRATION_VERSION: KNOWLEDGE_VERSIONING_MIGRATION_NAME,
    KNOWLEDGE_LEARNING_ARTIFACT_MIGRATION_VERSION: KNOWLEDGE_LEARNING_ARTIFACT_MIGRATION_NAME,
    LEARNING_APPROVAL_EVENT_MIGRATION_VERSION: LEARNING_APPROVAL_EVENT_MIGRATION_NAME,
}
KNOWLEDGE_GOVERNANCE_TABLES_V1 = (
    "knowledge_candidate_promotions_v1",
    "knowledge_candidate_units_v1",
    "knowledge_candidate_relations_v1",
)
KNOWLEDGE_GOVERNANCE_EVENT_TABLE = "knowledge_candidate_governance_events_v1"
KNOWLEDGE_GOVERNANCE_V1_OBJECTS = (
    *KNOWLEDGE_GOVERNANCE_TABLES_V1,
    "idx_knowledge_candidate_units_promotion_v1",
    "idx_knowledge_candidate_relations_promotion_v1",
)
KNOWLEDGE_GOVERNANCE_EVENT_OBJECTS = (
    KNOWLEDGE_GOVERNANCE_EVENT_TABLE,
    "idx_knowledge_candidate_events_package_v1",
)
KNOWLEDGE_VERSIONING_OBJECTS = (
    "knowledge_candidate_versions_v1",
    "idx_knowledge_candidate_versions_key_v1",
    "knowledge_candidate_conflict_reviews_v1",
)
LEARNING_ARTIFACT_OBJECTS = (
    "knowledge_candidate_learning_artifacts_v1",
    "idx_knowledge_candidate_learning_artifacts_source_v1",
)
LEARNING_APPROVAL_EVENT_OBJECTS = (
    "learning_approval_events_v1",
    "idx_learning_approval_events_artifact_v1",
)
KNOWLEDGE_GOVERNANCE_TABLES = (
    *KNOWLEDGE_GOVERNANCE_TABLES_V1,
    KNOWLEDGE_GOVERNANCE_EVENT_TABLE,
    "knowledge_candidate_versions_v1",
    "knowledge_candidate_conflict_reviews_v1",
    "knowledge_candidate_learning_artifacts_v1",
)
_OPERATOR_CAPABILITY = object()

SCHEMA_V1_SQL = """
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
EVENT_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS knowledge_candidate_governance_events_v1 (
    id TEXT PRIMARY KEY,
    promotion_id TEXT,
    package_id TEXT NOT NULL,
    approval_id TEXT NOT NULL UNIQUE,
    reviewer_id TEXT NOT NULL,
    decision TEXT NOT NULL CHECK(decision IN ('approved', 'rejected', 'deprecated')),
    rationale TEXT NOT NULL,
    reviewed_at TEXT NOT NULL,
    candidate_fingerprint TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(promotion_id) REFERENCES knowledge_candidate_promotions_v1(id)
);
CREATE INDEX IF NOT EXISTS idx_knowledge_candidate_events_package_v1
ON knowledge_candidate_governance_events_v1(package_id, created_at, id);
"""
VERSIONING_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS knowledge_candidate_versions_v1 (
    id TEXT PRIMARY KEY, unit_id TEXT NOT NULL, canonical_key TEXT NOT NULL,
    parent_version_id TEXT, content_json TEXT NOT NULL, content_fingerprint TEXT NOT NULL,
    lifecycle_status TEXT NOT NULL CHECK(lifecycle_status IN ('candidate','conflict','deprecated')),
    conflict_review_id TEXT, provenance_json TEXT NOT NULL, created_at TEXT NOT NULL,
    FOREIGN KEY(unit_id) REFERENCES knowledge_candidate_units_v1(id),
    FOREIGN KEY(parent_version_id) REFERENCES knowledge_candidate_versions_v1(id)
);
CREATE INDEX IF NOT EXISTS idx_knowledge_candidate_versions_key_v1 ON knowledge_candidate_versions_v1(canonical_key, created_at, id);
CREATE TABLE IF NOT EXISTS knowledge_candidate_conflict_reviews_v1 (
    id TEXT PRIMARY KEY, canonical_key TEXT NOT NULL, prior_version_id TEXT NOT NULL,
    proposed_version_id TEXT NOT NULL, status TEXT NOT NULL CHECK(status IN ('open','resolved')),
    reviewer_id TEXT NOT NULL, created_at TEXT NOT NULL,
    FOREIGN KEY(prior_version_id) REFERENCES knowledge_candidate_versions_v1(id),
    FOREIGN KEY(proposed_version_id) REFERENCES knowledge_candidate_versions_v1(id)
);
"""
LEARNING_ARTIFACT_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS knowledge_candidate_learning_artifacts_v1 (
    id TEXT PRIMARY KEY, source_unit_id TEXT NOT NULL, approval_id TEXT NOT NULL UNIQUE,
    reviewer_id TEXT NOT NULL, rationale TEXT NOT NULL, artifact_json TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('candidate','rejected','deprecated')),
    created_at TEXT NOT NULL,
    FOREIGN KEY(source_unit_id) REFERENCES knowledge_candidate_units_v1(id)
);
CREATE INDEX IF NOT EXISTS idx_knowledge_candidate_learning_artifacts_source_v1
ON knowledge_candidate_learning_artifacts_v1(source_unit_id, created_at, id);
"""
LEARNING_APPROVAL_EVENT_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS learning_approval_events_v1 (
    id TEXT PRIMARY KEY, artifact_id TEXT NOT NULL, command_id TEXT NOT NULL UNIQUE,
    reviewer_id TEXT NOT NULL, decision TEXT NOT NULL CHECK(decision = 'approved'),
    rationale TEXT NOT NULL, reviewed_at TEXT NOT NULL, created_at TEXT NOT NULL,
    FOREIGN KEY(artifact_id) REFERENCES knowledge_candidate_learning_artifacts_v1(id)
);
CREATE INDEX IF NOT EXISTS idx_learning_approval_events_artifact_v1
ON learning_approval_events_v1(artifact_id, reviewed_at, id);
"""


def _connect(path: Path, *, readonly: bool = False) -> sqlite3.Connection:
    if readonly:
        sidecars = [Path(f"{path}{suffix}") for suffix in ("-wal", "-shm")]
        if any(item.exists() for item in sidecars):
            raise RuntimeError("knowledge governance read requires checkpointed database")
        connection = sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro&immutable=1", uri=True, timeout=30.0)
        connection.execute("PRAGMA query_only=ON")
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(str(path), timeout=30.0)
    connection.execute("PRAGMA busy_timeout=30000")
    connection.row_factory = sqlite3.Row
    return connection


def _recorded_versions(connection: sqlite3.Connection) -> set[int]:
    if not migration._table_exists(connection, "schema_migrations"):
        return set()
    versions = tuple(KNOWLEDGE_GOVERNANCE_MIGRATIONS)
    names = tuple(KNOWLEDGE_GOVERNANCE_MIGRATIONS.values())
    placeholders = ", ".join("?" for _ in versions)
    rows = connection.execute(
        f"SELECT version, name FROM schema_migrations WHERE version IN ({placeholders}) "
        f"OR name IN ({placeholders})",
        (*versions, *names),
    ).fetchall()
    recorded: set[int] = set()
    for row in rows:
        version, name = int(row["version"]), str(row["name"])
        if KNOWLEDGE_GOVERNANCE_MIGRATIONS.get(version) != name:
            raise RuntimeError("knowledge governance migration version/name collision")
        recorded.add(version)
    return recorded


def _schema_objects(sql: str, names: tuple[str, ...]) -> dict[str, tuple[str, str, str]]:
    with closing(sqlite3.connect(":memory:")) as expected_connection:
        _execute_schema(expected_connection, sql)
        placeholders = ", ".join("?" for _ in names)
        rows = expected_connection.execute(
            f"SELECT type, name, tbl_name, sql FROM sqlite_master WHERE name IN ({placeholders})",
            names,
        ).fetchall()
    return {
        str(row[1]): (str(row[0]), str(row[2]), _normalize_sql(str(row[3] or "")))
        for row in rows
    }


def _normalize_sql(sql: str) -> str:
    return " ".join(sql.replace("IF NOT EXISTS", "").split()).casefold()


def _validate_schema(connection: sqlite3.Connection, sql: str, names: tuple[str, ...]) -> None:
    expected = _schema_objects(sql, names)
    placeholders = ", ".join("?" for _ in names)
    rows = connection.execute(
        f"SELECT type, name, tbl_name, sql FROM sqlite_master WHERE name IN ({placeholders})",
        names,
    ).fetchall()
    actual = {
        str(row["name"]): (
            str(row["type"]),
            str(row["tbl_name"]),
            _normalize_sql(str(row["sql"] or "")),
        )
        for row in rows
    }
    if actual != expected:
        raise RuntimeError("knowledge governance recorded schema drift")


def _pending(connection: sqlite3.Connection) -> tuple[str, ...]:
    recorded = _recorded_versions(connection)
    v1_existing = {item for item in KNOWLEDGE_GOVERNANCE_TABLES_V1 if migration._table_exists(connection, item)}
    event_exists = migration._table_exists(connection, KNOWLEDGE_GOVERNANCE_EVENT_TABLE)
    if KNOWLEDGE_GOVERNANCE_MIGRATION_VERSION not in recorded:
        if v1_existing or event_exists:
            raise RuntimeError("unrecorded knowledge governance schema mismatch")
        return tuple(KNOWLEDGE_GOVERNANCE_MIGRATIONS.values())
    if v1_existing != set(KNOWLEDGE_GOVERNANCE_TABLES_V1):
        raise RuntimeError("recorded knowledge governance v1 schema drift")
    _validate_schema(connection, SCHEMA_V1_SQL, KNOWLEDGE_GOVERNANCE_V1_OBJECTS)
    if KNOWLEDGE_GOVERNANCE_EVENT_MIGRATION_VERSION not in recorded:
        if event_exists:
            raise RuntimeError("unrecorded knowledge governance event schema mismatch")
        return (KNOWLEDGE_GOVERNANCE_EVENT_MIGRATION_NAME,)
    if not event_exists:
        raise RuntimeError("recorded knowledge governance event schema drift")
    versioning_tables = {
        "knowledge_candidate_versions_v1",
        "knowledge_candidate_conflict_reviews_v1",
    }
    versioning_existing = {
        item for item in versioning_tables if migration._table_exists(connection, item)
    }
    if KNOWLEDGE_VERSIONING_MIGRATION_VERSION not in recorded:
        if versioning_existing:
            raise RuntimeError("unrecorded knowledge governance versioning schema mismatch")
        return (KNOWLEDGE_VERSIONING_MIGRATION_NAME,)
    if versioning_existing != versioning_tables:
        raise RuntimeError("recorded knowledge governance versioning schema drift")
    artifact_table = "knowledge_candidate_learning_artifacts_v1"
    artifact_exists = migration._table_exists(connection, artifact_table)
    if KNOWLEDGE_LEARNING_ARTIFACT_MIGRATION_VERSION not in recorded:
        if artifact_exists:
            raise RuntimeError("unrecorded knowledge governance learning artifact schema mismatch")
        return (KNOWLEDGE_LEARNING_ARTIFACT_MIGRATION_NAME,)
    if not artifact_exists:
        raise RuntimeError("recorded knowledge governance learning artifact schema drift")
    approval_event_exists = migration._table_exists(connection, "learning_approval_events_v1")
    if LEARNING_APPROVAL_EVENT_MIGRATION_VERSION not in recorded:
        if approval_event_exists:
            raise RuntimeError("unrecorded learning approval event schema mismatch")
        return (LEARNING_APPROVAL_EVENT_MIGRATION_NAME,)
    if not approval_event_exists:
        raise RuntimeError("recorded learning approval event schema drift")
    _validate_schema(
        connection,
        SCHEMA_V1_SQL + EVENT_SCHEMA_SQL + VERSIONING_SCHEMA_SQL + LEARNING_ARTIFACT_SCHEMA_SQL + LEARNING_APPROVAL_EVENT_SCHEMA_SQL,
        (
            *KNOWLEDGE_GOVERNANCE_V1_OBJECTS,
            *KNOWLEDGE_GOVERNANCE_EVENT_OBJECTS,
            *KNOWLEDGE_VERSIONING_OBJECTS,
            *LEARNING_ARTIFACT_OBJECTS,
            *LEARNING_APPROVAL_EVENT_OBJECTS,
        ),
    )
    return ()


def _execute_schema(connection: sqlite3.Connection, sql: str) -> None:
    for statement in sql.split(";"):
        if statement.strip():
            connection.execute(statement)


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
                backup_path = migration._create_backup(
                    database,
                    backups,
                    "+".join(pending),
                    operator_run_id=operator_run_id,
                )
            connection.execute(migration.MIGRATIONS_TABLE)
            for version, name in KNOWLEDGE_GOVERNANCE_MIGRATIONS.items():
                if name not in pending:
                    continue
                schemas = {
                    KNOWLEDGE_GOVERNANCE_MIGRATION_VERSION: SCHEMA_V1_SQL,
                    KNOWLEDGE_GOVERNANCE_EVENT_MIGRATION_VERSION: EVENT_SCHEMA_SQL,
                    KNOWLEDGE_VERSIONING_MIGRATION_VERSION: VERSIONING_SCHEMA_SQL,
                    KNOWLEDGE_LEARNING_ARTIFACT_MIGRATION_VERSION: LEARNING_ARTIFACT_SCHEMA_SQL,
                    LEARNING_APPROVAL_EVENT_MIGRATION_VERSION: LEARNING_APPROVAL_EVENT_SCHEMA_SQL,
                }
                _execute_schema(connection, schemas[version])
                connection.execute("INSERT INTO schema_migrations(version, name) VALUES (?, ?)", (version, name))
            if _pending(connection):
                raise RuntimeError("knowledge governance migration did not converge")
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
        pending = tuple(KNOWLEDGE_GOVERNANCE_MIGRATIONS.values())
    else:
        with closing(_connect(database, readonly=True)) as connection:
            if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise RuntimeError("knowledge governance database integrity check failed")
            pending = _pending(connection)
    applied = [name for name in KNOWLEDGE_GOVERNANCE_MIGRATIONS.values() if name not in pending]
    return {
        "total": len(KNOWLEDGE_GOVERNANCE_MIGRATIONS),
        "applied": len(applied),
        "pending": [
            f"00{version}_{name}"
            for version, name in KNOWLEDGE_GOVERNANCE_MIGRATIONS.items()
            if name in pending
        ],
        "applied_list": applied,
    }


def require_applied(*, db_path: str | Path) -> None:
    if status(db_path=db_path)["pending"]:
        raise RuntimeError("phase5 knowledge governance schema migration is pending")
