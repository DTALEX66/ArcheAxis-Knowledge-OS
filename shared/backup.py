#!/usr/bin/env python3
"""Database backup + restore utility for Cognitive-Loop-OS.

Usage:
    python shared/backup.py backup              # Create timestamped backup
    python shared/backup.py restore <file>      # Restore from backup
    python shared/backup.py list                # List available backups
"""

from __future__ import annotations

import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = _PROJECT_ROOT / "data" / "cognitive_os.sqlite"
BACKUP_DIR = _PROJECT_ROOT / "data" / "backups"


def backup() -> str:
    """Create a timestamped backup of the SQLite database.

    Returns the backup file path.
    """
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / f"cognitive_os_{timestamp}.sqlite"

    # Use SQLite backup API for safe copy
    src = sqlite3.connect(str(DB_PATH))
    dst = sqlite3.connect(str(backup_path))
    src.backup(dst)
    src.close()
    dst.close()

    # Verify
    if backup_path.stat().st_size > 0:
        return str(backup_path)
    raise RuntimeError("Backup failed — empty file")


def restore(backup_path: str) -> str:
    """Restore database from a backup file.

    Creates a safety copy of the current DB before restoring.
    """
    src = Path(backup_path)
    if not src.exists():
        raise FileNotFoundError(f"Backup not found: {backup_path}")

    # Safety: backup current DB first
    safety = BACKUP_DIR / f"pre_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sqlite"
    if DB_PATH.exists():
        shutil.copy2(DB_PATH, safety)

    # Restore
    shutil.copy2(src, DB_PATH)

    # Verify
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("SELECT COUNT(*) FROM kb_documents")
    conn.close()

    return f"Restored from {backup_path} (safety copy at {safety})"


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
