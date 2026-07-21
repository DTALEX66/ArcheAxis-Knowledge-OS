"""Transactional, backed-up SQLite migrations for Cognitive-Loop-OS.

Migrations are code-owned and shipped with the application. Runtime data directories
contain databases and backups only; they are never treated as a source of executable
migration SQL.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import sqlite3
from collections.abc import Callable
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from shared.config import config, resolve_runtime_path
from shared.core_schema import BASELINE_MIGRATION_NAME

DB_PATH = resolve_runtime_path(str(config.get("database.path", "data/cognitive_os.sqlite")))
BACKUP_DIR = resolve_runtime_path(str(config.get("database.backup_dir", "data/backups")))

MIGRATIONS_TABLE = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    applied_at TEXT NOT NULL DEFAULT (datetime('now'))
)
"""

TASKPACK_MIGRATION_VERSION = 2
TASKPACK_MIGRATION_NAME = "taskpack_contract_v1"
TASKPACK_REPAIR_VERSION = 3
TASKPACK_REPAIR_NAME = "taskpack_review_fail_closed_v1"
TASKPACK_MIGRATIONS = {
    TASKPACK_MIGRATION_VERSION: TASKPACK_MIGRATION_NAME,
    TASKPACK_REPAIR_VERSION: TASKPACK_REPAIR_NAME,
}
RESEARCH_SCHEMA_MIGRATION_VERSION = 4
RESEARCH_SCHEMA_MIGRATION_NAME = "phase4_research_package_v1"
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
WORKSPACE_SCHEMA_MIGRATION_VERSION = 11
WORKSPACE_SCHEMA_MIGRATION_NAME = "phase5_workspace_job_outbox_v1"
SLEEP_LOOP_MIGRATION_VERSION = 12
SLEEP_LOOP_MIGRATION_NAME = "phase8_sleep_loop_runtime_leases_v1"
ROLLBACK_MIGRATION_NAMES = set(TASKPACK_MIGRATIONS.values()) | {
    RESEARCH_SCHEMA_MIGRATION_NAME,
    KNOWLEDGE_GOVERNANCE_MIGRATION_NAME,
    KNOWLEDGE_GOVERNANCE_EVENT_MIGRATION_NAME,
    KNOWLEDGE_VERSIONING_MIGRATION_NAME,
    KNOWLEDGE_LEARNING_ARTIFACT_MIGRATION_NAME,
    LEARNING_APPROVAL_EVENT_MIGRATION_NAME,
    MACHINE_KNOWLEDGE_APPROVAL_EVENT_MIGRATION_NAME,
    WORKSPACE_SCHEMA_MIGRATION_NAME,
    SLEEP_LOOP_MIGRATION_NAME,
    BASELINE_MIGRATION_NAME,
}
TASKPACK_COLUMNS = {
    "id",
    "context_id",
    "goal",
    "steps_json",
    "allowed_tools_json",
    "blocked_tools_json",
    "constraints_json",
    "success_criteria_json",
    "risk_level",
    "requires_review",
    "created_at",
}
TASKPACK_PRESERVED_COLUMNS = (
    "id",
    "context_id",
    "goal",
    "steps_json",
    "allowed_tools_json",
    "blocked_tools_json",
    "constraints_json",
    "success_criteria_json",
    "risk_level",
    "created_at",
)


@dataclass(frozen=True)
class MigrationRun:
    """Evidence returned by one migration invocation."""

    applied: tuple[str, ...]
    backup_path: Path | None


def _connect(path: Path, *, read_only: bool = False) -> sqlite3.Connection:
    target = f"{path.resolve().as_uri()}?mode=ro" if read_only else str(path)
    connection = sqlite3.connect(target, timeout=30.0, uri=read_only)
    connection.execute("PRAGMA busy_timeout=30000")
    connection.row_factory = sqlite3.Row
    return connection


def _table_exists(connection: sqlite3.Connection, table: str) -> bool:
    return (
        connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
        ).fetchone()
        is not None
    )


def _validate_database(path: Path) -> None:
    if not path.is_file():
        raise FileNotFoundError(f"SQLite database not found: {path}")
    with closing(_connect(path, read_only=True)) as connection:
        result = connection.execute("PRAGMA integrity_check").fetchone()[0]
        if result != "ok":
            raise RuntimeError(f"SQLite integrity check failed for {path}: {result}")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _backup_manifest_path(backup: Path) -> Path:
    return backup.with_suffix(f"{backup.suffix}.manifest.json")


def _create_backup(
    database: Path,
    backup_dir: Path,
    migration_name: str,
    *,
    operator_run_id: str | None = None,
) -> Path:
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")
    destination = backup_dir / f"pre_migration_{stamp}_{uuid4().hex[:8]}.sqlite"
    manifest = _backup_manifest_path(destination)
    temporary_manifest = manifest.with_suffix(f"{manifest.suffix}.tmp")
    try:
        with closing(_connect(database)) as source, closing(_connect(destination)) as target:
            source.backup(target)
        _validate_database(destination)
        payload = {
            "schema_version": 1,
            "migration": migration_name,
            "source_database": str(database.resolve(strict=True)),
            "backup_sha256": _sha256(destination),
            "operator_run_id": operator_run_id,
        }
        temporary_manifest.write_text(
            json.dumps(payload, ensure_ascii=True, sort_keys=True), encoding="utf-8"
        )
        temporary_manifest.replace(manifest)
    except Exception:
        temporary_manifest.unlink(missing_ok=True)
        manifest.unlink(missing_ok=True)
        destination.unlink(missing_ok=True)
        raise
    return destination


def _requires_review_schema_is_fail_closed(connection: sqlite3.Connection) -> bool:
    columns = {
        str(row["name"]): row
        for row in connection.execute("PRAGMA table_info(kb_taskpacks)").fetchall()
    }
    column = columns.get("requires_review")
    if column is None:
        return False
    table_row = connection.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='kb_taskpacks'"
    ).fetchone()
    compact_sql = "".join(str(table_row["sql"] or "").upper().split())
    invalid_values = connection.execute(
        "SELECT 1 FROM kb_taskpacks WHERE requires_review IS NULL "
        "OR requires_review NOT IN (0, 1) LIMIT 1"
    ).fetchone()
    return (
        int(column["notnull"]) == 1
        and str(column["dflt_value"]) == "1"
        and "CHECK(REQUIRES_REVIEWIN(0,1))" in compact_sql
        and invalid_values is None
    )


def _recorded_taskpack_migrations(connection: sqlite3.Connection) -> dict[int, str]:
    if not _table_exists(connection, "schema_migrations"):
        return {}
    return {
        int(row["version"]): str(row["name"])
        for row in connection.execute(
            "SELECT version, name FROM schema_migrations WHERE version IN (?, ?) OR name IN (?, ?)",
            (
                TASKPACK_MIGRATION_VERSION,
                TASKPACK_REPAIR_VERSION,
                TASKPACK_MIGRATION_NAME,
                TASKPACK_REPAIR_NAME,
            ),
        ).fetchall()
    }


def _taskpack_migrations_pending(connection: sqlite3.Connection) -> tuple[str, ...]:
    recorded = _recorded_taskpack_migrations(connection)
    for version, actual_name in recorded.items():
        expected_name = TASKPACK_MIGRATIONS.get(version)
        if expected_name == actual_name:
            continue
        if expected_name is not None:
            raise RuntimeError(
                f"migration version {version} name collision: "
                f"expected {expected_name!r}, found {actual_name!r}"
            )
        raise RuntimeError(
            "migration version/name collision: "
            f"name {actual_name!r} is registered at unexpected version {version}"
        )
    if TASKPACK_REPAIR_VERSION in recorded and TASKPACK_MIGRATION_VERSION not in recorded:
        raise RuntimeError("taskpack repair migration is recorded without its prerequisite")

    taskpack_exists = _table_exists(connection, "kb_taskpacks")
    if not taskpack_exists:
        if recorded:
            raise RuntimeError("recorded taskpack migration schema mismatch; table is missing")
        return ()

    columns = {
        str(row["name"]) for row in connection.execute("PRAGMA table_info(kb_taskpacks)").fetchall()
    }
    if TASKPACK_MIGRATION_VERSION in recorded:
        missing_columns = {"context_id", "requires_review"} - columns
        if missing_columns:
            detail = ", ".join(sorted(missing_columns))
            raise RuntimeError(f"recorded migration schema mismatch; missing: {detail}")
    if TASKPACK_REPAIR_VERSION in recorded and not _requires_review_schema_is_fail_closed(
        connection
    ):
        raise RuntimeError("recorded repair migration schema mismatch")

    return tuple(name for version, name in TASKPACK_MIGRATIONS.items() if version not in recorded)


def _apply_taskpack_migration(connection: sqlite3.Connection) -> None:
    columns = {
        str(row["name"]) for row in connection.execute("PRAGMA table_info(kb_taskpacks)").fetchall()
    }
    if "context_id" not in columns:
        connection.execute(
            "ALTER TABLE kb_taskpacks ADD COLUMN context_id TEXT NOT NULL DEFAULT ''"
        )
    if "requires_review" not in columns:
        connection.execute(
            "ALTER TABLE kb_taskpacks ADD COLUMN requires_review INTEGER NOT NULL DEFAULT 1 "
            "CHECK(requires_review IN (0, 1))"
        )


def _taskpack_v3_repair_required(connection: sqlite3.Connection) -> bool:
    if not _requires_review_schema_is_fail_closed(connection):
        return True
    return (
        connection.execute(
            "SELECT 1 FROM kb_taskpacks WHERE requires_review != 1 LIMIT 1"
        ).fetchone()
        is not None
    )


def _validate_taskpack_repair_copy(connection: sqlite3.Connection) -> None:
    source_count = int(connection.execute("SELECT COUNT(*) FROM kb_taskpacks").fetchone()[0])
    target_count = int(
        connection.execute("SELECT COUNT(*) FROM kb_taskpacks__repair").fetchone()[0]
    )
    if source_count != target_count:
        raise RuntimeError("kb_taskpacks repair row count mismatch")

    columns = ", ".join(TASKPACK_PRESERVED_COLUMNS)
    for source, target in (
        ("kb_taskpacks", "kb_taskpacks__repair"),
        ("kb_taskpacks__repair", "kb_taskpacks"),
    ):
        difference = connection.execute(
            f"SELECT 1 FROM ("
            f"SELECT {columns} FROM {source} "
            f"EXCEPT SELECT {columns} FROM {target}"
            f") LIMIT 1"
        ).fetchone()
        if difference is not None:
            raise RuntimeError("kb_taskpacks repair field preservation mismatch")
    unsafe_review = connection.execute(
        "SELECT 1 FROM kb_taskpacks__repair WHERE requires_review != 1 LIMIT 1"
    ).fetchone()
    if unsafe_review is not None:
        raise RuntimeError("kb_taskpacks repair did not fail closed")


def _reject_unsupported_taskpack_table_constraints(connection: sqlite3.Connection) -> None:
    table_row = connection.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='kb_taskpacks'"
    ).fetchone()
    table_sql = str(table_row["sql"] or "") if table_row is not None else ""
    compact_sql = "".join(table_sql.upper().split())
    index_rows = connection.execute("PRAGMA index_list(kb_taskpacks)").fetchall()
    has_implicit_unique = any(str(row["origin"]) == "u" for row in index_rows)
    has_foreign_key = (
        connection.execute("PRAGMA foreign_key_list(kb_taskpacks)").fetchone() is not None
    )
    check_count = len(re.findall(r"\bCHECK\s*\(", table_sql, flags=re.IGNORECASE))
    has_expected_review_check = "CHECK(REQUIRES_REVIEWIN(0,1))" in compact_sql
    has_unsupported_check = check_count > 1 or (check_count == 1 and not has_expected_review_check)
    if (
        has_implicit_unique
        or has_foreign_key
        or re.search(r"\bUNIQUE\s*\(", table_sql, flags=re.IGNORECASE)
        or re.search(r"\bCONSTRAINT\b", table_sql, flags=re.IGNORECASE)
        or has_unsupported_check
    ):
        raise RuntimeError("unsupported kb_taskpacks table constraints")


def _repair_taskpack_review_schema(connection: sqlite3.Connection) -> None:
    if not _taskpack_v3_repair_required(connection):
        return
    columns = {
        str(row["name"]) for row in connection.execute("PRAGMA table_info(kb_taskpacks)").fetchall()
    }
    if columns != TASKPACK_COLUMNS:
        detail = ", ".join(sorted(columns ^ TASKPACK_COLUMNS))
        raise RuntimeError(f"cannot safely rebuild kb_taskpacks; unexpected columns: {detail}")
    _reject_unsupported_taskpack_table_constraints(connection)
    dependent_schema = [
        str(row["sql"])
        for row in connection.execute(
            "SELECT sql FROM sqlite_master "
            "WHERE tbl_name='kb_taskpacks' AND type IN ('index', 'trigger') "
            "AND sql IS NOT NULL ORDER BY type, name"
        ).fetchall()
    ]
    connection.execute(
        """
        CREATE TABLE kb_taskpacks__repair (
            id TEXT PRIMARY KEY,
            context_id TEXT NOT NULL DEFAULT '',
            goal TEXT NOT NULL,
            steps_json TEXT NOT NULL DEFAULT '[]',
            allowed_tools_json TEXT NOT NULL DEFAULT '[]',
            blocked_tools_json TEXT NOT NULL DEFAULT '[]',
            constraints_json TEXT NOT NULL DEFAULT '[]',
            success_criteria_json TEXT NOT NULL DEFAULT '[]',
            risk_level TEXT NOT NULL DEFAULT 'low',
            requires_review INTEGER NOT NULL DEFAULT 1 CHECK(requires_review IN (0, 1)),
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    connection.execute(
        """
        INSERT INTO kb_taskpacks__repair (
            id, context_id, goal, steps_json, allowed_tools_json, blocked_tools_json,
            constraints_json, success_criteria_json, risk_level, requires_review, created_at
        )
        SELECT
            id, context_id, goal, steps_json, allowed_tools_json, blocked_tools_json,
            constraints_json, success_criteria_json, risk_level, 1, created_at
        FROM kb_taskpacks
        """
    )
    _validate_taskpack_repair_copy(connection)
    connection.execute("DROP TABLE kb_taskpacks")
    connection.execute("ALTER TABLE kb_taskpacks__repair RENAME TO kb_taskpacks")
    for statement in dependent_schema:
        connection.execute(statement)


def _taskpack_schema_change_required(
    connection: sqlite3.Connection, pending: tuple[str, ...]
) -> bool:
    columns = {
        str(row["name"]) for row in connection.execute("PRAGMA table_info(kb_taskpacks)").fetchall()
    }
    if TASKPACK_MIGRATION_NAME in pending and {"context_id", "requires_review"} - columns:
        return True
    return bool(
        TASKPACK_REPAIR_NAME in pending
        and "requires_review" in columns
        and _taskpack_v3_repair_required(connection)
    )


def migrate(
    *,
    db_path: str | Path = DB_PATH,
    backup_dir: str | Path = BACKUP_DIR,
    before_commit: Callable[[sqlite3.Connection, MigrationRun], None] | None = None,
    backup_when_pending: bool = False,
    operator_run_id: str | None = None,
) -> MigrationRun:
    """Apply pending migrations once, after creating a verified SQLite backup."""

    database = Path(db_path)
    backups = Path(backup_dir)
    _validate_database(database)

    backup_path: Path | None = None
    with closing(_connect(database)) as connection:
        try:
            connection.execute("BEGIN IMMEDIATE")
            pending = _taskpack_migrations_pending(connection)
            if not pending:
                connection.commit()
                return MigrationRun(applied=(), backup_path=None)
            if backup_when_pending or _taskpack_schema_change_required(connection, pending):
                backup_path = _create_backup(
                    database,
                    backups,
                    "+".join(pending),
                    operator_run_id=operator_run_id,
                )
            connection.execute(MIGRATIONS_TABLE)
            for version, name in TASKPACK_MIGRATIONS.items():
                if name not in pending:
                    continue
                if version == TASKPACK_MIGRATION_VERSION:
                    _apply_taskpack_migration(connection)
                elif version == TASKPACK_REPAIR_VERSION:
                    _repair_taskpack_review_schema(connection)
                connection.execute(
                    "INSERT INTO schema_migrations(version, name) VALUES (?, ?)",
                    (version, name),
                )
            run = MigrationRun(applied=pending, backup_path=backup_path)
            if before_commit is not None:
                before_commit(connection, run)
            connection.commit()
        except Exception:
            connection.rollback()
            raise

    _validate_database(database)
    return run


def rollback(
    *,
    backup_path: str | Path,
    db_path: str | Path = DB_PATH,
    prepare_replacement: Callable[[Path], None] | None = None,
    expected_migrations: set[str] | None = None,
    expected_operator_run_id: str | None = None,
) -> Path:
    """Restore a migration backup while the runtime is offline.

    Idle WAL state is checkpointed and switched to DELETE before replacement.
    Busy connections or residual WAL/SHM sidecars fail closed.
    """

    backup = Path(backup_path)
    database = Path(db_path)
    _validate_database(backup)
    manifest_path = _backup_manifest_path(backup)
    if not manifest_path.is_file():
        raise RuntimeError("backup provenance manifest is missing")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError("backup provenance manifest is invalid") from exc
    recorded_migrations = set(str(manifest.get("migration", "")).split("+"))
    if (
        manifest.get("schema_version") != 1
        or not recorded_migrations
        or not recorded_migrations <= ROLLBACK_MIGRATION_NAMES
        or (expected_migrations is not None and recorded_migrations != expected_migrations)
        or (
            expected_operator_run_id is not None
            and manifest.get("operator_run_id") != expected_operator_run_id
        )
        or manifest.get("backup_sha256") != _sha256(backup)
    ):
        raise RuntimeError("backup provenance manifest is invalid")
    expected_database = Path(str(manifest.get("source_database", "")))
    if expected_database != database.resolve(strict=True):
        raise RuntimeError("backup target does not match provenance manifest")
    _validate_database(database)
    sidecars = [Path(f"{database}{suffix}") for suffix in ("-wal", "-shm")]
    try:
        with closing(sqlite3.connect(str(database), timeout=0)) as offline_probe:
            journal_mode = str(offline_probe.execute("PRAGMA journal_mode").fetchone()[0]).lower()
            if journal_mode == "wal":
                checkpoint = offline_probe.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()
                if int(checkpoint[0]) != 0:
                    raise RuntimeError("database rollback requires offline mode")
                switched = str(
                    offline_probe.execute("PRAGMA journal_mode=DELETE").fetchone()[0]
                ).lower()
                if switched != "delete":
                    raise RuntimeError("database rollback could not leave WAL mode")
            offline_probe.execute("BEGIN EXCLUSIVE")
            offline_probe.rollback()
    except sqlite3.OperationalError as exc:
        raise RuntimeError("database rollback requires offline mode") from exc

    active_sidecars = [path for path in sidecars if path.exists()]
    if active_sidecars:
        raise RuntimeError("database rollback requires offline mode without WAL/SHM sidecars")

    database.parent.mkdir(parents=True, exist_ok=True)
    temporary = database.with_name(f".{database.name}.rollback-{uuid4().hex}.tmp")
    try:
        shutil.copyfile(backup, temporary)
        _validate_database(temporary)
        if prepare_replacement is not None:
            prepare_replacement(temporary)
            _validate_database(temporary)
        temporary.replace(database)
    finally:
        temporary.unlink(missing_ok=True)
    _validate_database(database)
    return database


def status(*, db_path: str | Path = DB_PATH) -> dict[str, object]:
    """Return migration state without modifying the database."""

    database = Path(db_path)
    _validate_database(database)
    with closing(_connect(database, read_only=True)) as connection:
        taskpack_exists = _table_exists(connection, "kb_taskpacks")
        pending = _taskpack_migrations_pending(connection)
        recorded = _recorded_taskpack_migrations(connection)
    return {
        "total": len(TASKPACK_MIGRATIONS) if taskpack_exists else 0,
        "applied": sum(version in recorded for version in TASKPACK_MIGRATIONS),
        "pending": [
            f"{version:03d}_{name}"
            for version, name in TASKPACK_MIGRATIONS.items()
            if name in pending
        ],
        "applied_list": [
            f"{version:03d}_{name}"
            for version, name in TASKPACK_MIGRATIONS.items()
            if version in recorded
        ],
    }
