"""Compatibility Kernel — revision log and rollback (K2).

Writes to vault files are revisioned (prior content snapshotted in a governed
ledger) so a write can be rolled back to the exact prior content. This replaces
the previous unsafe direct ``Path.write_text`` overwrite used by the legacy
Obsidian projection path.
"""

from __future__ import annotations

import os
import sqlite3
import tempfile
from pathlib import Path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS compat_revisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    relative_path TEXT NOT NULL,
    prior_hash TEXT NOT NULL,
    prior_content TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""


class RevisionConflictError(RuntimeError):
    """Raised when an external edit makes a revision write unsafe."""


class RevisionLog:
    """Revisioned writes with rollback to prior content."""

    def __init__(self, store: Path, vault_root: Path) -> None:
        self.store = store
        self.vault_root = vault_root.resolve()
        self._conn = sqlite3.connect(store)
        self._conn.execute(_SCHEMA)
        self._conn.commit()

    def record(self, path: Path, content: str, *, expected_hash: str | None = None) -> None:
        """Record the prior content, then write the new content atomically.

        The prior content is snapshotted into the revision ledger before the
        new content is written, enabling rollback.
        """
        resolved = path.resolve()
        try:
            rel = resolved.relative_to(self.vault_root).as_posix()
        except ValueError as exc:
            raise RevisionConflictError("revision path escaped approved vault root") from exc
        prior = resolved.read_text(encoding="utf-8") if resolved.exists() else ""
        current_hash = _sha256(prior)
        if expected_hash is not None and current_hash != expected_hash:
            raise RevisionConflictError("expected hash does not match current file")
        now = _now()
        self._conn.execute(
            "INSERT INTO compat_revisions (relative_path, prior_hash, prior_content,"
            " created_at) VALUES (?,?,?,?)",
            (rel, _sha256(prior), prior, now),
        )
        self._conn.commit()
        # atomic write via temp + rename
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=resolved.parent, delete=False
        ) as handle:
            handle.write(content)
            tmp_name = handle.name
        os.replace(tmp_name, resolved)

    def rollback(self, path: Path, *, expected_hash: str | None = None) -> None:
        """Restore the most recent prior content for a path."""
        resolved = path.resolve()
        try:
            rel = resolved.relative_to(self.vault_root).as_posix()
        except ValueError as exc:
            raise RevisionConflictError("rollback path escaped approved vault root") from exc
        row = self._conn.execute(
            "SELECT prior_content FROM compat_revisions WHERE relative_path=? ORDER BY id DESC LIMIT 1",
            (rel,),
        ).fetchone()
        if row is None:
            return
        current = resolved.read_text(encoding="utf-8") if resolved.exists() else ""
        if expected_hash is not None and _sha256(current) != expected_hash:
            raise RevisionConflictError("expected hash does not match current file")
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=resolved.parent, delete=False
        ) as handle:
            handle.write(row[0])
            tmp_name = handle.name
        os.replace(tmp_name, resolved)


def _now() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()


def _sha256(text: str) -> str:
    import hashlib

    return hashlib.sha256(text.encode("utf-8")).hexdigest()
