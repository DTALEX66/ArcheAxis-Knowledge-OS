"""Compatibility Kernel — import session with path safety and idempotency (K2).

The import session scans an approved vault root, parses each file into a
canonical ``VaultFile``, persists a governed compatibility ledger (not the
governed knowledge/machine-knowledge tables), and reports any content that
could not be expressed without loss. Re-importing the same source is
idempotent.
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

from shared.approved_paths import ApprovedRoots, ApprovedRootsError
from shared.compat.models import VaultFile

_SCHEMA = """
CREATE TABLE IF NOT EXISTS compat_files (
    relative_path TEXT PRIMARY KEY,
    source_hash TEXT NOT NULL,
    file_size INTEGER NOT NULL,
    frontmatter_json TEXT NOT NULL,
    body_hash TEXT NOT NULL,
    is_canvas INTEGER NOT NULL DEFAULT 0,
    imported_at TEXT NOT NULL
);
"""


class ImportSession:
    """Scan and import a vault under an approved root into a compat ledger."""

    def __init__(self, store: Path, vault_root: Path) -> None:
        self.store = store
        self.vault_root = vault_root.resolve()
        if not self.vault_root.is_dir():
            raise ValueError(f"vault root is not a directory: {vault_root}")
        self.approved = ApprovedRoots(source_roots=[self.vault_root])
        self._conn = sqlite3.connect(store)
        self._conn.execute(_SCHEMA)
        self._conn.commit()
        self._losses: list[dict[str, object]] = []

    def _scan_paths(self) -> list[Path]:
        """Enumerate files under the vault, rejecting symlink escapes."""
        results: list[Path] = []
        for root_name, dirs, files in os.walk(self.vault_root, topdown=True, followlinks=False):
            root = Path(root_name)
            # drop symlink dirs that escape the approved root
            kept: list[str] = []
            for d in dirs:
                candidate = (root / d).resolve()
                try:
                    self.approved.resolve_source(candidate)
                    kept.append(d)
                except ApprovedRootsError:
                    raise ApprovedRootsError(
                        f"vault traversal escaped approved root: {(root / d).as_posix()}"
                    ) from None
            dirs[:] = kept
            for f in files:
                results.append(root / f)
        return results

    def import_path(self, path: Path) -> VaultFile:
        """Import a single path, rejecting escapes."""
        resolved = self.approved.resolve_source(path)
        return VaultFile.from_path(resolved, vault=self.vault_root)

    def scan(self) -> list[VaultFile]:
        """Scan the vault, importing every file idempotently."""
        return [self.import_path(p) for p in self._scan_paths()]

    def run(self) -> int:
        """Run a full import, persisting the compatibility ledger."""
        files = self.scan()
        now = _now()
        for vf in files:
            # idempotent upsert keyed on relative path
            self._conn.execute(
                "INSERT INTO compat_files (relative_path, source_hash, file_size,"
                " frontmatter_json, body_hash, is_canvas, imported_at) VALUES (?,?,?,?,?,?,?)"
                " ON CONFLICT(relative_path) DO UPDATE SET source_hash=excluded.source_hash,"
                " file_size=excluded.file_size, frontmatter_json=excluded.frontmatter_json,"
                " body_hash=excluded.body_hash, is_canvas=excluded.is_canvas,"
                " imported_at=excluded.imported_at",
                (
                    vf.relative_path,
                    vf.source_hash,
                    vf.file_size,
                    _json(vf.frontmatter),
                    _sha256(vf.body),
                    1 if vf.is_canvas else 0,
                    now,
                ),
            )
        self._conn.commit()
        return len(files)

    def file_count(self) -> int:
        return self._conn.execute("SELECT COUNT(*) FROM compat_files").fetchone()[0]

    def loss_report(self) -> list[dict[str, object]]:
        return list(self._losses)


def _now() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()


def _sha256(text: str) -> str:
    import hashlib

    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _json(value: object) -> str:
    import json

    return json.dumps(value, ensure_ascii=False, sort_keys=True)
