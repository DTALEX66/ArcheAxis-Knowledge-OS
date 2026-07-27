"""Graph index shadow candidate lifecycle — rebuild, verify, activate, rollback.

Builds on top of the ``graph_entities`` and ``graph_relations`` SQLite tables
used by ``app.memory.graph_db.GraphDB``.  A candidate is a snapshot of both
tables in shadow tables; activation replaces active rows inside a transaction
while preserving a rollback copy.

Usage::

    from shared.graph_index import build_graph_candidate

    candidate = build_graph_candidate(db_path)
    try:
        candidate.verify()                     # read-only check
        rollback = candidate.activate()        # swap into active tables
        # ... verify new graph state ...
        rollback.rollback()                    # restore previous state
    finally:
        candidate.discard()                    # clean up shadow tables
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

_ENTITY_TABLE = "graph_entities"
_RELATION_TABLE = "graph_relations"


def _validate_db(connection: sqlite3.Connection) -> None:
    """Verify that both graph tables exist; raise ValueError if not."""
    for t in (_ENTITY_TABLE, _RELATION_TABLE):
        row = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
            (t,),
        ).fetchone()
        if row is None:
            raise ValueError(f"graph table not found: {t}")


def _graph_fingerprint(connection: sqlite3.Connection) -> dict[str, object]:
    """Deterministic fingerprint of the current graph tables."""
    entities = connection.execute(
        f"SELECT id, entity_type, properties FROM {_ENTITY_TABLE} ORDER BY id"
    ).fetchall()
    relations = connection.execute(
        f"SELECT source_id, target_id, relation_type, weight "
        f"FROM {_RELATION_TABLE} ORDER BY source_id, target_id"
    ).fetchall()
    payload = {
        "entities": [
            (str(r["id"]), str(r["entity_type"]), str(r["properties"]))
            for r in entities
        ],
        "relations": [
            (str(r["source_id"]), str(r["target_id"]),
             str(r["relation_type"]), float(r["weight"]))
            for r in relations
        ],
    }
    encoded = json.dumps(
        payload, ensure_ascii=True, separators=(",", ":"), default=str
    ).encode("utf-8")
    return {
        "row_count": len(entities) + len(relations),
        "sha256": hashlib.sha256(encoded).hexdigest(),
    }


@dataclass(frozen=True)
class GraphIndexRollback:
    """Rollback handle for one successful graph candidate activation."""

    entity_backup_table: str
    relation_backup_table: str
    entity_candidate_table: str
    relation_candidate_table: str
    db_path: str

    def rollback(
        self,
        *,
        expected_active_fingerprint: dict[str, object] | None = None,
        before_commit: Callable[[sqlite3.Connection], None] | None = None,
    ) -> None:
        """Restore the pre-activation graph rows and remove migration tables."""
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        try:
            connection.execute("BEGIN IMMEDIATE")
            if expected_active_fingerprint is not None:
                current = _graph_fingerprint(connection)
                if current != expected_active_fingerprint:
                    raise RuntimeError("active graph changed since apply")
            for t in (
                self.entity_backup_table,
                self.relation_backup_table,
            ):
                row = connection.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
                    (t,),
                ).fetchone()
                if row is None:
                    raise ValueError("graph rollback source missing")

            # Restore entities from backup
            connection.execute(f"DELETE FROM {_ENTITY_TABLE}")
            backup_entities = connection.execute(
                f"SELECT * FROM {self.entity_backup_table} ORDER BY rowid"
            ).fetchall()
            for row in backup_entities:
                connection.execute(
                    f"INSERT INTO {_ENTITY_TABLE}(id, entity_type, properties, graph_name) "
                    f"VALUES (?, ?, ?, ?)",
                    (row["id"], row["entity_type"], row["properties"], row["graph_name"]),
                )

            # Restore relations from backup
            connection.execute(f"DELETE FROM {_RELATION_TABLE}")
            backup_relations = connection.execute(
                f"SELECT * FROM {self.relation_backup_table} ORDER BY rowid"
            ).fetchall()
            for row in backup_relations:
                connection.execute(
                    f"INSERT INTO {_RELATION_TABLE}(id, source_id, target_id, "
                    f"relation_type, weight, graph_name) "
                    f"VALUES (?, ?, ?, ?, ?, ?)",
                    (row["id"], row["source_id"], row["target_id"],
                     row["relation_type"], row["weight"], row["graph_name"]),
                )

            # Drop migration tables
            for t in (
                self.entity_candidate_table,
                self.relation_candidate_table,
                self.entity_backup_table,
                self.relation_backup_table,
            ):
                connection.execute(f"DROP TABLE IF EXISTS {t}")

            if before_commit is not None:
                before_commit(connection)
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()


@dataclass(frozen=True)
class GraphIndexCandidate:
    """A verified, inactive graph snapshot produced from canonical rows."""

    entity_table: str
    relation_table: str
    db_path: str
    entity_ids: tuple[str, ...]
    relation_keys: tuple[tuple[str, str, str], ...]
    entity_count: int
    relation_count: int

    def verify(self, connection: sqlite3.Connection | None = None) -> bool:
        """Verify candidate matches active source tables. Raises RuntimeError on mismatch."""
        close_after = connection is None
        try:
            if connection is None:
                connection = sqlite3.connect(self.db_path)
                connection.row_factory = sqlite3.Row

            for t in (self.entity_table, self.relation_table, _ENTITY_TABLE, _RELATION_TABLE):
                row = connection.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
                    (t,),
                ).fetchone()
                if row is None:
                    raise RuntimeError("graph candidate verification failed")

            # Compare candidate entity IDs with active entity IDs
            candidate_entity_ids = {
                str(r["id"])
                for r in connection.execute(
                    f"SELECT id FROM {self.entity_table} ORDER BY id"
                ).fetchall()
            }
            active_entity_ids = {
                str(r["id"])
                for r in connection.execute(
                    f"SELECT id FROM {_ENTITY_TABLE} ORDER BY id"
                ).fetchall()
            }
            if candidate_entity_ids != active_entity_ids:
                raise RuntimeError("graph candidate verification failed")
            if len(candidate_entity_ids) != self.entity_count:
                raise RuntimeError("graph candidate verification failed")

            # Compare candidate relation keys with active relation keys
            candidate_relation_keys = {
                (str(r["source_id"]), str(r["target_id"]), str(r["relation_type"]))
                for r in connection.execute(
                    f"SELECT source_id, target_id, relation_type "
                    f"FROM {self.relation_table} ORDER BY source_id, target_id"
                ).fetchall()
            }
            active_relation_keys = {
                (str(r["source_id"]), str(r["target_id"]), str(r["relation_type"]))
                for r in connection.execute(
                    f"SELECT source_id, target_id, relation_type "
                    f"FROM {_RELATION_TABLE} ORDER BY source_id, target_id"
                ).fetchall()
            }
            if candidate_relation_keys != active_relation_keys:
                raise RuntimeError("graph candidate verification failed")
            if len(candidate_relation_keys) != self.relation_count:
                raise RuntimeError("graph candidate verification failed")

            return True
        except (sqlite3.Error, OSError) as exc:
            raise RuntimeError("graph candidate verification failed") from exc
        finally:
            if close_after:
                connection.close()

    def activate(
        self,
        *,
        before_switch: Callable[[sqlite3.Connection], None] | None = None,
        before_commit: Callable[
            [sqlite3.Connection, GraphIndexRollback], None
        ] | None = None,
    ) -> GraphIndexRollback:
        """Replace active graph rows after verification and retain a rollback copy."""
        suffix = uuid4().hex
        entity_backup = f"{_ENTITY_TABLE}__rollback_{suffix}"
        relation_backup = f"{_RELATION_TABLE}__rollback_{suffix}"

        rollback = GraphIndexRollback(
            entity_backup_table=entity_backup,
            relation_backup_table=relation_backup,
            entity_candidate_table=self.entity_table,
            relation_candidate_table=self.relation_table,
            db_path=self.db_path,
        )

        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        try:
            connection.execute("BEGIN IMMEDIATE")
            _validate_db(connection)
            self.verify(connection=connection)
            if before_switch is not None:
                before_switch(connection)

            # Backup active entities
            connection.execute(
                f"CREATE TABLE {entity_backup} AS SELECT * FROM {_ENTITY_TABLE}"
            )
            connection.execute(
                f"CREATE TABLE {relation_backup} AS SELECT * FROM {_RELATION_TABLE}"
            )

            # Delete and replace active entities
            connection.execute(f"DELETE FROM {_ENTITY_TABLE}")
            candidate_entities = connection.execute(
                f"SELECT * FROM {self.entity_table} ORDER BY rowid"
            ).fetchall()
            for row in candidate_entities:
                connection.execute(
                    f"INSERT INTO {_ENTITY_TABLE}(id, entity_type, properties, graph_name) "
                    f"VALUES (?, ?, ?, ?)",
                    (row["id"], row["entity_type"], row["properties"], row["graph_name"]),
                )

            # Delete and replace active relations
            connection.execute(f"DELETE FROM {_RELATION_TABLE}")
            candidate_relations = connection.execute(
                f"SELECT * FROM {self.relation_table} ORDER BY rowid"
            ).fetchall()
            for row in candidate_relations:
                connection.execute(
                    f"INSERT INTO {_RELATION_TABLE}(id, source_id, target_id, "
                    f"relation_type, weight, graph_name) "
                    f"VALUES (?, ?, ?, ?, ?, ?)",
                    (row["id"], row["source_id"], row["target_id"],
                     row["relation_type"], row["weight"], row["graph_name"]),
                )

            if before_commit is not None:
                before_commit(connection, rollback)
            connection.commit()
        except Exception:
            connection.rollback()
            with suppress(Exception):
                connection.execute(f"DROP TABLE IF EXISTS {entity_backup}")
                connection.execute(f"DROP TABLE IF EXISTS {relation_backup}")
                connection.commit()
            raise
        finally:
            connection.close()
        return rollback

    def discard(self) -> None:
        """Drop this inactive candidate; active tables are never touched."""
        connection = sqlite3.connect(self.db_path)
        try:
            for t in (self.entity_table, self.relation_table):
                connection.execute(f"DROP TABLE IF EXISTS {t}")
            connection.commit()
        finally:
            connection.close()


def build_graph_candidate(db_path: str | Path) -> GraphIndexCandidate:
    """Build and verify an inactive graph snapshot.

    Creates shadow tables ``graph_entities__candidate_<hex>`` and
    ``graph_relations__candidate_<hex>`` with exact copies of the current
    active graph rows, then returns a verified ``GraphIndexCandidate``.

    Args:
        db_path: Path to the SQLite database containing the graph tables.

    Returns:
        A verified ``GraphIndexCandidate``.

    Raises:
        ValueError: If graph tables do not exist.
        RuntimeError: If candidate verification fails.
    """
    database = Path(db_path).resolve()
    connection = sqlite3.connect(str(database))
    connection.row_factory = sqlite3.Row
    suffix = uuid4().hex
    entity_candidate = f"{_ENTITY_TABLE}__candidate_{suffix}"
    relation_candidate = f"{_RELATION_TABLE}__candidate_{suffix}"

    try:
        _validate_db(connection)

        # Snapshot entities
        connection.execute(
            f"CREATE TABLE {entity_candidate} AS SELECT * FROM {_ENTITY_TABLE}"
        )
        # Snapshot relations
        connection.execute(
            f"CREATE TABLE {relation_candidate} AS SELECT * FROM {_RELATION_TABLE}"
        )
        connection.commit()

        entity_ids = tuple(
            str(r["id"])
            for r in connection.execute(
                f"SELECT id FROM {entity_candidate} ORDER BY id"
            ).fetchall()
        )
        relation_keys = tuple(
            (str(r["source_id"]), str(r["target_id"]), str(r["relation_type"]))
            for r in connection.execute(
                f"SELECT source_id, target_id, relation_type "
                f"FROM {relation_candidate} ORDER BY source_id, target_id"
            ).fetchall()
        )
        entity_count = len(entity_ids)
        relation_count = len(relation_keys)

        candidate = GraphIndexCandidate(
            entity_table=entity_candidate,
            relation_table=relation_candidate,
            db_path=str(database),
            entity_ids=entity_ids,
            relation_keys=relation_keys,
            entity_count=entity_count,
            relation_count=relation_count,
        )

        candidate.verify(connection=connection)
    except Exception:
        for t in (entity_candidate, relation_candidate):
            with suppress(Exception):
                connection.execute(f"DROP TABLE IF EXISTS {t}")
        connection.commit()
        raise
    finally:
        connection.close()

    return candidate
