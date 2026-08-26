"""Owner-bound SQLite schema for Research-to-Knowledge candidate governance."""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from contextlib import closing
from datetime import UTC, datetime
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
MACHINE_KNOWLEDGE_APPROVAL_EVENT_MIGRATION_VERSION = 10
MACHINE_KNOWLEDGE_APPROVAL_EVENT_MIGRATION_NAME = "phase5_machine_knowledge_approval_events_v1"
EVIDENCE_BUNDLE_LEDGER_MIGRATION_VERSION = 15
EVIDENCE_BUNDLE_LEDGER_MIGRATION_NAME = "phase5_evidence_bundle_ledger_v1"
AXR_LEARNING_TRUTH_MIGRATION_VERSION = 16
AXR_LEARNING_TRUTH_MIGRATION_NAME = "axr_learning_truth_v2"
AXR_SOURCE_TRUTH_MIGRATION_VERSION = 17
AXR_SOURCE_TRUTH_MIGRATION_NAME = "axr_source_truth_v2"
KNOWLEDGE_GOVERNANCE_MIGRATIONS = {
    KNOWLEDGE_GOVERNANCE_MIGRATION_VERSION: KNOWLEDGE_GOVERNANCE_MIGRATION_NAME,
    KNOWLEDGE_GOVERNANCE_EVENT_MIGRATION_VERSION: KNOWLEDGE_GOVERNANCE_EVENT_MIGRATION_NAME,
    KNOWLEDGE_VERSIONING_MIGRATION_VERSION: KNOWLEDGE_VERSIONING_MIGRATION_NAME,
    KNOWLEDGE_LEARNING_ARTIFACT_MIGRATION_VERSION: KNOWLEDGE_LEARNING_ARTIFACT_MIGRATION_NAME,
    LEARNING_APPROVAL_EVENT_MIGRATION_VERSION: LEARNING_APPROVAL_EVENT_MIGRATION_NAME,
    MACHINE_KNOWLEDGE_APPROVAL_EVENT_MIGRATION_VERSION: MACHINE_KNOWLEDGE_APPROVAL_EVENT_MIGRATION_NAME,
    EVIDENCE_BUNDLE_LEDGER_MIGRATION_VERSION: EVIDENCE_BUNDLE_LEDGER_MIGRATION_NAME,
    AXR_LEARNING_TRUTH_MIGRATION_VERSION: AXR_LEARNING_TRUTH_MIGRATION_NAME,
    AXR_SOURCE_TRUTH_MIGRATION_VERSION: AXR_SOURCE_TRUTH_MIGRATION_NAME,
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
MACHINE_KNOWLEDGE_APPROVAL_EVENT_OBJECTS = (
    "machine_knowledge_approval_events_v1",
    "idx_machine_knowledge_approval_events_candidate_v1",
)
EVIDENCE_BUNDLE_LEDGER_OBJECTS = (
    "evidence_bundles_v1",
    "evidence_bundle_entries_v1",
    "idx_evidence_bundle_entries_bundle_v1",
    "evidence_bundle_reviews_v1",
    "idx_evidence_bundle_reviews_bundle_v1",
)
AXR_LEARNING_TRUTH_OBJECTS = (
    "learning_events_v2",
    "idx_learning_events_v2_learner_node",
    "distillation_candidates_v2",
    "idx_distillation_candidates_v2_status",
    "machine_competence_receipts_v2",
    "idx_machine_competence_receipts_v2_node",
    "machine_competence_legacy_v2",
)
AXR_SOURCE_TRUTH_OBJECTS = (
    "source_objects_v2",
    "idx_source_objects_v2_sha",
    "anchors_v2",
    "idx_anchors_v2_source",
    "provenance_activities_v2",
    "idx_provenance_activities_v2_source",
    "archive_exports_v2",
    "idx_archive_exports_v2_source",
)
KNOWLEDGE_GOVERNANCE_TABLES = (
    *KNOWLEDGE_GOVERNANCE_TABLES_V1,
    KNOWLEDGE_GOVERNANCE_EVENT_TABLE,
    "knowledge_candidate_versions_v1",
    "knowledge_candidate_conflict_reviews_v1",
    "knowledge_candidate_learning_artifacts_v1",
    "evidence_bundles_v1",
    "evidence_bundle_entries_v1",
    "evidence_bundle_reviews_v1",
    "learning_events_v2",
    "distillation_candidates_v2",
    "machine_competence_receipts_v2",
    "machine_competence_legacy_v2",
    "source_objects_v2",
    "anchors_v2",
    "provenance_activities_v2",
    "archive_exports_v2",
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
MACHINE_KNOWLEDGE_APPROVAL_EVENT_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS machine_knowledge_approval_events_v1 (
    id TEXT PRIMARY KEY, candidate_id TEXT NOT NULL, approval_id TEXT NOT NULL UNIQUE,
    reviewer_id TEXT NOT NULL, decision TEXT NOT NULL CHECK(decision IN ('approved','deprecated')),
    rationale TEXT NOT NULL, reviewed_at TEXT NOT NULL, created_at TEXT NOT NULL,
    FOREIGN KEY(candidate_id) REFERENCES machine_knowledge_candidates_v1(id)
);
CREATE INDEX IF NOT EXISTS idx_machine_knowledge_approval_events_candidate_v1
ON machine_knowledge_approval_events_v1(candidate_id, reviewed_at, id);
"""
EVIDENCE_BUNDLE_LEDGER_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS evidence_bundles_v1 (
    id TEXT PRIMARY KEY,
    claim_id TEXT NOT NULL,
    bundle_fingerprint TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS evidence_bundle_entries_v1 (
    id TEXT PRIMARY KEY,
    bundle_id TEXT NOT NULL,
    relation_kind TEXT NOT NULL CHECK(relation_kind IN ('supports','refutes','unknown')),
    raw_sha256 TEXT NOT NULL CHECK(length(raw_sha256) = 64),
    source_revision TEXT NOT NULL,
    anchor_json TEXT NOT NULL,
    source_lineage TEXT NOT NULL,
    source_kind TEXT NOT NULL,
    valid_from TEXT,
    valid_to TEXT,
    scope TEXT NOT NULL,
    rights TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(bundle_id) REFERENCES evidence_bundles_v1(id)
);
CREATE INDEX IF NOT EXISTS idx_evidence_bundle_entries_bundle_v1
ON evidence_bundle_entries_v1(bundle_id, created_at, id);
CREATE TABLE IF NOT EXISTS evidence_bundle_reviews_v1 (
    id TEXT PRIMARY KEY,
    bundle_id TEXT NOT NULL,
    decision TEXT NOT NULL CHECK(decision IN ('verified','not_verifiable','rejected')),
    reviewer_id TEXT NOT NULL,
    rationale TEXT NOT NULL,
    reviewed_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(bundle_id) REFERENCES evidence_bundles_v1(id)
);
CREATE INDEX IF NOT EXISTS idx_evidence_bundle_reviews_bundle_v1
ON evidence_bundle_reviews_v1(bundle_id, reviewed_at, id);
"""
AXR_LEARNING_TRUTH_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS learning_events_v2 (
    event_id TEXT PRIMARY KEY,
    learner_id TEXT NOT NULL,
    node_id TEXT NOT NULL,
    event_type TEXT NOT NULL CHECK(event_type IN (
        'review','quiz','teach_back','mistake','hint','session_started','session_completed'
    )),
    payload_json TEXT NOT NULL CHECK(json_valid(payload_json)),
    occurred_at TEXT NOT NULL,
    idempotency_key TEXT NOT NULL UNIQUE,
    source_system TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_learning_events_v2_learner_node
ON learning_events_v2(learner_id, node_id, occurred_at, event_id);
CREATE TABLE IF NOT EXISTS distillation_candidates_v2 (
    candidate_id TEXT PRIMARY KEY,
    source_event_id TEXT NOT NULL UNIQUE,
    source_card_id TEXT NOT NULL,
    payload_json TEXT NOT NULL CHECK(json_valid(payload_json)),
    status TEXT NOT NULL CHECK(status IN ('unverified','reviewed','rejected','promoted')),
    reviewer_id TEXT,
    review_rationale TEXT,
    created_at TEXT NOT NULL,
    reviewed_at TEXT,
    FOREIGN KEY(source_event_id) REFERENCES learning_events_v2(event_id)
);
CREATE INDEX IF NOT EXISTS idx_distillation_candidates_v2_status
ON distillation_candidates_v2(status, created_at, candidate_id);
CREATE TABLE IF NOT EXISTS machine_competence_receipts_v2 (
    receipt_id TEXT PRIMARY KEY,
    node_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    level TEXT NOT NULL CHECK(level IN ('K0','K1','K2','K3','K4','K5','K6','K7','K8')),
    outcome TEXT NOT NULL CHECK(outcome IN ('passed','failed')),
    evidence_bundle_id TEXT NOT NULL,
    evaluator TEXT NOT NULL,
    payload_json TEXT NOT NULL CHECK(json_valid(payload_json)),
    created_at TEXT NOT NULL,
    UNIQUE(node_id, task_id, evaluator, evidence_bundle_id),
    FOREIGN KEY(evidence_bundle_id) REFERENCES evidence_bundles_v1(id)
);
CREATE INDEX IF NOT EXISTS idx_machine_competence_receipts_v2_node
ON machine_competence_receipts_v2(node_id, created_at, receipt_id);
CREATE TABLE IF NOT EXISTS machine_competence_legacy_v2 (
    legacy_table TEXT NOT NULL,
    legacy_id TEXT NOT NULL,
    migration_status TEXT NOT NULL CHECK(migration_status = 'UNMIGRATED'),
    observed_at TEXT NOT NULL,
    PRIMARY KEY(legacy_table, legacy_id)
);
"""
AXR_SOURCE_TRUTH_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS source_objects_v2 (
    source_id TEXT NOT NULL,
    version INTEGER NOT NULL CHECK(version >= 1),
    raw_sha256 TEXT NOT NULL CHECK(length(raw_sha256) = 64),
    byte_size INTEGER NOT NULL CHECK(byte_size >= 0),
    media_type TEXT NOT NULL,
    rights_status TEXT NOT NULL CHECK(rights_status IN (
        'owned','licensed','public-domain','permission-recorded'
    )),
    rights_json TEXT NOT NULL CHECK(json_valid(rights_json)),
    provenance_json TEXT NOT NULL CHECK(json_valid(provenance_json)),
    original_retained INTEGER NOT NULL CHECK(original_retained = 1),
    created_at TEXT NOT NULL,
    PRIMARY KEY(source_id, version)
);
CREATE INDEX IF NOT EXISTS idx_source_objects_v2_sha
ON source_objects_v2(raw_sha256, source_id, version);
CREATE TABLE IF NOT EXISTS anchors_v2 (
    anchor_id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL,
    source_version INTEGER NOT NULL,
    selector_json TEXT NOT NULL CHECK(json_valid(selector_json)),
    quote_sha256 TEXT,
    state TEXT NOT NULL CHECK(state IN ('CURRENT','STALE','ORPHANED')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(source_id, source_version) REFERENCES source_objects_v2(source_id, version)
);
CREATE INDEX IF NOT EXISTS idx_anchors_v2_source
ON anchors_v2(source_id, source_version, state, anchor_id);
CREATE TABLE IF NOT EXISTS provenance_activities_v2 (
    activity_id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL,
    source_version INTEGER NOT NULL,
    activity_type TEXT NOT NULL,
    agent TEXT NOT NULL,
    used_json TEXT NOT NULL CHECK(json_valid(used_json)),
    generated_json TEXT NOT NULL CHECK(json_valid(generated_json)),
    started_at TEXT NOT NULL,
    ended_at TEXT,
    FOREIGN KEY(source_id, source_version) REFERENCES source_objects_v2(source_id, version)
);
CREATE INDEX IF NOT EXISTS idx_provenance_activities_v2_source
ON provenance_activities_v2(source_id, source_version, started_at, activity_id);
CREATE TABLE IF NOT EXISTS archive_exports_v2 (
    export_id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL,
    source_version INTEGER NOT NULL,
    artifact_ref TEXT NOT NULL,
    inventory_sha512 TEXT NOT NULL CHECK(length(inventory_sha512) = 128),
    verified INTEGER NOT NULL CHECK(verified IN (0,1)),
    created_at TEXT NOT NULL,
    FOREIGN KEY(source_id, source_version) REFERENCES source_objects_v2(source_id, version)
);
CREATE INDEX IF NOT EXISTS idx_archive_exports_v2_source
ON archive_exports_v2(source_id, source_version, created_at, export_id);
"""


def _connect(
    path: Path, *, readonly: bool = False, live_wal: bool = False
) -> sqlite3.Connection:
    if readonly:
        if live_wal:
            connection = sqlite3.connect(str(path), timeout=30.0)
        else:
            sidecars = [Path(f"{path}{suffix}") for suffix in ("-wal", "-shm")]
            if any(item.exists() for item in sidecars):
                raise RuntimeError("knowledge governance read requires checkpointed database")
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


def _actual_owned_schema_objects(
    connection: sqlite3.Connection,
    expected: dict[str, tuple[str, str, str]],
) -> dict[str, tuple[str, str, str]]:
    expected_names = tuple(expected)
    owned_tables = tuple(
        name for name, definition in expected.items() if definition[0] == "table"
    )
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
            _normalize_sql(str(row["sql"])),
        )
        for row in rows
    }


def _validate_schema(connection: sqlite3.Connection, sql: str, names: tuple[str, ...]) -> None:
    expected = _schema_objects(sql, names)
    actual = _actual_owned_schema_objects(connection, expected)
    if actual != expected:
        raise RuntimeError("knowledge governance recorded schema drift")


def _pending(connection: sqlite3.Connection) -> tuple[str, ...]:
    recorded = _recorded_versions(connection)
    specifications = (
        (
            KNOWLEDGE_GOVERNANCE_MIGRATION_VERSION,
            KNOWLEDGE_GOVERNANCE_MIGRATION_NAME,
            SCHEMA_V1_SQL,
            KNOWLEDGE_GOVERNANCE_V1_OBJECTS,
        ),
        (
            KNOWLEDGE_GOVERNANCE_EVENT_MIGRATION_VERSION,
            KNOWLEDGE_GOVERNANCE_EVENT_MIGRATION_NAME,
            EVENT_SCHEMA_SQL,
            KNOWLEDGE_GOVERNANCE_EVENT_OBJECTS,
        ),
        (
            KNOWLEDGE_VERSIONING_MIGRATION_VERSION,
            KNOWLEDGE_VERSIONING_MIGRATION_NAME,
            VERSIONING_SCHEMA_SQL,
            KNOWLEDGE_VERSIONING_OBJECTS,
        ),
        (
            KNOWLEDGE_LEARNING_ARTIFACT_MIGRATION_VERSION,
            KNOWLEDGE_LEARNING_ARTIFACT_MIGRATION_NAME,
            LEARNING_ARTIFACT_SCHEMA_SQL,
            LEARNING_ARTIFACT_OBJECTS,
        ),
        (
            LEARNING_APPROVAL_EVENT_MIGRATION_VERSION,
            LEARNING_APPROVAL_EVENT_MIGRATION_NAME,
            LEARNING_APPROVAL_EVENT_SCHEMA_SQL,
            LEARNING_APPROVAL_EVENT_OBJECTS,
        ),
        (
            MACHINE_KNOWLEDGE_APPROVAL_EVENT_MIGRATION_VERSION,
            MACHINE_KNOWLEDGE_APPROVAL_EVENT_MIGRATION_NAME,
            MACHINE_KNOWLEDGE_APPROVAL_EVENT_SCHEMA_SQL,
            MACHINE_KNOWLEDGE_APPROVAL_EVENT_OBJECTS,
        ),
        (
            EVIDENCE_BUNDLE_LEDGER_MIGRATION_VERSION,
            EVIDENCE_BUNDLE_LEDGER_MIGRATION_NAME,
            EVIDENCE_BUNDLE_LEDGER_SCHEMA_SQL,
            EVIDENCE_BUNDLE_LEDGER_OBJECTS,
        ),
        (
            AXR_LEARNING_TRUTH_MIGRATION_VERSION,
            AXR_LEARNING_TRUTH_MIGRATION_NAME,
            AXR_LEARNING_TRUTH_SCHEMA_SQL,
            AXR_LEARNING_TRUTH_OBJECTS,
        ),
        (
            AXR_SOURCE_TRUTH_MIGRATION_VERSION,
            AXR_SOURCE_TRUTH_MIGRATION_NAME,
            AXR_SOURCE_TRUTH_SCHEMA_SQL,
            AXR_SOURCE_TRUTH_OBJECTS,
        ),
    )
    for index, (version, _name, schema_sql, object_names) in enumerate(specifications):
        if version in recorded:
            _validate_schema(connection, schema_sql, object_names)
            continue
        later_versions = {item[0] for item in specifications[index + 1 :]}
        if recorded & later_versions:
            raise RuntimeError("knowledge governance migration schema is not contiguous")
        for _, _, pending_sql, pending_objects in specifications[index:]:
            expected = _schema_objects(pending_sql, pending_objects)
            if _actual_owned_schema_objects(connection, expected):
                raise RuntimeError("unrecorded knowledge governance schema mismatch")
        return tuple(item[1] for item in specifications[index:])
    return ()


def _execute_schema(connection: sqlite3.Connection, sql: str) -> None:
    for statement in sql.split(";"):
        if statement.strip():
            connection.execute(statement)


def _mark_legacy_machine_state_unmigrated(connection: sqlite3.Connection) -> None:
    """Quarantine legacy machine rows instead of inventing K-level evidence."""
    observed_at = datetime.now(UTC).isoformat()
    for table in ("machine_knowledge", "machine_knowledge_units"):
        if not migration._table_exists(connection, table):
            continue
        rows = connection.execute(f'SELECT id FROM "{table}"').fetchall()
        connection.executemany(
            "INSERT OR IGNORE INTO machine_competence_legacy_v2 "
            "(legacy_table, legacy_id, migration_status, observed_at) "
            "VALUES (?, ?, 'UNMIGRATED', ?)",
            ((table, str(row[0]), observed_at) for row in rows),
        )


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
                    MACHINE_KNOWLEDGE_APPROVAL_EVENT_MIGRATION_VERSION: MACHINE_KNOWLEDGE_APPROVAL_EVENT_SCHEMA_SQL,
                    EVIDENCE_BUNDLE_LEDGER_MIGRATION_VERSION: EVIDENCE_BUNDLE_LEDGER_SCHEMA_SQL,
                    AXR_LEARNING_TRUTH_MIGRATION_VERSION: AXR_LEARNING_TRUTH_SCHEMA_SQL,
                    AXR_SOURCE_TRUTH_MIGRATION_VERSION: AXR_SOURCE_TRUTH_SCHEMA_SQL,
                }
                _execute_schema(connection, schemas[version])
                if version == AXR_LEARNING_TRUTH_MIGRATION_VERSION:
                    _mark_legacy_machine_state_unmigrated(connection)
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


def status(*, db_path: str | Path, live_wal: bool = False) -> dict[str, object]:
    database = Path(db_path)
    if not database.is_file():
        pending = tuple(KNOWLEDGE_GOVERNANCE_MIGRATIONS.values())
    else:
        with closing(_connect(database, readonly=True, live_wal=live_wal)) as connection:
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


def require_applied(*, db_path: str | Path, live_wal: bool = False) -> None:
    if status(db_path=db_path, live_wal=live_wal)["pending"]:
        raise RuntimeError("phase5 knowledge governance schema migration is pending")
