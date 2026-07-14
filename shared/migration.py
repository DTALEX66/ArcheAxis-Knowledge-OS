"""Transactional, backed-up SQLite migrations for Cognitive-Loop-OS.

Migrations are code-owned and shipped with the application. Runtime data directories
contain databases and backups only; they are never treated as a source of executable
migration SQL.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from shared.config import config, resolve_runtime_path

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


@dataclass(frozen=True)
class MigrationRun:
    """Evidence returned by one migration invocation."""

    applied: tuple[str, ...]
    backup_path: Path | None


def _connect(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(str(path))
    connection.row_factory = sqlite3.Row
    return connection


def _table_exists(connection: sqlite3.Connection, table: str) -> bool:
    return (
        connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
        ).fetchone()
        is not None
    )


def _applied_versions(connection: sqlite3.Connection) -> set[int]:
    if not _table_exists(connection, "schema_migrations"):
        return set()
    return {
        int(row["version"])
        for row in connection.execute("SELECT version FROM schema_migrations").fetchall()
    }


def _validate_database(path: Path) -> None:
    if not path.is_file():
        raise FileNotFoundError(f"SQLite database not found: {path}")
    with closing(_connect(path)) as connection:
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


def _create_backup(database: Path, backup_dir: Path) -> Path:
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
            "migration": TASKPACK_MIGRATION_NAME,
            "source_database": str(database.resolve(strict=True)),
            "backup_sha256": _sha256(destination),
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


def _validate_requires_review_schema(connection: sqlite3.Connection) -> None:
    columns = {
        str(row["name"]): row
        for row in connection.execute("PRAGMA table_info(kb_taskpacks)").fetchall()
    }
    column = columns.get("requires_review")
    if column is None:
        return
    table_row = connection.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='kb_taskpacks'"
    ).fetchone()
    compact_sql = "".join(str(table_row["sql"] or "").upper().split())
    invalid_values = connection.execute(
        "SELECT 1 FROM kb_taskpacks WHERE requires_review IS NULL "
        "OR requires_review NOT IN (0, 1) LIMIT 1"
    ).fetchone()
    if (
        int(column["notnull"]) != 1
        or str(column["dflt_value"]) != "1"
        or "CHECK(REQUIRES_REVIEWIN(0,1))" not in compact_sql
        or invalid_values is not None
    ):
        raise RuntimeError("kb_taskpacks requires_review schema is not fail closed")


def _taskpack_migration_pending(connection: sqlite3.Connection) -> bool:
    migration_row = None
    if _table_exists(connection, "schema_migrations"):
        migration_row = connection.execute(
            "SELECT name FROM schema_migrations WHERE version=?", (TASKPACK_MIGRATION_VERSION,)
        ).fetchone()
    if migration_row is not None and migration_row["name"] != TASKPACK_MIGRATION_NAME:
        raise RuntimeError(
            f"migration version {TASKPACK_MIGRATION_VERSION} name collision: "
            f"expected {TASKPACK_MIGRATION_NAME!r}, found {migration_row['name']!r}"
        )
    taskpack_exists = _table_exists(connection, "kb_taskpacks")
    if taskpack_exists:
        _validate_requires_review_schema(connection)
    if migration_row is not None:
        columns = (
            {
                str(row["name"])
                for row in connection.execute("PRAGMA table_info(kb_taskpacks)").fetchall()
            }
            if taskpack_exists
            else set()
        )
        missing_columns = {"context_id", "requires_review"} - columns
        if missing_columns:
            detail = ", ".join(sorted(missing_columns))
            raise RuntimeError(f"recorded migration schema mismatch; missing: {detail}")
        return False
    return taskpack_exists


def _apply_taskpack_migration(connection: sqlite3.Connection) -> None:
    columns = {
        str(row["name"])
        for row in connection.execute("PRAGMA table_info(kb_taskpacks)").fetchall()
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


def migrate(
    *, db_path: str | Path = DB_PATH, backup_dir: str | Path = BACKUP_DIR
) -> MigrationRun:
    """Apply pending migrations once, after creating a verified SQLite backup."""

    database = Path(db_path)
    backups = Path(backup_dir)
    _validate_database(database)

    backup_path: Path | None = None
    with closing(_connect(database)) as connection:
        try:
            connection.execute("BEGIN IMMEDIATE")
            if not _taskpack_migration_pending(connection):
                connection.commit()
                return MigrationRun(applied=(), backup_path=None)
            backup_path = _create_backup(database, backups)
            connection.execute(MIGRATIONS_TABLE)
            _apply_taskpack_migration(connection)
            connection.execute(
                "INSERT INTO schema_migrations(version, name) VALUES (?, ?)",
                (TASKPACK_MIGRATION_VERSION, TASKPACK_MIGRATION_NAME),
            )
            connection.commit()
        except Exception:
            connection.rollback()
            raise

    _validate_database(database)
    return MigrationRun(applied=(TASKPACK_MIGRATION_NAME,), backup_path=backup_path)


def rollback(*, backup_path: str | Path, db_path: str | Path = DB_PATH) -> Path:
    """Restore a migration backup while the runtime is offline.

    WAL/SHM sidecars indicate that the runtime may still own the database, so the
    operation fails closed instead of replacing a potentially active file.
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
    if (
        manifest.get("schema_version") != 1
        or manifest.get("migration") != TASKPACK_MIGRATION_NAME
        or manifest.get("backup_sha256") != _sha256(backup)
    ):
        raise RuntimeError("backup provenance manifest is invalid")
    expected_database = Path(str(manifest.get("source_database", "")))
    if expected_database != database.resolve(strict=True):
        raise RuntimeError("backup target does not match provenance manifest")
    _validate_database(database)
    sidecars = [Path(f"{database}{suffix}") for suffix in ("-wal", "-shm")]
    active_sidecars = [path for path in sidecars if path.exists()]
    if active_sidecars:
        raise RuntimeError("database rollback requires offline mode without WAL/SHM sidecars")

    try:
        with closing(sqlite3.connect(str(database), timeout=0)) as offline_probe:
            offline_probe.execute("BEGIN EXCLUSIVE")
            offline_probe.rollback()
    except sqlite3.OperationalError as exc:
        raise RuntimeError("database rollback requires offline mode") from exc

    database.parent.mkdir(parents=True, exist_ok=True)
    temporary = database.with_name(f".{database.name}.rollback-{uuid4().hex}.tmp")
    try:
        shutil.copyfile(backup, temporary)
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
    with closing(_connect(database)) as connection:
        applied = _applied_versions(connection)
        taskpack_exists = _table_exists(connection, "kb_taskpacks")
        pending = _taskpack_migration_pending(connection)
    is_applied = TASKPACK_MIGRATION_VERSION in applied
    return {
        "total": 1 if taskpack_exists else 0,
        "applied": 1 if taskpack_exists and is_applied else 0,
        "pending": []
        if not pending
        else [f"{TASKPACK_MIGRATION_VERSION:03d}_{TASKPACK_MIGRATION_NAME}"],
        "applied_list": [f"{TASKPACK_MIGRATION_VERSION:03d}_{TASKPACK_MIGRATION_NAME}"]
        if taskpack_exists and is_applied
        else [],
    }
