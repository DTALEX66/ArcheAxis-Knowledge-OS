"""Side-effect-free FTS5 shadow candidate lifecycle for explicit SQLite targets."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from shared.stable_hash import stable_hash_text

_FTS_SOURCE_SPECS = {
    "kb_documents": (
        "kb_documents_fts",
        "CREATE VIRTUAL TABLE {candidate} USING fts5("
        "id UNINDEXED, title, content, source, tokenize='porter unicode61')",
        ("id", "title", "content", "source"),
        ("id", "title", "content", "source"),
    ),
    "kb_cards": (
        "kb_cards_fts",
        "CREATE VIRTUAL TABLE {candidate} USING fts5("
        "id UNINDEXED, title, content, tags, tokenize='porter unicode61')",
        ("id", "title", "content", "tags"),
        ("id", "title", "content", "tags_json AS tags"),
    ),
}


def fts_source_spec(source_table: str) -> tuple[str, str, tuple[str, ...], tuple[str, ...]]:
    """Return the code-owned FTS spec for one canonical source table."""
    try:
        return _FTS_SOURCE_SPECS[source_table]
    except KeyError as exc:
        raise ValueError(f"unsupported FTS source table: {source_table}") from exc


def _validated_table(connection: sqlite3.Connection, table: str) -> str:
    row = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE (type='table' OR type='view') AND name=?",
        (table,),
    ).fetchone()
    if row is None:
        raise ValueError(f"unknown storage table: {table}")
    return table


def _fts_row_fingerprint(row: sqlite3.Row, columns: tuple[str, ...]) -> str:
    payload = json.dumps(
        [row[column] for column in columns],
        ensure_ascii=False,
        separators=(",", ":"),
        default=str,
    )
    return stable_hash_text(payload, namespace="fts-row")


def fts_index_fingerprint(
    connection: sqlite3.Connection, table: str, columns: tuple[str, ...]
) -> dict[str, object]:
    """Return a deterministic fingerprint for the current contents of an FTS table."""
    _validated_table(connection, table)
    quoted_columns = ", ".join(f'"{column}"' for column in columns)
    rows = connection.execute(
        f'SELECT rowid, {quoted_columns} FROM "{table}" ORDER BY rowid'
    ).fetchall()
    payload = {
        "table": table,
        "columns": list(columns),
        "rows": [[int(row[0]), *list(tuple(row)[1:])] for row in rows],
    }
    encoded = json.dumps(
        payload, ensure_ascii=True, separators=(",", ":"), default=str
    ).encode("utf-8")
    return {
        "kind": "fts",
        "table": table,
        "columns": list(columns),
        "row_count": len(rows),
        "sha256": hashlib.sha256(encoded).hexdigest(),
    }


@dataclass(frozen=True)
class FtsIndexRollback:
    """Rollback handle for one successful FTS candidate activation."""

    active_table: str
    backup_table: str
    candidate_table: str
    create_sql: str
    columns: tuple[str, ...]
    db_path: str

    def rollback(
        self,
        *,
        expected_active_fingerprint: dict[str, object] | None = None,
        before_commit: Callable[[sqlite3.Connection], None] | None = None,
    ) -> None:
        """Restore the pre-activation FTS rows and remove migration tables."""
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        quoted_active = f'"{self.active_table}"'
        quoted_backup = f'"{self.backup_table}"'
        quoted_candidate = f'"{self.candidate_table}"'
        quoted_columns = ", ".join(f'"{column}"' for column in self.columns)
        try:
            connection.execute("BEGIN IMMEDIATE")
            if expected_active_fingerprint is not None:
                current_fingerprint = fts_index_fingerprint(
                    connection, self.active_table, self.columns
                )
                if current_fingerprint != expected_active_fingerprint:
                    raise RuntimeError("active FTS index changed since apply")
            names = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE name IN (?, ?)",
                    (self.active_table, self.backup_table),
                )
            }
            if names != {self.active_table, self.backup_table}:
                raise ValueError("FTS rollback source missing")
            rows = connection.execute(
                f"SELECT rowid, {quoted_columns} FROM {quoted_backup} ORDER BY rowid"
            ).fetchall()
            connection.execute(f"DELETE FROM {quoted_active}")
            for row in rows:
                values = (row[0], *row[1:])
                placeholders = ", ".join("?" for _ in values)
                connection.execute(
                    f"INSERT INTO {quoted_active}(rowid, {quoted_columns}) "
                    f"VALUES ({placeholders})",
                    values,
                )
            connection.execute(f"DROP TABLE IF EXISTS {quoted_candidate}")
            connection.execute(f"DROP TABLE {quoted_backup}")
            if before_commit is not None:
                before_commit(connection)
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()


@dataclass(frozen=True)
class FtsIndexCandidate:
    """A verified, inactive FTS5 index produced from canonical rows."""

    source_table: str
    active_table: str
    table_name: str
    db_path: str
    object_ids: tuple[str, ...]
    rowids: tuple[int, ...]
    count: int
    row_fingerprints: tuple[str, ...]
    create_sql: str
    columns: tuple[str, ...]

    def verify(self, connection: sqlite3.Connection | None = None) -> bool:
        """Verify candidate payload and canonical source without touching active FTS."""
        spec = _FTS_SOURCE_SPECS.get(self.source_table)
        if spec is None:
            raise RuntimeError("FTS candidate verification failed")
        _, _, columns, source_columns = spec
        quoted_columns = ", ".join(f'"{column}"' for column in columns)
        try:
            if connection is None:
                with sqlite3.connect(self.db_path) as owned_connection:
                    owned_connection.row_factory = sqlite3.Row
                    return self.verify(connection=owned_connection)
            candidate_rows = connection.execute(
                f'SELECT rowid, {quoted_columns} FROM "{self.table_name}" ORDER BY rowid'
            ).fetchall()
            source_rows = connection.execute(
                f'SELECT rowid, {", ".join(source_columns)} '
                f'FROM "{self.source_table}" ORDER BY rowid'
            ).fetchall()
            actual_rowids = tuple(int(row["rowid"]) for row in candidate_rows)
            actual_ids = tuple(str(row["id"]) for row in candidate_rows)
            actual_fingerprints = tuple(
                _fts_row_fingerprint(row, columns) for row in candidate_rows
            )
            source_rowids = tuple(int(row["rowid"]) for row in source_rows)
            source_ids = tuple(str(row["id"]) for row in source_rows)
            source_fingerprints = tuple(
                _fts_row_fingerprint(row, columns) for row in source_rows
            )
        except (OSError, sqlite3.Error) as exc:
            raise RuntimeError("FTS candidate verification failed") from exc
        if (
            len(actual_ids) != self.count
            or len(set(actual_ids)) != len(actual_ids)
            or actual_rowids != self.rowids
            or actual_ids != self.object_ids
            or actual_fingerprints != self.row_fingerprints
            or source_rowids != self.rowids
            or source_ids != self.object_ids
            or source_fingerprints != self.row_fingerprints
        ):
            raise RuntimeError("FTS candidate verification failed")
        return True

    def activate(
        self,
        *,
        before_switch: Callable[[sqlite3.Connection], None] | None = None,
        before_commit: Callable[[sqlite3.Connection, FtsIndexRollback], None]
        | None = None,
    ) -> FtsIndexRollback:
        """Replace active FTS rows after verification and retain a rollback copy."""
        backup_table = f"{self.active_table}__rollback_{uuid4().hex}"
        quoted_active = f'"{self.active_table}"'
        quoted_candidate = f'"{self.table_name}"'
        quoted_backup = f'"{backup_table}"'
        quoted_columns = ", ".join(f'"{column}"' for column in self.columns)
        rollback = FtsIndexRollback(
            active_table=self.active_table,
            backup_table=backup_table,
            candidate_table=self.table_name,
            create_sql=self.create_sql,
            columns=self.columns,
            db_path=self.db_path,
        )
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        try:
            connection.execute("BEGIN IMMEDIATE")
            _validated_table(connection, self.active_table)
            _validated_table(connection, self.table_name)
            self.verify(connection=connection)
            if before_switch is not None:
                before_switch(connection)
            connection.execute(self.create_sql.format(candidate=quoted_backup))
            active_rows = connection.execute(
                f"SELECT rowid, {quoted_columns} FROM {quoted_active} ORDER BY rowid"
            ).fetchall()
            candidate_rows = connection.execute(
                f"SELECT rowid, {quoted_columns} FROM {quoted_candidate} ORDER BY rowid"
            ).fetchall()
            for row in active_rows:
                values = (row[0], *row[1:])
                placeholders = ", ".join("?" for _ in values)
                connection.execute(
                    f"INSERT INTO {quoted_backup}(rowid, {quoted_columns}) "
                    f"VALUES ({placeholders})",
                    values,
                )
            connection.execute(f"DELETE FROM {quoted_active}")
            for row in candidate_rows:
                values = (row[0], *row[1:])
                placeholders = ", ".join("?" for _ in values)
                connection.execute(
                    f"INSERT INTO {quoted_active}(rowid, {quoted_columns}) "
                    f"VALUES ({placeholders})",
                    values,
                )
            if before_commit is not None:
                before_commit(connection, rollback)
            connection.commit()
        except Exception:
            connection.rollback()
            with suppress(Exception):
                connection.execute(f"DROP TABLE IF EXISTS {quoted_backup}")
                connection.commit()
            raise
        finally:
            connection.close()
        return rollback

    def discard(self) -> None:
        """Drop this inactive candidate; the active index is never touched."""
        with sqlite3.connect(self.db_path) as connection:
            connection.execute(f'DROP TABLE IF EXISTS "{self.table_name}"')
            connection.commit()


def build_fts_candidate(source_table: str, *, db_path: str | Path) -> FtsIndexCandidate:
    """Build and verify an inactive FTS5 candidate on one explicit database."""
    spec = _FTS_SOURCE_SPECS.get(source_table)
    if spec is None:
        raise ValueError(f"unsupported FTS source table: {source_table}")
    active_table, create_sql, columns, source_columns = spec
    database = Path(db_path).resolve()
    connection = sqlite3.connect(str(database))
    connection.row_factory = sqlite3.Row
    candidate_table = f"{active_table}__candidate_{uuid4().hex}"
    quoted_candidate = f'"{candidate_table}"'
    try:
        _validated_table(connection, source_table)
        rows = connection.execute(
            f'SELECT rowid, {", ".join(source_columns)} FROM "{source_table}" ORDER BY rowid'
        ).fetchall()
        connection.execute(create_sql.format(candidate=quoted_candidate))
        quoted_columns = ", ".join(f'"{column}"' for column in columns)
        placeholders = ", ".join("?" for _ in range(len(columns) + 1))
        for row in rows:
            connection.execute(
                f"INSERT INTO {quoted_candidate}(rowid, {quoted_columns}) "
                f"VALUES ({placeholders})",
                (row["rowid"], *(row[column] for column in columns)),
            )
        connection.commit()
    except Exception:
        connection.rollback()
        connection.execute(f'DROP TABLE IF EXISTS {quoted_candidate}')
        connection.commit()
        raise
    finally:
        connection.close()
    object_ids = tuple(str(row["id"]) for row in rows)
    candidate = FtsIndexCandidate(
        source_table=source_table,
        active_table=active_table,
        table_name=candidate_table,
        db_path=str(database),
        object_ids=object_ids,
        rowids=tuple(int(row["rowid"]) for row in rows),
        count=len(object_ids),
        row_fingerprints=tuple(_fts_row_fingerprint(row, columns) for row in rows),
        create_sql=create_sql,
        columns=columns,
    )
    try:
        candidate.verify()
    except Exception:
        candidate.discard()
        raise
    return candidate
