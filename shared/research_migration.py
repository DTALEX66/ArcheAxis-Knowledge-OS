"""Formal SQLite migration for Phase 4 research package persistence."""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from contextlib import closing
from pathlib import Path

from shared import migration

RESEARCH_TABLES = (
    "ir_intake_cards",
    "research_sources_v1",
    "research_claims_v1",
    "research_evidence_v1",
    "research_packages_v1",
    "research_governance_findings_v1",
    "research_package_intake_links_v1",
)

RESEARCH_INDEXES = (
    "idx_research_sources_group_v1",
    "idx_research_sources_locator_hash_v1",
    "idx_research_evidence_claim_v1",
    "idx_research_packages_canonical_url_v1",
    "idx_research_findings_package_v1",
)

_OPERATOR_CAPABILITY = object()

RESEARCH_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS ir_intake_cards (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    why TEXT NOT NULL,
    what_to_absorb_json TEXT NOT NULL DEFAULT '[]',
    what_not_to_absorb_json TEXT NOT NULL DEFAULT '[]',
    source_ids_json TEXT NOT NULL DEFAULT '[]',
    risk_level TEXT NOT NULL DEFAULT 'low',
    target_repo TEXT NOT NULL DEFAULT 'Knowledge-Base',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS research_sources_v1 (
    id TEXT PRIMARY KEY,
    schema_version TEXT NOT NULL CHECK(schema_version = '1.0.0'),
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    source_locator TEXT NOT NULL,
    tags_json TEXT NOT NULL DEFAULT '[]',
    provenance_status TEXT NOT NULL CHECK(provenance_status IN ('unverified', 'verified', 'rejected')),
    quarantine_status TEXT NOT NULL CHECK(quarantine_status IN ('candidate', 'released', 'rejected')),
    created_at TEXT NOT NULL,
    canonical_url TEXT NOT NULL,
    source_group_id TEXT NOT NULL,
    retrieved_at TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    content_type TEXT NOT NULL,
    media_type TEXT NOT NULL,
    byte_length INTEGER NOT NULL CHECK(byte_length >= 0),
    collector_identity TEXT NOT NULL,
    extractor_identity TEXT NOT NULL,
    payload_role TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_research_sources_group_v1
ON research_sources_v1(source_group_id);

CREATE UNIQUE INDEX IF NOT EXISTS idx_research_sources_locator_hash_v1
ON research_sources_v1(source_locator, content_hash, extractor_identity);

CREATE TABLE IF NOT EXISTS research_claims_v1 (
    id TEXT PRIMARY KEY,
    schema_version TEXT NOT NULL CHECK(schema_version = '1.0.0'),
    statement TEXT NOT NULL,
    source_record_ids_json TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('candidate', 'verified', 'rejected', 'conflicted', 'unknown')),
    provenance_status TEXT NOT NULL CHECK(provenance_status IN ('caller_supplied', 'server_verified')),
    requires_human_review INTEGER NOT NULL CHECK(requires_human_review IN (0, 1)),
    created_at TEXT NOT NULL,
    claim_kind TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS research_evidence_v1 (
    id TEXT PRIMARY KEY,
    schema_version TEXT NOT NULL CHECK(schema_version = '1.0.0'),
    claim_id TEXT NOT NULL,
    matched_term TEXT NOT NULL,
    source_locator TEXT NOT NULL,
    source_content_hash TEXT NOT NULL,
    location TEXT NOT NULL,
    asset_locator TEXT NOT NULL,
    kind TEXT NOT NULL,
    context TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('matched', 'unverified', 'rejected')),
    provenance_status TEXT NOT NULL CHECK(provenance_status IN ('caller_supplied', 'server_verified')),
    requires_human_review INTEGER NOT NULL CHECK(requires_human_review IN (0, 1)),
    FOREIGN KEY(claim_id) REFERENCES research_claims_v1(id)
);

CREATE INDEX IF NOT EXISTS idx_research_evidence_claim_v1
ON research_evidence_v1(claim_id);

CREATE TABLE IF NOT EXISTS research_packages_v1 (
    id TEXT PRIMARY KEY,
    schema_version TEXT NOT NULL CHECK(schema_version = '1.0.0'),
    canonical_url TEXT NOT NULL,
    intake_id TEXT NOT NULL,
    source_record_ids_json TEXT NOT NULL,
    claim_ids_json TEXT NOT NULL,
    evidence_ids_json TEXT NOT NULL,
    source_group_ids_json TEXT NOT NULL,
    independent_source_count INTEGER NOT NULL CHECK(independent_source_count >= 0),
    conflicts_json TEXT NOT NULL DEFAULT '[]',
    unknowns_json TEXT NOT NULL DEFAULT '[]',
    risks_json TEXT NOT NULL DEFAULT '[]',
    verification_status TEXT NOT NULL CHECK(verification_status IN ('unverified', 'caller_supplied_candidate', 'server_verified')),
    status TEXT NOT NULL CHECK(status IN ('candidate', 'ready_for_review', 'verified', 'rejected')),
    provenance_status TEXT NOT NULL CHECK(provenance_status IN ('caller_supplied', 'server_verified')),
    requires_human_review INTEGER NOT NULL CHECK(requires_human_review IN (0, 1)),
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_research_packages_canonical_url_v1
ON research_packages_v1(canonical_url);

CREATE TABLE IF NOT EXISTS research_governance_findings_v1 (
    id TEXT PRIMARY KEY,
    package_id TEXT NOT NULL,
    finding_type TEXT NOT NULL CHECK(finding_type IN ('corroboration', 'conflict', 'unknown', 'risk')),
    detail TEXT NOT NULL,
    severity TEXT NOT NULL CHECK(severity IN ('info', 'low', 'medium', 'high')),
    claim_id TEXT NOT NULL DEFAULT '',
    evidence_ids_json TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL,
    FOREIGN KEY(package_id) REFERENCES research_packages_v1(id)
);

CREATE INDEX IF NOT EXISTS idx_research_findings_package_v1
ON research_governance_findings_v1(package_id);

CREATE TABLE IF NOT EXISTS research_package_intake_links_v1 (
    package_id TEXT NOT NULL,
    intake_id TEXT NOT NULL,
    relation_type TEXT NOT NULL DEFAULT 'phase4_candidate',
    created_at TEXT NOT NULL,
    PRIMARY KEY(package_id, intake_id),
    FOREIGN KEY(package_id) REFERENCES research_packages_v1(id)
);
"""


def _connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(path), timeout=30.0)
    connection.execute("PRAGMA busy_timeout=30000")
    connection.row_factory = sqlite3.Row
    return connection


def _connect_readonly(path: Path) -> sqlite3.Connection:
    uri = f"{path.resolve().as_uri()}?mode=ro"
    connection = sqlite3.connect(uri, uri=True, timeout=30.0)
    connection.execute("PRAGMA busy_timeout=30000")
    connection.row_factory = sqlite3.Row
    return connection


def _table_exists(connection: sqlite3.Connection, table: str) -> bool:
    return migration._table_exists(connection, table)


def _research_schema_recorded(connection: sqlite3.Connection) -> bool:
    if not _table_exists(connection, "schema_migrations"):
        return False
    rows = connection.execute(
        "SELECT version, name FROM schema_migrations WHERE version=? OR name=?",
        (
            migration.RESEARCH_SCHEMA_MIGRATION_VERSION,
            migration.RESEARCH_SCHEMA_MIGRATION_NAME,
        ),
    ).fetchall()
    recorded = False
    for row in rows:
        version = int(row["version"])
        name = str(row["name"])
        if (
            version == migration.RESEARCH_SCHEMA_MIGRATION_VERSION
            and name == migration.RESEARCH_SCHEMA_MIGRATION_NAME
        ):
            recorded = True
            continue
        raise RuntimeError("research migration version/name collision")
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
            "recorded research migration schema mismatch; objects: " + ", ".join(mismatches)
        )


def _normalize_schema_sql(sql: str) -> str:
    return " ".join(sql.replace("IF NOT EXISTS", "").split()).casefold()


def _expected_schema_objects() -> dict[str, tuple[str, str, str]]:
    names = RESEARCH_TABLES + RESEARCH_INDEXES
    with closing(sqlite3.connect(":memory:")) as expected_connection:
        for statement in RESEARCH_SCHEMA_SQL.split(";"):
            sql = statement.strip()
            if sql:
                expected_connection.execute(sql)
        placeholders = ", ".join("?" for _ in names)
        rows = expected_connection.execute(
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
    owned_tables = tuple(RESEARCH_TABLES)
    name_placeholders = ", ".join("?" for _ in expected_names)
    table_placeholders = ", ".join("?" for _ in owned_tables)
    rows = connection.execute(
        "SELECT type, name, tbl_name, sql FROM sqlite_master "
        "WHERE sql IS NOT NULL AND "
        f"(name IN ({name_placeholders}) OR tbl_name IN ({table_placeholders}))",
        (*expected_names, *owned_tables),
    ).fetchall()
    return {
        str(row["name"]): (
            str(row["type"]),
            str(row["tbl_name"]),
            _normalize_schema_sql(str(row["sql"])),
        )
        for row in rows
    }


def _validate_unrecorded_schema(connection: sqlite3.Connection) -> None:
    expected = _expected_schema_objects()
    actual = _actual_owned_schema_objects(connection, expected)
    mismatches = sorted(
        {name for name, definition in actual.items() if expected.get(name) != definition}
        | (set(actual) - set(expected))
    )
    if mismatches:
        raise RuntimeError(
            "unrecorded research migration schema mismatch; objects: " + ", ".join(mismatches)
        )


def _pending(connection: sqlite3.Connection) -> tuple[str, ...]:
    recorded = _research_schema_recorded(connection)
    if recorded:
        _validate_recorded_schema(connection)
        return ()
    _validate_unrecorded_schema(connection)
    return (migration.RESEARCH_SCHEMA_MIGRATION_NAME,)


def _apply_schema(connection: sqlite3.Connection) -> None:
    for statement in RESEARCH_SCHEMA_SQL.split(";"):
        sql = statement.strip()
        if sql:
            connection.execute(sql)


def migrate(
    *,
    db_path: str | Path,
    backup_dir: str | Path,
    before_commit: Callable[[sqlite3.Connection, migration.MigrationRun], None] | None = None,
    backup_when_pending: bool = False,
    operator_run_id: str | None = None,
    _operator_capability: object | None = None,
) -> migration.MigrationRun:
    """Apply the Phase 4 research schema under the authoritative operator."""

    if _operator_capability is not _OPERATOR_CAPABILITY:
        raise RuntimeError("research schema migration must be driven by MigrationOperator")

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
                    migration.RESEARCH_SCHEMA_MIGRATION_NAME,
                    operator_run_id=operator_run_id,
                )
            connection.execute(migration.MIGRATIONS_TABLE)
            _apply_schema(connection)
            _validate_recorded_schema(connection)
            connection.execute(
                "INSERT INTO schema_migrations(version, name) VALUES (?, ?)",
                (
                    migration.RESEARCH_SCHEMA_MIGRATION_VERSION,
                    migration.RESEARCH_SCHEMA_MIGRATION_NAME,
                ),
            )
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
    """Return Phase 4 research schema migration state without changing the database."""

    database = Path(db_path)
    if not database.is_file():
        return {
            "total": 1,
            "applied": 0,
            "pending": [
                f"{migration.RESEARCH_SCHEMA_MIGRATION_VERSION:03d}_"
                f"{migration.RESEARCH_SCHEMA_MIGRATION_NAME}"
            ],
            "applied_list": [],
        }
    migration._validate_database(database)
    with closing(_connect(database)) as connection:
        pending = _pending(connection)
        applied = not pending
    return {
        "total": 1,
        "applied": 1 if applied else 0,
        "pending": [
            f"{migration.RESEARCH_SCHEMA_MIGRATION_VERSION:03d}_{item}" for item in pending
        ],
        "applied_list": [
            f"{migration.RESEARCH_SCHEMA_MIGRATION_VERSION:03d}_"
            f"{migration.RESEARCH_SCHEMA_MIGRATION_NAME}"
        ]
        if applied
        else [],
    }


def require_applied(*, db_path: str | Path) -> None:
    """Validate the research schema read-only; never create or migrate it."""

    database = Path(db_path)
    if not database.is_file():
        raise RuntimeError("phase4 research schema migration is pending")
    migration._validate_database(database)
    with closing(_connect_readonly(database)) as connection:
        pending = _pending(connection)
    if pending:
        raise RuntimeError("phase4 research schema migration is pending")
