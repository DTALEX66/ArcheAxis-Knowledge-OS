#!/usr/bin/env python3
"""Database backup + restore utility for Cognitive-Loop-OS.

Usage:
    python shared/backup.py backup              # Create timestamped backup
    python shared/backup.py restore <file>      # Stage validated offline restore candidate
    python shared/backup.py list                # List available backups
"""

from __future__ import annotations

import sqlite3
import sys
from contextlib import closing
from datetime import datetime
from pathlib import Path

from shared.config import config, resolve_runtime_path

DB_PATH = resolve_runtime_path(str(config.get("database.path", "data/cognitive_os.sqlite")))
BACKUP_DIR = resolve_runtime_path(str(config.get("database.backup_dir", "data/backups")))



def _sqlite_backup(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(str(source))) as src, closing(sqlite3.connect(str(destination))) as dst:
        src.backup(dst)


def _validate_sqlite_backup(path: Path) -> None:
    with closing(sqlite3.connect(str(path))) as conn:
        if conn.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise RuntimeError(f"Invalid SQLite backup: {path}")
        conn.execute("SELECT COUNT(*) FROM kb_documents")


def backup() -> str:
    """Create a timestamped backup of the SQLite database.

    Returns the backup file path.
    """
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / f"cognitive_os_{timestamp}.sqlite"

    # Use SQLite backup API for safe copy
    _sqlite_backup(DB_PATH, backup_path)
    _validate_sqlite_backup(backup_path)

    # Verify
    if backup_path.stat().st_size > 0:
        return str(backup_path)
    raise RuntimeError("Backup failed — empty file")


def restore(backup_path: str) -> str:
    """Stage a validated restore candidate without touching the live database.

    Activating a candidate is intentionally an offline operator action: stop all
    services and workers, then replace the database outside this runtime.
    """
    src = Path(backup_path)
    if not src.exists():
        raise FileNotFoundError(f"Backup not found: {backup_path}")
    _validate_sqlite_backup(src)
    candidate_dir = BACKUP_DIR / "restore-candidates"
    candidate = candidate_dir / f"restore_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.sqlite"
    _sqlite_backup(src, candidate)
    _validate_sqlite_backup(candidate)
    return str(candidate)


def list_backups() -> list[str]:
    """List available backup files, newest first."""
    if not BACKUP_DIR.exists():
        return []
    backups = sorted(BACKUP_DIR.glob("cognitive_os_*.sqlite"), reverse=True)
    return [str(b) for b in backups[:20]]


def auto_backup() -> dict:
    """Auto-backup with size check — skips if DB < 10KB."""
    if DB_PATH.exists() and DB_PATH.stat().st_size > 10240:
        path = backup()
        # Cleanup old backups (keep last 10)
        all_backups = list_backups()
        for old in all_backups[10:]:
            Path(old).unlink(missing_ok=True)
        return {"backup": path, "total_backups": min(len(all_backups), 10)}
    return {"skipped": "DB too small for backup"}


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "backup"
    if cmd == "backup":
        print(backup())
    elif cmd == "restore" and len(sys.argv) > 2:
        print(restore(sys.argv[2]))
    elif cmd == "list":
        for b in list_backups():
            print(b)
    elif cmd == "auto":
        print(auto_backup())
    else:
        print("Usage: backup|restore <file>|list|auto")
