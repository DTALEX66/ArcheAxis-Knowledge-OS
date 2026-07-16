"""sqlite-vec powered vector database — cosine similarity search over dense embeddings.

Uses the sqlite-vec extension (https://github.com/asg017/sqlite-vec) for fast,
in-process vector search with no external server.  The vec0 virtual table stores
float32 embeddings and supports MATCH queries with distance ordering.

Because vec0 requires integer rowids, we maintain a ``_id_map`` lookup table
that maps application-level object IDs (strings like ``doc_xxxx``) to internal
integer rowids.

Usage:
    vdb = VectorDB(dim=384)
    vdb.insert("doc_001", embedding)          # numpy float32[dim]
    results = vdb.search(query_embedding, top_k=5)  # → [(id, distance), ...]
"""

from __future__ import annotations

import re
import sqlite3
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

import numpy as np

from shared.config import config, resolve_runtime_path
from shared.stable_hash import stable_hash_text

DEFAULT_DB_PATH = resolve_runtime_path(str(config.get("database.path", "data/cognitive_os.sqlite")))
_SQL_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


@dataclass(frozen=True)
class VectorIndexCandidate:
    """A validated, inactive vector index produced by a shadow rebuild.

    The candidate owns only its temporary SQLite tables.  It deliberately has no
    switch operation yet: callers must validate it before a future migration
    boundary is allowed to replace the active index.
    """

    active_table: str
    table_name: str
    dim: int
    db_path: str
    object_ids: tuple[str, ...]
    count: int

    def discard(self) -> None:
        """Drop this inactive candidate; the active index is never touched."""
        VectorDB(table_name=self.table_name, dim=self.dim, db_path=self.db_path).drop()


class VectorDB:
    """sqlite-vec powered vector index in the shared SQLite database."""

    def __init__(
        self,
        table_name: str = "vec_embeddings",
        dim: int = 384,
        db_path: str | Path | None = None,
    ) -> None:
        if not _SQL_IDENTIFIER_RE.fullmatch(table_name):
            raise ValueError(f"invalid vector table name: {table_name!r}")
        self.table_name = table_name
        self.dim = dim
        self.db_path = str(db_path or DEFAULT_DB_PATH)
        self._map_table = f"{table_name}_id_map"

    # ── connection ──────────────────────────────────────

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.enable_load_extension(True)
        import sqlite_vec as sv  # noqa: F811 — loaded at call time

        sv.load(conn)
        conn.enable_load_extension(False)
        conn.row_factory = sqlite3.Row
        return conn

    # ── lifecycle ───────────────────────────────────────

    def init(self) -> None:
        """Create the vec0 virtual table + id-map table if they don't exist."""
        conn = self._get_conn()
        try:
            conn.execute(
                f"CREATE TABLE IF NOT EXISTS {self._map_table} ("
                "  object_id TEXT PRIMARY KEY,"
                "  rowid INTEGER UNIQUE"
                ")"
            )
            conn.execute(
                f"CREATE VIRTUAL TABLE IF NOT EXISTS {self.table_name} "
                f"USING vec0(embedding float[{self.dim}])"
            )
            conn.commit()
        finally:
            conn.close()

    def build_candidate(
        self, records: Iterable[tuple[str, np.ndarray]]
    ) -> VectorIndexCandidate:
        """Build and validate an inactive shadow index from canonical records.

        This method never drops or writes the active index.  Record IDs and
        vector dimensions are validated before candidate tables are created;
        candidate tables are removed automatically if construction or validation
        fails.  Switching and rollback remain separate migration operations.
        """
        materialized = tuple(records)
        object_ids: list[str] = []
        vectors: list[np.ndarray] = []
        seen: set[str] = set()
        for record in materialized:
            try:
                object_id, vector = record
            except (TypeError, ValueError) as exc:
                raise ValueError("candidate records must be (object_id, vector) pairs") from exc
            if not isinstance(object_id, str) or not object_id:
                raise ValueError("candidate object_id must be a non-empty string")
            if object_id in seen:
                raise ValueError(f"duplicate object_id in candidate: {object_id!r}")
            seen.add(object_id)
            array = np.asarray(vector, dtype=np.float32)
            if array.shape != (self.dim,):
                raise ValueError(
                    f"candidate vector for {object_id!r} must have shape ({self.dim},)"
                )
            object_ids.append(object_id)
            vectors.append(array)

        candidate_table = f"{self.table_name}__candidate_{uuid4().hex}"
        candidate_db = VectorDB(
            table_name=candidate_table,
            dim=self.dim,
            db_path=self.db_path,
        )
        try:
            candidate_db.init()
            for object_id, vector in zip(object_ids, vectors, strict=True):
                candidate_db.insert(object_id, vector)
            actual_ids = set(candidate_db.list_ids(limit=max(len(object_ids), 1)))
            if candidate_db.count() != len(object_ids) or actual_ids != seen:
                raise RuntimeError("candidate index validation failed")
        except Exception:
            candidate_db.drop()
            raise

        return VectorIndexCandidate(
            active_table=self.table_name,
            table_name=candidate_table,
            dim=self.dim,
            db_path=self.db_path,
            object_ids=tuple(object_ids),
            count=len(object_ids),
        )

    def drop(self) -> None:
        """Drop the virtual table + map (for teardown / rebuild)."""
        conn = self._get_conn()
        try:
            conn.execute(f"DROP TABLE IF EXISTS {self._map_table}")
            conn.execute(f"DROP TABLE IF EXISTS {self.table_name}")
            conn.commit()
        finally:
            conn.close()

    # ── internal id mapping ─────────────────────────────

    def _to_rowid(self, object_id: str) -> int:
        """Map a string object_id to an integer rowid (stable hash)."""
        return int(stable_hash_text(object_id, namespace="vector-rowid")[:14], 16) % (2**53)

    def _resolve_rowid(self, object_id: str, conn: sqlite3.Connection) -> int:
        """Return the stored integer rowid for *object_id*, inserting a new
        mapping if one does not exist."""
        row = conn.execute(
            f"SELECT rowid FROM {self._map_table} WHERE object_id=?",
            (object_id,),
        ).fetchone()
        if row:
            return row["rowid"]
        rid = self._to_rowid(object_id)
        conn.execute(
            f"INSERT OR IGNORE INTO {self._map_table}(object_id, rowid) VALUES (?,?)",
            (object_id, rid),
        )
        return rid

    def _resolve_object_id(self, rowid: int, conn: sqlite3.Connection) -> str | None:
        """Reverse-lookup: integer rowid → string object_id."""
        row = conn.execute(
            f"SELECT object_id FROM {self._map_table} WHERE rowid=?",
            (rowid,),
        ).fetchone()
        return row["object_id"] if row else None

    # ── CRUD ────────────────────────────────────────────

    def insert(self, object_id: str, vector: np.ndarray) -> None:
        """Insert or replace an embedding.

        Args:
            object_id: a unique key linking this vector back to its source row
                       (e.g. ``doc_xxxx``, ``card_xxxx``).
            vector: float32 numpy array of length ``self.dim``.
        """
        blob = np.asarray(vector, dtype=np.float32).tobytes()
        conn = self._get_conn()
        try:
            # Remove old mapping + vector if present
            old = conn.execute(
                f"SELECT rowid FROM {self._map_table} WHERE object_id=?",
                (object_id,),
            ).fetchone()
            if old:
                conn.execute(
                    f"DELETE FROM {self.table_name} WHERE rowid=?",
                    (old["rowid"],),
                )

            rid = self._to_rowid(object_id)
            conn.execute(
                f"INSERT OR REPLACE INTO {self._map_table}(object_id, rowid) VALUES (?,?)",
                (object_id, rid),
            )
            conn.execute(
                f"INSERT OR REPLACE INTO {self.table_name}(rowid, embedding) VALUES (?, ?)",
                (rid, blob),
            )
            conn.commit()
        finally:
            conn.close()

    def insert_by_text(self, object_id: str, text: str, embedder=None) -> None:
        """Convenience: embed *text* and store.

        If *embedder* is None, uses :class:`SimpleTextEmbedder` with ``dim``.
        """
        if embedder is None:
            from app.memory.vector_db import SimpleTextEmbedder

            embedder = SimpleTextEmbedder(dim=self.dim)
        vec = embedder.embed(text)
        self.insert(object_id, vec)

    def search(self, vector: np.ndarray, top_k: int = 5) -> list[tuple[str, float]]:
        """K-nearest-neighbour search via cosine distance.

        Returns:
            List of ``(object_id, distance)`` tuples sorted by ascending distance.
            Distance 0 = identical; higher = more dissimilar.
        """
        blob = np.asarray(vector, dtype=np.float32).tobytes()
        conn = self._get_conn()
        try:
            rows = conn.execute(
                f"SELECT rowid, distance FROM {self.table_name} WHERE embedding MATCH ? AND k=?",
                (blob, top_k),
            ).fetchall()
            results = []
            for r in rows:
                oid = self._resolve_object_id(r["rowid"], conn)
                if oid:
                    results.append((oid, r["distance"]))
            return results
        finally:
            conn.close()

    def search_by_text(self, query: str, top_k: int = 5, embedder=None) -> list[tuple[str, float]]:
        """Convenience: embed *query* and search."""
        if embedder is None:
            from app.memory.vector_db import SimpleTextEmbedder

            embedder = SimpleTextEmbedder(dim=self.dim)
        vec = embedder.embed(query)
        return self.search(vec, top_k=top_k)

    def delete(self, object_id: str) -> None:
        """Remove a single vector by its object id."""
        conn = self._get_conn()
        try:
            row = conn.execute(
                f"SELECT rowid FROM {self._map_table} WHERE object_id=?",
                (object_id,),
            ).fetchone()
            if row:
                conn.execute(
                    f"DELETE FROM {self.table_name} WHERE rowid=?",
                    (row["rowid"],),
                )
                conn.execute(
                    f"DELETE FROM {self._map_table} WHERE object_id=?",
                    (object_id,),
                )
            conn.commit()
        finally:
            conn.close()

    def delete_many(self, object_ids: list[str]) -> None:
        """Batch-delete vectors."""
        conn = self._get_conn()
        try:
            placeholders = ",".join("?" for _ in object_ids)
            rows = conn.execute(
                f"SELECT rowid FROM {self._map_table} WHERE object_id IN ({placeholders})",
                object_ids,
            ).fetchall()
            rids = [r["rowid"] for r in rows]
            if rids:
                rid_ph = ",".join("?" for _ in rids)
                conn.execute(
                    f"DELETE FROM {self.table_name} WHERE rowid IN ({rid_ph})",
                    rids,
                )
            conn.execute(
                f"DELETE FROM {self._map_table} WHERE object_id IN ({placeholders})",
                object_ids,
            )
            conn.commit()
        finally:
            conn.close()

    def count(self) -> int:
        """Number of indexed vectors."""
        conn = self._get_conn()
        try:
            n = conn.execute(f"SELECT COUNT(*) FROM {self.table_name}").fetchone()[0]
            return n
        finally:
            conn.close()

    def list_ids(self, limit: int = 1000) -> list[str]:
        """Return all indexed object ids."""
        conn = self._get_conn()
        try:
            rows = conn.execute(
                f"SELECT object_id FROM {self._map_table} LIMIT ?", (limit,)
            ).fetchall()
            return [r["object_id"] for r in rows]
        finally:
            conn.close()


# ── embedder ────────────────────────────────────────────


class SimpleTextEmbedder:
    """Lightweight, zero-dependency text embedder.

    Uses character n-gram hashing + L2 normalisation to produce a dense
    fixed-size vector.  This is fast and captures a surprising amount of
    lexical + sub-word similarity without requiring a model download.

    Attributes:
        dim: output vector dimension (default 384).
        ngram_range: min/max character n-gram sizes.
    """

    def __init__(self, dim: int = 384, ngram_range: tuple[int, int] = (2, 4)) -> None:
        self.dim = dim
        self.ngram_range = ngram_range

    @staticmethod
    def _char_ngrams(text: str, n: int):
        """Yield character n-grams from *text*."""
        text = text.lower()
        for i in range(len(text) - n + 1):
            yield text[i : i + n]

    def embed(self, text: str) -> np.ndarray:
        """Convert *text* to a unit-norm float32 vector."""
        if not text or not text.strip():
            return np.zeros(self.dim, dtype=np.float32)

        vec = np.zeros(self.dim, dtype=np.float32)
        ngram_count = 0

        for n in range(self.ngram_range[0], self.ngram_range[1] + 1):
            for ng in self._char_ngrams(text, n):
                h = int(stable_hash_text(ng, namespace="embedding-ngram")[:14], 16) % self.dim
                vec[h] += 1.0
                ngram_count += 1

        if ngram_count == 0:
            return vec

        # L2 normalise so cosine distance is meaningful
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec /= norm
        return vec.astype(np.float32)
