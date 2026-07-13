from __future__ import annotations

import sqlite3
from pathlib import Path

from shared import backup as backup_module


def _create_database(path: Path, title: str) -> None:
    with sqlite3.connect(path) as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("CREATE TABLE kb_documents (id TEXT PRIMARY KEY, title TEXT NOT NULL)")
        conn.execute("INSERT INTO kb_documents VALUES ('doc-1', ?)", (title,))
        conn.commit()


def test_backup_and_restore_candidate_use_consistent_snapshots(monkeypatch, tmp_path):
    database = tmp_path / "runtime" / "cognitive.sqlite"
    database.parent.mkdir()
    backup_dir = tmp_path / "backups"
    _create_database(database, "before")
    monkeypatch.setattr(backup_module, "DB_PATH", database)
    monkeypatch.setattr(backup_module, "BACKUP_DIR", backup_dir)

    snapshot = Path(backup_module.backup())
    with sqlite3.connect(database) as conn:
        conn.execute("UPDATE kb_documents SET title='after' WHERE id='doc-1'")
        conn.commit()

    candidate = Path(backup_module.restore(str(snapshot)))
    with sqlite3.connect(database) as conn:
        assert conn.execute("SELECT title FROM kb_documents WHERE id='doc-1'").fetchone()[0] == "after"
    with sqlite3.connect(candidate) as conn:
        assert conn.execute("SELECT title FROM kb_documents WHERE id='doc-1'").fetchone()[0] == "before"
    assert candidate.parent == backup_dir / "restore-candidates"
