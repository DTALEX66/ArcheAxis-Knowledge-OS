"""AXW-094B: verifiable backup, validation and restorable recovery.

A backup is a self-describing directory snapshot of an exchange export
(or any asset tree): every file is copied with its sha256 recorded in a
``backup-manifest.json``. Restore supports:

- ``dry_run=True``: rehearses the restore against the current target,
  reporting what would change, without touching anything;
- actual restore with atomic per-file writes and a restore receipt;
- explicit failure semantics for corruption (hash mismatch), partial
  backups (missing manifest or missing files) and schema/version
  incompatibility.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BACKUP_SCHEMA_VERSION = "v1"
_BACKUP_MANIFEST = "backup-manifest.json"


class BackupError(ValueError):
    """Raised for corruption, partial backups, or incompatible versions."""


@dataclass(frozen=True)
class BackupEntry:
    relative_path: str
    sha256: str
    size: int

    def to_dict(self) -> dict[str, Any]:
        return {"path": self.relative_path, "sha256": self.sha256, "size": self.size}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BackupEntry:
        return cls(
            relative_path=str(data["path"]),
            sha256=str(data["sha256"]),
            size=int(data["size"]),
        )


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _iter_files(root: Path) -> list[Path]:
    return sorted(p for p in root.rglob("*") if p.is_file())


def create_backup(*, source: str | Path, backup_dir: str | Path) -> dict[str, Any]:
    """Snapshot ``source`` into ``backup_dir`` with a verifiable manifest."""
    source = Path(source)
    backup_dir = Path(backup_dir)
    if not source.is_dir():
        raise BackupError(f"backup source is not a directory: {source}")
    if backup_dir.exists() and any(backup_dir.iterdir()):
        raise BackupError(
            f"backup destination is not empty: {backup_dir} "
            "(refusing to mix snapshots; use a fresh directory)"
        )
    backup_dir.mkdir(parents=True, exist_ok=True)

    entries: list[BackupEntry] = []
    for file_path in _iter_files(source):
        relative = file_path.relative_to(source).as_posix()
        digest = _sha256_file(file_path)
        target = backup_dir / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(file_path, target)
        entries.append(BackupEntry(relative_path=relative, sha256=digest, size=file_path.stat().st_size))

    manifest: dict[str, Any] = {
        "schema_version": BACKUP_SCHEMA_VERSION,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "tool": "archeaxis-knowledge-os",
        "source_relpath": str(source.resolve()),
        "file_count": len(entries),
        "files": [entry.to_dict() for entry in entries],
    }
    manifest_path = backup_dir / _BACKUP_MANIFEST
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return manifest


def verify_backup(backup_dir: str | Path) -> dict[str, Any]:
    """Validate a backup: manifest present, every file present and unmodified.

    Raises ``BackupError`` with an explicit message for partial backups,
    corruption, or incompatible schema versions.
    """
    backup_dir = Path(backup_dir)
    manifest_path = backup_dir / _BACKUP_MANIFEST
    if not manifest_path.is_file():
        raise BackupError(
            f"backup verification failed: {_BACKUP_MANIFEST} missing "
            f"(partial or interrupted backup): {backup_dir}"
        )
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        raise BackupError(f"backup verification failed: unreadable manifest: {exc}") from exc

    if manifest.get("schema_version") != BACKUP_SCHEMA_VERSION:
        raise BackupError(
            "backup verification failed: incompatible backup version "
            f"{manifest.get('schema_version')!r} (expected {BACKUP_SCHEMA_VERSION!r})"
        )

    failures: list[str] = []
    verified = 0
    for raw_entry in manifest.get("files", []):
        try:
            entry = BackupEntry.from_dict(raw_entry)
        except (KeyError, TypeError, ValueError) as exc:
            failures.append(f"invalid backup entry {raw_entry!r}: {exc}")
            continue
        target = backup_dir / entry.relative_path
        if not target.is_file():
            failures.append(f"missing backup file: {entry.relative_path}")
            continue
        if _sha256_file(target) != entry.sha256:
            failures.append(
                f"corrupted backup file: {entry.relative_path} "
                f"(sha256 mismatch)"
            )
            continue
        verified += 1

    if failures:
        raise BackupError(
            "backup verification failed:\n- " + "\n- ".join(failures[:20])
        )
    if verified != manifest.get("file_count"):
        raise BackupError(
            "backup verification failed: file_count mismatch "
            f"(manifest says {manifest.get('file_count')}, verified {verified})"
        )
    return {"manifest": manifest, "verified_files": verified}


def restore_backup(
    *,
    backup_dir: str | Path,
    target: str | Path,
    dry_run: bool = True,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Restore a verified backup into ``target``.

    With ``dry_run=True`` (default) nothing is written; the plan is
    returned so recovery can be rehearsed first. With ``dry_run=False``
    files are restored atomically (write to temp, then replace) and a
    receipt with restored hashes is returned.
    """
    backup_dir = Path(backup_dir)
    target = Path(target)
    result = verify_backup(backup_dir)
    manifest = result["manifest"]

    plan: list[dict[str, Any]] = []
    for raw_entry in manifest["files"]:
        entry = BackupEntry.from_dict(raw_entry)
        destination = target / entry.relative_path
        state = "create" if not destination.exists() else "overwrite"
        if state == "overwrite" and not overwrite:
            raise BackupError(
                f"restore refused: {entry.relative_path} already exists at {target} "
                "(pass overwrite=True to replace)"
            )
        plan.append(
            {
                "path": entry.relative_path,
                "sha256": entry.sha256,
                "action": state,
            }
        )

    if dry_run:
        return {
            "dry_run": True,
            "restored_files": 0,
            "plan": plan,
            "source_backup": str(backup_dir.resolve()),
        }

    target.mkdir(parents=True, exist_ok=True)
    restored: list[dict[str, Any]] = []
    for entry in (BackupEntry.from_dict(raw) for raw in manifest["files"]):
        source_file = backup_dir / entry.relative_path
        destination = target / entry.relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        temp = destination.with_name(destination.name + ".restore-tmp")
        shutil.copy2(source_file, temp)
        temp.replace(destination)
        restored.append(
            {"path": entry.relative_path, "sha256": entry.sha256, "action": "restored"}
        )

    receipt: dict[str, Any] = {
        "schema_version": BACKUP_SCHEMA_VERSION,
        "restored_at": datetime.now(timezone.utc).isoformat(),
        "restored_files": len(restored),
        "files": restored,
    }
    (target / "restore-receipt.json").write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return {"dry_run": False, "restored_files": len(restored), "plan": plan, "receipt": receipt}
