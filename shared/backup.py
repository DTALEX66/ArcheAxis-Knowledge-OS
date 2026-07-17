#!/usr/bin/env python3
"""Manifest-bound SQLite backup and offline restore utilities."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import sys
from collections.abc import Iterator
from contextlib import closing, contextmanager
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

from shared.config import config, resolve_runtime_path

DB_PATH = resolve_runtime_path(str(config.get("database.path", "data/cognitive_os.sqlite")))
BACKUP_DIR = resolve_runtime_path(str(config.get("database.backup_dir", "data/backups")))

MANIFEST_VERSION = 1
BACKUP_KIND = "cognitive-os-sqlite-backup"
CANDIDATE_KIND = "cognitive-os-sqlite-restore-candidate"
_RUNTIME_LOCK_FD: int | None = None
REQUIRED_TABLES = frozenset(
    {
        "kb_documents",
        "kb_cards",
        "kb_taskpacks",
        "ir_research_notes",
        "ir_daily_briefs",
        "schema_migrations",
        "core_objects",
    }
)
INVARIANT_TABLES = (
    "core_objects",
    "kb_documents",
    "kb_cards",
    "kb_taskpacks",
    "ir_research_notes",
    "ir_daily_briefs",
)


def _sqlite_uri(path: Path) -> str:
    return f"{path.resolve().as_uri()}?mode=ro"


def _manifest_path(path: Path) -> Path:
    return path.with_suffix(f"{path.suffix}.manifest.json")


def _runtime_lock_path(database: Path | None = None) -> Path:
    target = (database or DB_PATH).resolve()
    return target.with_name(f".{target.name}.runtime.lock")


def _volume_identity_path(database: Path | None = None) -> Path:
    target = (database or DB_PATH).resolve()
    return target.with_name(".cognitive-volume-id")


def _read_volume_identity(database: Path) -> str:
    path = _volume_identity_path(database)
    try:
        value = path.read_text(encoding="ascii").strip()
        parsed = UUID(value)
    except (OSError, ValueError) as exc:
        raise RuntimeError(f"database volume identity is missing or invalid: {path}") from exc
    if str(parsed) != value:
        raise RuntimeError(f"database volume identity is not canonical: {path}")
    return value


def ensure_volume_identity(database: Path) -> str:
    path = _volume_identity_path(database)
    path.parent.mkdir(parents=True, exist_ok=True)
    value = str(uuid4())
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        return _read_volume_identity(database)
    try:
        os.write(fd, value.encode("ascii"))
        os.fsync(fd)
    finally:
        os.close(fd)
    return _read_volume_identity(database)


def _lock_file(fd: int, *, nonblocking: bool) -> None:
    if os.name == "posix":
        import fcntl

        flags = fcntl.LOCK_EX | (fcntl.LOCK_NB if nonblocking else 0)
        fcntl.flock(fd, flags)
        return
    if os.name == "nt":
        import msvcrt

        os.lseek(fd, 0, os.SEEK_SET)
        mode = msvcrt.LK_NBLCK if nonblocking else msvcrt.LK_LOCK
        msvcrt.locking(fd, mode, 1)
        return
    raise RuntimeError(f"runtime lock is unsupported on platform: {os.name}")


def _unlock_file(fd: int) -> None:
    if os.name == "posix":
        import fcntl

        fcntl.flock(fd, fcntl.LOCK_UN)
    elif os.name == "nt":
        import msvcrt

        os.lseek(fd, 0, os.SEEK_SET)
        msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)


def _open_runtime_lock(database: Path, *, inheritable: bool = False) -> int:
    path = _runtime_lock_path(database)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_RDWR | os.O_CREAT, 0o600)
    try:
        if os.fstat(fd).st_size == 0:
            os.write(fd, b"1")
        _lock_file(fd, nonblocking=True)
        os.set_inheritable(fd, inheritable)
    except OSError as exc:
        os.close(fd)
        raise RuntimeError("database operator requires the app to be offline") from exc
    except Exception:
        os.close(fd)
        raise
    return fd


def acquire_runtime_lock() -> None:
    """Hold the single-runtime lease across the Uvicorn exec boundary."""
    global _RUNTIME_LOCK_FD
    if _RUNTIME_LOCK_FD is not None:
        return
    _RUNTIME_LOCK_FD = _open_runtime_lock(DB_PATH, inheritable=True)


def release_runtime_lock() -> None:
    """Release the runtime lease after a failed launch or in an isolated test."""
    global _RUNTIME_LOCK_FD
    if _RUNTIME_LOCK_FD is None:
        return
    fd, _RUNTIME_LOCK_FD = _RUNTIME_LOCK_FD, None
    try:
        _unlock_file(fd)
    finally:
        os.close(fd)


@contextmanager
def runtime_lease(database: Path | None = None) -> Iterator[None]:
    """Hold the target database operator lease for an entire one-shot operation."""
    fd = _open_runtime_lock((database or DB_PATH).resolve())
    try:
        yield
    finally:
        try:
            _unlock_file(fd)
        finally:
            os.close(fd)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sqlite_backup(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(_sqlite_uri(source), uri=True)) as src, closing(
        sqlite3.connect(str(destination))
    ) as dst:
        src.backup(dst)


def _migration_ledger(connection: sqlite3.Connection) -> list[dict[str, object]]:
    return [
        {
            "version": int(row["version"]),
            "name": str(row["name"]),
            "applied_at": str(row["applied_at"]),
        }
        for row in connection.execute(
            "SELECT version, name, applied_at FROM schema_migrations ORDER BY version"
        ).fetchall()
    ]


def _validate_sqlite_database(path: Path) -> dict[str, object]:
    if not path.is_file():
        raise FileNotFoundError(f"SQLite database not found: {path}")
    try:
        with closing(sqlite3.connect(_sqlite_uri(path), uri=True)) as connection:
            connection.row_factory = sqlite3.Row
            integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
            if integrity != "ok":
                raise RuntimeError(f"SQLite integrity check failed for {path}: {integrity}")
            tables = {
                str(row["name"])
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type IN ('table', 'view')"
                ).fetchall()
            }
            missing = sorted(REQUIRED_TABLES - tables)
            if missing:
                raise RuntimeError(
                    f"SQLite backup invariants failed; missing tables: {', '.join(missing)}"
                )
            ledger = _migration_ledger(connection)
            counts = {
                table: int(connection.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0])
                for table in INVARIANT_TABLES
            }
    except sqlite3.Error as exc:
        raise RuntimeError(f"SQLite validation failed for {path}") from exc

    from shared import migration

    status = migration.status(db_path=path)
    if status.get("pending"):
        pending = ", ".join(str(item) for item in status["pending"])
        raise RuntimeError(f"SQLite backup invariants failed; pending migrations: {pending}")
    return {
        "sha256": _sha256(path),
        "size_bytes": path.stat().st_size,
        "schema_migrations": ledger,
        "migration_status": status,
        "domain_invariants": {
            "required_tables": sorted(REQUIRED_TABLES),
            "row_counts": counts,
        },
    }


def _write_manifest(path: Path, payload: dict[str, object]) -> Path:
    manifest = _manifest_path(path)
    temporary = manifest.with_suffix(f"{manifest.suffix}.{uuid4().hex}.tmp")
    try:
        temporary.write_text(
            json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        temporary.replace(manifest)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    return manifest


def _load_manifest(path: Path) -> dict[str, object]:
    manifest_path = _manifest_path(path)
    if not manifest_path.is_file():
        raise RuntimeError(f"backup manifest is missing: {manifest_path}")
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"backup manifest is invalid: {manifest_path}") from exc
    if not isinstance(data, dict):
        raise RuntimeError(f"backup manifest is invalid: {manifest_path}")
    return data


def _verify_manifest(path: Path, *, kind: str) -> dict[str, object]:
    manifest = _load_manifest(path)
    metadata = _validate_sqlite_database(path)
    if manifest.get("manifest_version") != MANIFEST_VERSION or manifest.get("kind") != kind:
        raise RuntimeError("backup manifest has unexpected type or version")
    if kind == BACKUP_KIND:
        file_record = manifest.get("backup")
    else:
        file_record = manifest.get("candidate")
    if not isinstance(file_record, dict):
        raise RuntimeError("backup manifest is missing file identity")
    if file_record.get("sha256") != metadata["sha256"]:
        raise RuntimeError("backup manifest does not match the SQLite file hash")
    if file_record.get("size_bytes") != metadata["size_bytes"]:
        raise RuntimeError("backup manifest does not match the SQLite file size")
    if manifest.get("schema_migrations") != metadata["schema_migrations"]:
        raise RuntimeError("backup manifest does not match the migration ledger")
    if manifest.get("domain_invariants") != metadata["domain_invariants"]:
        raise RuntimeError("backup manifest does not match domain invariants")
    return manifest


def backup() -> str:
    """Create a verified SQLite backup and manifest."""
    volume_identity = ensure_volume_identity(DB_PATH)
    source_metadata = _validate_sqlite_database(DB_PATH)
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")
    final = BACKUP_DIR / f"cognitive_os_{timestamp}.sqlite"
    temporary = BACKUP_DIR / f".{final.name}.{uuid4().hex}.tmp"
    try:
        _sqlite_backup(DB_PATH, temporary)
        backup_metadata = _validate_sqlite_database(temporary)
        temporary.replace(final)
        manifest = {
            "manifest_version": MANIFEST_VERSION,
            "kind": BACKUP_KIND,
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "source": {
                "path": str(DB_PATH.resolve()),
                "volume_identity": volume_identity,
                "sha256_at_backup_start": source_metadata["sha256"],
                "size_bytes_at_backup_start": source_metadata["size_bytes"],
            },
            "backup": {
                "path": str(final.resolve()),
                "sha256": backup_metadata["sha256"],
                "size_bytes": backup_metadata["size_bytes"],
            },
            "schema_migrations": backup_metadata["schema_migrations"],
            "migration_status": backup_metadata["migration_status"],
            "domain_invariants": backup_metadata["domain_invariants"],
        }
        _write_manifest(final, manifest)
        _verify_manifest(final, kind=BACKUP_KIND)
    except Exception:
        temporary.unlink(missing_ok=True)
        final.unlink(missing_ok=True)
        _manifest_path(final).unlink(missing_ok=True)
        raise
    return str(final)


def restore(backup_path: str) -> str:
    """Stage a restore candidate by verifying and copying an exact backup."""
    backup_file = Path(backup_path)
    backup_manifest = _verify_manifest(backup_file, kind=BACKUP_KIND)
    backup_hash = str(backup_manifest["backup"]["sha256"])  # type: ignore[index]
    candidate_dir = BACKUP_DIR / "restore-candidates"
    candidate_dir.mkdir(parents=True, exist_ok=True)
    final = candidate_dir / f"restore_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S_%fZ')}.sqlite"
    temporary = candidate_dir / f".{final.name}.{uuid4().hex}.tmp"
    try:
        shutil.copyfile(backup_file, temporary)
        candidate_metadata = _validate_sqlite_database(temporary)
        if candidate_metadata["sha256"] != backup_hash:
            raise RuntimeError("restore candidate does not exactly match the backup hash")
        temporary.replace(final)
        manifest = {
            "manifest_version": MANIFEST_VERSION,
            "kind": CANDIDATE_KIND,
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "source_backup": {
                "path": str(backup_file.resolve()),
                "sha256": backup_hash,
            },
            "target_database": str(backup_manifest["source"]["path"]),  # type: ignore[index]
            "target_volume_identity": str(
                backup_manifest["source"]["volume_identity"]  # type: ignore[index]
            ),
            "candidate": {
                "path": str(final.resolve()),
                "sha256": candidate_metadata["sha256"],
                "size_bytes": candidate_metadata["size_bytes"],
            },
            "schema_migrations": candidate_metadata["schema_migrations"],
            "migration_status": candidate_metadata["migration_status"],
            "domain_invariants": candidate_metadata["domain_invariants"],
        }
        _write_manifest(final, manifest)
        _verify_manifest(final, kind=CANDIDATE_KIND)
    except Exception:
        temporary.unlink(missing_ok=True)
        final.unlink(missing_ok=True)
        _manifest_path(final).unlink(missing_ok=True)
        raise
    return str(final)


def _require_offline_database(database: Path) -> None:
    if not database.is_file():
        raise FileNotFoundError(f"SQLite database not found: {database}")
    sidecars = [Path(f"{database}{suffix}") for suffix in ("-wal", "-shm")]
    try:
        with closing(sqlite3.connect(str(database), timeout=0.0)) as connection:
            connection.execute("PRAGMA busy_timeout=0")
            journal_mode = str(connection.execute("PRAGMA journal_mode").fetchone()[0]).lower()
            if journal_mode == "wal":
                checkpoint = connection.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()
                if int(checkpoint[0]) != 0:
                    raise RuntimeError("restore activation requires the app to be offline")
            connection.execute("BEGIN EXCLUSIVE")
            connection.rollback()
    except sqlite3.OperationalError as exc:
        raise RuntimeError("restore activation requires the app to be offline") from exc
    for sidecar in sidecars:
        try:
            sidecar.unlink(missing_ok=True)
        except PermissionError:
            if sidecar.name.endswith("-wal") and sidecar.exists() and sidecar.stat().st_size != 0:
                raise


def _activate_restore_locked(candidate: Path, candidate_hash: str, database: Path) -> str:
    _require_offline_database(database)
    live_metadata = _validate_sqlite_database(database)
    compensation = database.with_name(f".{database.name}.pre_restore_{uuid4().hex}.sqlite")
    compensation_replacement = database.with_name(
        f".{database.name}.compensation_{uuid4().hex}.tmp"
    )
    replacement = database.with_name(f".{database.name}.restore_{uuid4().hex}.tmp")
    live_replaced = False
    preserve_compensation = False
    try:
        shutil.copyfile(database, compensation)
        compensation_metadata = _validate_sqlite_database(compensation)
        if compensation_metadata["sha256"] != live_metadata["sha256"]:
            raise RuntimeError("restore compensation copy does not match live database")
        shutil.copyfile(candidate, replacement)
        replacement_metadata = _validate_sqlite_database(replacement)
        if replacement_metadata["sha256"] != candidate_hash:
            raise RuntimeError("restore replacement does not match candidate manifest")
        replacement.replace(database)
        live_replaced = True
        restored_metadata = _validate_sqlite_database(database)
        if restored_metadata["sha256"] != candidate_hash:
            raise RuntimeError("post-restore database does not match candidate manifest")
    except Exception:
        if not live_replaced:
            _validate_sqlite_database(database)
            raise
        try:
            if compensation.is_file():
                shutil.copyfile(compensation, compensation_replacement)
                recovery_metadata = _validate_sqlite_database(compensation_replacement)
                if recovery_metadata["sha256"] != compensation_metadata["sha256"]:
                    raise RuntimeError("restore compensation replacement does not match recovery copy")
                compensation_replacement.replace(database)
                _validate_sqlite_database(database)
        except Exception as compensation_error:
            preserve_compensation = True
            raise RuntimeError(
                "restore activation failed; compensation could not be applied and the verified "
                f"recovery copy was preserved at {compensation}"
            ) from compensation_error
        raise
    finally:
        replacement.unlink(missing_ok=True)
        compensation_replacement.unlink(missing_ok=True)
        if not preserve_compensation:
            compensation.unlink(missing_ok=True)
    return str(database)


def activate_restore(candidate_path: str) -> str:
    """Atomically replace the live DB while holding its target-scoped operator lease."""
    candidate = Path(candidate_path)
    candidate_manifest = _verify_manifest(candidate, kind=CANDIDATE_KIND)
    candidate_hash = str(candidate_manifest["candidate"]["sha256"])  # type: ignore[index]
    database = DB_PATH
    if candidate_manifest.get("target_database") != str(database.resolve()):
        raise RuntimeError("restore candidate is bound to a different target database")
    if candidate_manifest.get("target_volume_identity") != _read_volume_identity(database):
        raise RuntimeError("restore candidate is bound to a different database volume")
    with runtime_lease(database):
        return _activate_restore_locked(candidate, candidate_hash, database)


def list_backups() -> list[str]:
    """List available backups, newest first."""
    if not BACKUP_DIR.exists():
        return []
    backups = sorted(BACKUP_DIR.glob("cognitive_os_*.sqlite"), reverse=True)
    return [str(path) for path in backups[:20]]


def auto_backup() -> dict:
    """Auto-backup with size check; skips tiny or absent databases."""
    if DB_PATH.exists() and DB_PATH.stat().st_size > 10240:
        path = backup()
        all_backups = list_backups()
        for old in all_backups[10:]:
            old_path = Path(old)
            old_path.unlink(missing_ok=True)
            _manifest_path(old_path).unlink(missing_ok=True)
        return {"backup": path, "total_backups": min(len(all_backups), 10)}
    return {"skipped": "DB too small for backup"}


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "backup"
    if cmd == "backup":
        print(backup())
    elif cmd == "restore" and len(sys.argv) > 2:
        print(restore(sys.argv[2]))
    elif cmd == "activate" and len(sys.argv) > 2:
        print(activate_restore(sys.argv[2]))
    elif cmd == "list":
        for item in list_backups():
            print(item)
    elif cmd == "auto":
        print(auto_backup())
    else:
        print("Usage: backup|restore <file>|activate <candidate>|list|auto")
