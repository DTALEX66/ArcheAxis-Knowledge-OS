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

import hashlib
import json
import re
import sqlite3
from collections.abc import Callable, Iterable
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

import numpy as np

from shared.config import config, resolve_runtime_path
from shared.stable_hash import stable_hash_text

DEFAULT_DB_PATH = resolve_runtime_path(str(config.get("database.path", "data/cognitive_os.sqlite")))
_SQL_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def vector_fingerprint(vector: np.ndarray) -> str:
    """Return a deterministic digest for one normalized float32 embedding."""
    array = np.asarray(vector, dtype=np.float32)
    return hashlib.sha256(array.tobytes()).hexdigest()


@dataclass(frozen=True)
class VectorIndexRollback:
    """Rollback handle for one successful vector candidate activation."""

    active_table: str
    backup_table: str
    candidate_table: str
    dim: int
    db_path: str

    def rollback(
        self,
        *,
        expected_active_fingerprint: dict[str, object] | None = None,
        before_commit: Callable[[sqlite3.Connection], None] | None = None,
    ) -> None:
        """Atomically restore the pre-activation index and remove migration tables."""
        active_db = VectorDB(table_name=self.active_table, dim=self.dim, db_path=self.db_path)
        backup_db = VectorDB(table_name=self.backup_table, dim=self.dim, db_path=self.db_path)
        candidate_db = VectorDB(
            table_name=self.candidate_table, dim=self.dim, db_path=self.db_path
        )
        connection = active_db._get_conn()
        try:
            connection.execute("BEGIN IMMEDIATE")
            if expected_active_fingerprint is not None:
                current_fingerprint = active_db.fingerprint(connection=connection)
                if current_fingerprint != expected_active_fingerprint:
                    raise RuntimeError("active vector index changed since apply")
            required = {
                active_db.table_name,
                active_db._map_table,
                backup_db.table_name,
                backup_db._map_table,
            }
            existing = {
                str(row[0])
                for row in connection.execute(
                    f"SELECT name FROM sqlite_master WHERE name IN ({','.join('?' for _ in required)})",
                    tuple(required),
                )
            }
            if existing != required:
                raise ValueError("rollback source missing")
            rows = backup_db._records_in_connection(connection)
            active_db._replace_records_in_transaction(connection, rows)
            VectorDB._drop_index(
                connection, candidate_db.table_name, candidate_db._map_table
            )
            VectorDB._drop_index(connection, backup_db.table_name, backup_db._map_table)
            if before_commit is not None:
                before_commit(connection)
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()


@dataclass(frozen=True)
class VectorIndexCandidate:
    """A validated, inactive vector index produced by a shadow rebuild."""

    active_table: str
    table_name: str
    dim: int
    db_path: str
    object_ids: tuple[str, ...]
    count: int
    vector_fingerprints: tuple[tuple[str, str], ...]

    def verify(self, connection: sqlite3.Connection | None = None) -> bool:
        """Verify candidate cardinality and IDs without mutating either index.

        Verification is intentionally fail-closed so activation can require an
        intact candidate as a precondition.  The active table is not opened or
        modified by this check.
        """
        candidate_db = VectorDB(table_name=self.table_name, dim=self.dim, db_path=self.db_path)
        try:
            if connection is None:
                records = candidate_db._records()
            else:
                records = candidate_db._records_in_connection(connection)
        except Exception as exc:
            raise RuntimeError("candidate verification failed") from exc
        actual_fingerprints = tuple(
            sorted((object_id, vector_fingerprint(vector)) for object_id, vector in records)
        )
        if (
            len(records) != self.count
            or {object_id for object_id, _ in records} != set(self.object_ids)
            or actual_fingerprints != self.vector_fingerprints
        ):
            raise RuntimeError("candidate verification failed")
        return True

    def activate(
        self,
        *,
        before_switch: Callable[[sqlite3.Connection], None] | None = None,
        before_commit: Callable[[sqlite3.Connection, VectorIndexRollback], None]
        | None = None,
    ) -> VectorIndexRollback:
        """Replace the active contents after validation and retain a rollback copy."""
        active_db = VectorDB(table_name=self.active_table, dim=self.dim, db_path=self.db_path)
        candidate_db = VectorDB(
            table_name=self.table_name, dim=self.dim, db_path=self.db_path
        )
        backup_table = f"{self.active_table}__rollback_{uuid4().hex}"
        backup_db = VectorDB(table_name=backup_table, dim=self.dim, db_path=self.db_path)
        rollback = VectorIndexRollback(
            active_table=self.active_table,
            backup_table=backup_table,
            candidate_table=self.table_name,
            dim=self.dim,
            db_path=self.db_path,
        )
        connection = active_db._get_conn()
        try:
            connection.execute("BEGIN IMMEDIATE")
            if not active_db._index_exists_in_connection(connection):
                raise RuntimeError("active vector index is missing")
            self.verify(connection=connection)
            if before_switch is not None:
                before_switch(connection)
            candidate_records = candidate_db._records_in_connection(connection)
            active_records = active_db._records_in_connection(connection)
            backup_db._init_in_transaction(connection)
            backup_db._replace_records_in_transaction(connection, active_records)
            active_db._replace_records_in_transaction(connection, candidate_records)
            if before_commit is not None:
                before_commit(connection, rollback)
            connection.commit()
        except Exception:
            connection.rollback()
            with suppress(Exception):
                backup_db.drop()
            raise
        finally:
            connection.close()
        return rollback

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
            self._init_in_transaction(conn)
            conn.commit()
        finally:
            conn.close()

    def _init_in_transaction(self, connection: sqlite3.Connection) -> None:
        """Create this vec0 index using a caller-owned transaction."""
        connection.execute(
            f"CREATE TABLE IF NOT EXISTS {self._map_table} ("
            "  object_id TEXT PRIMARY KEY,"
            "  rowid INTEGER UNIQUE"
            ")"
        )
        connection.execute(
            f"CREATE VIRTUAL TABLE IF NOT EXISTS {self.table_name} "
            f"USING vec0(embedding float[{self.dim}])"
        )

    def _index_exists_in_connection(self, connection: sqlite3.Connection) -> bool:
        """Return whether both physical tables for this index exist on a connection."""
        names = {
            row["name"]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE name IN (?, ?)",
                (self.table_name, self._map_table),
            )
        }
        return names == {self.table_name, self._map_table}

    def _index_exists(self) -> bool:
        """Return whether both physical tables for this index exist."""
        conn = self._get_conn()
        try:
            return self._index_exists_in_connection(conn)
        finally:
            conn.close()

    def _records_in_connection(
        self, connection: sqlite3.Connection
    ) -> tuple[tuple[str, np.ndarray], ...]:
        """Read complete indexed records for a shadow copy operation."""
        rows = connection.execute(
            f"SELECT m.object_id, v.embedding FROM {self._map_table} AS m "
            f"JOIN {self.table_name} AS v ON v.rowid=m.rowid ORDER BY m.rowid"
        ).fetchall()
        records = []
        for row in rows:
            vector = np.frombuffer(bytes(row["embedding"]), dtype=np.float32).copy()
            if vector.shape != (self.dim,):
                raise RuntimeError(f"vector record has unexpected shape: {vector.shape}")
            records.append((str(row["object_id"]), vector))
        return tuple(records)

    def _records(self) -> tuple[tuple[str, np.ndarray], ...]:
        """Read complete indexed records for a shadow copy operation."""
        conn = self._get_conn()
        try:
            return self._records_in_connection(conn)
        finally:
            conn.close()

    def fingerprint(
        self, connection: sqlite3.Connection | None = None
    ) -> dict[str, object]:
        """Return a deterministic fingerprint for this vector index."""
        if connection is None:
            conn = self._get_conn()
            try:
                return self.fingerprint(connection=conn)
            finally:
                conn.close()
        records = self._records_in_connection(connection)
        payload = {
            "table": self.table_name,
            "dim": self.dim,
            "records": sorted(
                (object_id, vector_fingerprint(vector)) for object_id, vector in records
            ),
        }
        encoded = json.dumps(
            payload, ensure_ascii=True, separators=(",", ":")
        ).encode("utf-8")
        return {
            "kind": "vector",
            "table": self.table_name,
            "dim": self.dim,
            "row_count": len(records),
            "sha256": hashlib.sha256(encoded).hexdigest(),
        }

    def _replace_records_in_transaction(
        self,
        connection: sqlite3.Connection,
        records: Iterable[tuple[str, np.ndarray]],
    ) -> None:
        """Replace this index using a transaction owned by the caller."""
        materialized = tuple(records)
        object_ids: set[str] = set()
        prepared: list[tuple[str, bytes]] = []
        for object_id, vector in materialized:
            if not isinstance(object_id, str) or not object_id or object_id in object_ids:
                raise ValueError("replacement records must have unique non-empty IDs")
            array = np.asarray(vector, dtype=np.float32)
            if array.shape != (self.dim,):
                raise ValueError(f"replacement vector must have shape ({self.dim},)")
            object_ids.add(object_id)
            prepared.append((object_id, array.tobytes()))

        connection.execute(f"DELETE FROM {self.table_name}")
        connection.execute(f"DELETE FROM {self._map_table}")
        for object_id, blob in prepared:
            rowid = self._to_rowid(object_id)
            connection.execute(
                f"INSERT INTO {self._map_table}(object_id, rowid) VALUES (?, ?)",
                (object_id, rowid),
            )
            connection.execute(
                f"INSERT INTO {self.table_name}(rowid, embedding) VALUES (?, ?)",
                (rowid, blob),
            )

    def _replace_records(self, records: Iterable[tuple[str, np.ndarray]]) -> None:
        """Atomically replace this already-created index with validated records."""
        conn = self._get_conn()
        try:
            conn.execute("BEGIN IMMEDIATE")
            self._replace_records_in_transaction(conn, records)
            conn.commit()
        except Exception:
            conn.rollback()
            raise
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
            vector_fingerprints=tuple(
                sorted(
                    (object_id, vector_fingerprint(vector))
                    for object_id, vector in zip(object_ids, vectors, strict=True)
                )
            ),
        )

    @staticmethod
    def _drop_index(
        connection: sqlite3.Connection, table_name: str, map_table: str
    ) -> None:
        """Drop one vector index using the caller's transaction."""
        connection.execute(f"DROP TABLE IF EXISTS {map_table}")
        connection.execute(f"DROP TABLE IF EXISTS {table_name}")

    def drop(self) -> None:
        """Drop the virtual table + map (for teardown / rebuild)."""
        conn = self._get_conn()
        try:
            self._drop_index(conn, self.table_name, self._map_table)
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
