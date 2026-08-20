"""Unified version manifest for all derived indexes (FTS5, vector, graph, evidence).

Tracks version, sha256 fingerprint, row count, and timestamp per index kind.
Enables restart readback: after a process restart, the manifest can verify
that each index matches its last-recorded fingerprint.

Usage::

    from shared.index_manifest import IndexManifest

    manifest = IndexManifest("data/archeaxis.sqlite")
    manifest.ensure_table()

    # Record an index after rebuild
    manifest.record("fts", "kb_documents_fts", sha256="...", row_count=5)

    # Verify at restart
    entry = manifest.get("fts", "kb_documents_fts")
    if entry and entry.sha256 == current_fingerprint["sha256"]:
        pass  # index is still valid
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class IndexManifestEntry:
    """One recorded entry in the index version manifest."""

    kind: str  # "fts" | "vector" | "graph" | "evidence"
    name: str  # e.g. "kb_documents_fts", "vec_embeddings", "default"
    version: int  # monotonically increasing version
    sha256: str  # deterministic fingerprint of the index contents
    row_count: int  # number of indexed records
    updated_at: str  # ISO-8601 timestamp
    metadata_json: str = "{}"  # extra key-value pairs as JSON


class IndexManifest:
    """Persistent version manifest for derived indexes.

    Uses a shared SQLite database. Each index kind+name pair has exactly
    one active manifest row, replaced on every record() call.
    """

    TABLE = "index_manifest"
    CREATE_SQL = (
        f"CREATE TABLE IF NOT EXISTS {TABLE} ("
        "  kind TEXT NOT NULL,"
        "  name TEXT NOT NULL,"
        "  version INTEGER NOT NULL DEFAULT 1,"
        "  sha256 TEXT NOT NULL,"
        "  row_count INTEGER NOT NULL DEFAULT 0,"
        "  updated_at TEXT NOT NULL,"
        "  metadata_json TEXT NOT NULL DEFAULT '{}',"
        "  PRIMARY KEY (kind, name)"
        ")"
    )

    SUPPORTED_KINDS = frozenset({"fts", "vector", "graph", "evidence"})

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = str(db_path)

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def ensure_table(self) -> None:
        """Create the manifest table if it does not exist."""
        with self._conn() as conn:
            conn.execute(self.CREATE_SQL)
            conn.commit()

    # ── CRUD ──────────────────────────────────────────────────────────────

    def record(
        self,
        kind: str,
        name: str,
        sha256: str,
        row_count: int,
        metadata: dict[str, Any] | None = None,
    ) -> IndexManifestEntry:
        """Insert or replace the manifest entry for one index."""
        if kind not in self.SUPPORTED_KINDS:
            raise ValueError(f"unsupported index kind: {kind!r}")
        self.ensure_table()
        now = datetime.now(timezone.utc).isoformat()
        meta = json.dumps(metadata or {}, ensure_ascii=False)
        with self._conn() as conn:
            existing = conn.execute(
                f"SELECT version FROM {self.TABLE} WHERE kind=? AND name=?",
                (kind, name),
            ).fetchone()
            version = (existing["version"] + 1) if existing else 1
            conn.execute(
                f"INSERT OR REPLACE INTO {self.TABLE} "
                f"(kind, name, version, sha256, row_count, updated_at, metadata_json) "
                f"VALUES (?, ?, ?, ?, ?, ?, ?)",
                (kind, name, version, sha256, row_count, now, meta),
            )
            conn.commit()
        return IndexManifestEntry(
            kind=kind,
            name=name,
            version=version,
            sha256=sha256,
            row_count=row_count,
            updated_at=now,
            metadata_json=meta,
        )

    def get(self, kind: str, name: str) -> IndexManifestEntry | None:
        """Return the manifest entry for one index, or None."""
        self.ensure_table()
        with self._conn() as conn:
            row = conn.execute(
                f"SELECT * FROM {self.TABLE} WHERE kind=? AND name=?",
                (kind, name),
            ).fetchone()
            if row is None:
                return None
            return IndexManifestEntry(
                kind=row["kind"],
                name=row["name"],
                version=row["version"],
                sha256=row["sha256"],
                row_count=row["row_count"],
                updated_at=row["updated_at"],
                metadata_json=row["metadata_json"],
            )

    def list_entries(self) -> list[IndexManifestEntry]:
        """Return all manifest entries."""
        self.ensure_table()
        with self._conn() as conn:
            rows = conn.execute(
                f"SELECT * FROM {self.TABLE} ORDER BY kind, name"
            ).fetchall()
            return [
                IndexManifestEntry(
                    kind=r["kind"],
                    name=r["name"],
                    version=r["version"],
                    sha256=r["sha256"],
                    row_count=r["row_count"],
                    updated_at=r["updated_at"],
                    metadata_json=r["metadata_json"],
                )
                for r in rows
            ]

    def delete(self, kind: str, name: str) -> bool:
        """Delete one manifest entry. Returns True if a row was removed."""
        self.ensure_table()
        with self._conn() as conn:
            cur = conn.execute(
                f"DELETE FROM {self.TABLE} WHERE kind=? AND name=?",
                (kind, name),
            )
            conn.commit()
            return cur.rowcount > 0

    # ── fingerprint helpers ───────────────────────────────────────────────

    @staticmethod
    def _fingerprint_fts(conn: sqlite3.Connection, table: str) -> dict[str, Any]:
        """Compute fingerprint for an FTS5 virtual table."""
        try:
            rows = conn.execute(
                f"SELECT rowid, * FROM {table} ORDER BY rowid"
            ).fetchall()
        except sqlite3.OperationalError as exc:
            raise ValueError(f"FTS table not found: {table}") from exc
        payload = {
            "kind": "fts",
            "table": table,
            "rows": [[r["rowid"]] + [r[c] for c in r if c != "rowid"] for r in rows],
        }
        return IndexManifest._payload_fingerprint(payload, len(rows), table)

    @staticmethod
    def _fingerprint_vector(conn: sqlite3.Connection, table: str) -> dict[str, Any]:
        """Compute fingerprint for a vec0 virtual table."""
        try:
            map_table = f"{table}_id_map"
            conn.execute(f"SELECT 1 FROM {map_table} LIMIT 1")
        except sqlite3.OperationalError as exc:
            raise ValueError(f"vector map table not found: {map_table}") from exc
        rows = conn.execute(
            f"SELECT m.object_id, v.embedding "
            f"FROM {map_table} AS m "
            f"JOIN {table} AS v ON v.rowid=m.rowid "
            f"ORDER BY m.object_id"
        ).fetchall()
        records = sorted(
            (str(r["object_id"]), hashlib.sha256(bytes(r["embedding"])).hexdigest())
            for r in rows
        )
        payload = {"kind": "vector", "table": table, "records": records}
        return IndexManifest._payload_fingerprint(payload, len(rows), table)

    @staticmethod
    def _fingerprint_graph(conn: sqlite3.Connection) -> dict[str, Any]:
        """Compute fingerprint for the graph index."""
        try:
            entities = conn.execute(
                "SELECT id, entity_type, properties FROM graph_entities ORDER BY id"
            ).fetchall()
            relations = conn.execute(
                "SELECT source_id, target_id, relation_type "
                "FROM graph_relations ORDER BY source_id, target_id"
            ).fetchall()
        except sqlite3.OperationalError as exc:
            raise ValueError("graph tables not found") from exc
        payload = {
            "kind": "graph",
            "table": "graph",
            "entities": [(str(r["id"]), str(r["entity_type"])) for r in entities],
            "relations": [
                (str(r["source_id"]), str(r["target_id"]), str(r["relation_type"]))
                for r in relations
            ],
        }
        total = len(entities) + len(relations)
        return IndexManifest._payload_fingerprint(payload, total, "graph")

    @staticmethod
    def _fingerprint_evidence(conn: sqlite3.Connection, table: str) -> dict[str, Any]:
        """Compute fingerprint for an evidence table."""
        try:
            rows = conn.execute(f"SELECT * FROM {table} ORDER BY rowid").fetchall()
        except sqlite3.OperationalError as exc:
            raise ValueError(f"evidence table not found: {table}") from exc
        payload = {
            "kind": "evidence",
            "table": table,
            "rows": [dict(r) for r in rows],
        }
        return IndexManifest._payload_fingerprint(payload, len(rows), table)

    @staticmethod
    def _payload_fingerprint(
        payload: dict[str, Any], row_count: int, table: str
    ) -> dict[str, Any]:
        encoded = json.dumps(
            payload, ensure_ascii=True, separators=(",", ":"), default=str
        ).encode("utf-8")
        return {
            "kind": payload["kind"],
            "table": table,
            "row_count": row_count,
            "sha256": hashlib.sha256(encoded).hexdigest(),
        }

    def compute_fingerprint(
        self, kind: str, table: str | None = None
    ) -> dict[str, Any]:
        """Compute a deterministic fingerprint for an index.

        Args:
            kind: One of "fts", "vector", "graph", "evidence".
            table: The SQLite table name (required for fts, vector, evidence;
                   ignored for graph).

        Returns:
            Dict with keys: kind, table, row_count, sha256.
        """
        if kind not in self.SUPPORTED_KINDS:
            raise ValueError(f"unsupported index kind: {kind!r}")
        with self._conn() as conn:
            if kind == "fts":
                if not table:
                    raise ValueError("table name required for fts fingerprint")
                return self._fingerprint_fts(conn, table)
            elif kind == "vector":
                if not table:
                    raise ValueError("table name required for vector fingerprint")
                return self._fingerprint_vector(conn, table)
            elif kind == "graph":
                return self._fingerprint_graph(conn)
            elif kind == "evidence":
                if not table:
                    raise ValueError("table name required for evidence fingerprint")
                return self._fingerprint_evidence(conn, table)
        raise ValueError(f"unexpected kind: {kind}")

    # ── restart readback ──────────────────────────────────────────────────

    def verify_restart_readback(self, kind: str, table: str | None = None) -> dict[str, Any]:
        """Verify that a recorded index still matches its last fingerprint.

        This simulates restart readback: re-compute the fingerprint and compare
        with the stored manifest entry.

        Returns:
            {kind, name, stored_sha256, current_sha256, row_count, match, entry}.
        """
        name = table or kind
        entry = self.get(kind, name)
        if entry is None:
            return {
                "kind": kind,
                "name": name,
                "match": False,
                "reason": "no_manifest_entry",
                "row_count": 0,
            }
        current = self.compute_fingerprint(kind, table)
        match = current["sha256"] == entry.sha256 and current["row_count"] == entry.row_count
        return {
            "kind": kind,
            "name": name,
            "stored_sha256": entry.sha256,
            "current_sha256": current["sha256"],
            "row_count": current["row_count"],
            "stored_row_count": entry.row_count,
            "match": match,
            "entry": entry,
        }
