"""Canonical baseline SQLite schema owned by ``core.sqlite``."""

from __future__ import annotations

import re
import sqlite3
from collections.abc import Iterator
from functools import lru_cache

BASELINE_OWNER = "core.sqlite"
BASELINE_VERSION = 1
BASELINE_TARGET = "core_schema_v1"
BASELINE_MIGRATION_NAME = "core_sqlite_baseline_v1"
_DELEGATED_TABLES = frozenset({"kb_taskpacks"})
_SCHEMA_TYPES = ("table", "index", "trigger", "view")


def _scripts() -> tuple[str, str, str]:
    from app.memory import database as memory_database
    from shared import storage

    return storage.IR_KB_TABLES, storage.IR_KB_TABLES_EXT, memory_database.SCHEMA


def _statements(script: str) -> Iterator[str]:
    buffer = ""
    for line in script.splitlines(keepends=True):
        buffer += line
        if sqlite3.complete_statement(buffer):
            statement = buffer.strip()
            buffer = ""
            if statement:
                yield statement
    if buffer.strip():
        raise RuntimeError("baseline schema contains an incomplete SQL statement")


def apply(connection: sqlite3.Connection) -> None:
    """Apply the complete baseline schema in the caller-owned transaction."""
    for script in _scripts():
        for statement in _statements(script):
            connection.execute(statement)


def _normalize_sql(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip()).casefold()


def _contract(connection: sqlite3.Connection) -> dict[tuple[str, str], tuple[str, str]]:
    placeholders = ", ".join("?" for _ in _SCHEMA_TYPES)
    rows = connection.execute(
        "SELECT type, name, tbl_name, sql FROM sqlite_master "
        f"WHERE type IN ({placeholders}) AND sql IS NOT NULL "
        "AND name NOT LIKE 'sqlite_%' ORDER BY type, name",
        _SCHEMA_TYPES,
    ).fetchall()
    return {
        (str(row[0]), str(row[1])): (str(row[2]), _normalize_sql(row[3]))
        for row in rows
        if str(row[1]) not in _DELEGATED_TABLES and str(row[2]) not in _DELEGATED_TABLES
    }


@lru_cache(maxsize=1)
def expected_contract() -> dict[tuple[str, str], tuple[str, str]]:
    connection = sqlite3.connect(":memory:")
    try:
        apply(connection)
        return _contract(connection)
    finally:
        connection.close()


def validate(connection: sqlite3.Connection) -> None:
    """Fail closed when any baseline table/constraint/index differs from canonical DDL."""
    expected = expected_contract()
    actual = _contract(connection)
    missing = sorted(set(expected) - set(actual))
    mismatched = sorted(key for key in expected if key in actual and expected[key] != actual[key])
    if missing or mismatched:
        details = []
        if missing:
            details.append("missing=" + ",".join(f"{kind}:{name}" for kind, name in missing))
        if mismatched:
            details.append("mismatched=" + ",".join(f"{kind}:{name}" for kind, name in mismatched))
        raise RuntimeError("baseline schema does not match core.sqlite owner: " + "; ".join(details))
