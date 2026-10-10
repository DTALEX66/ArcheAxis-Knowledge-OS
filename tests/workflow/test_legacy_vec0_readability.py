"""A `vec0` table the Rust audit export cannot read is still readable by the product's own path.

This distinction is worth a test because getting it wrong is easy and costly: the Rust
`legacy_dryrun` export records such a table as `unqueried` with `no such module: vec0`, which reads
as "this data cannot be recovered". It can. `sqlite_vec` is an installed dependency, the product's
own reader loads it best-effort, and the table then reads normally. The gap belongs to one reader,
not to the data — and the real legacy store's `vec_episodes` is exactly that case (5 rows of
1536-dimension embeddings, measured 2026-10-06).

The test skips only when the extension genuinely is not installed, which is a different fact from
an unreadable table.
"""

from __future__ import annotations

import hashlib
import sqlite3
import struct
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]


def _vec0_database(path: Path, dimensions: int = 4) -> Path:
    sqlite_vec = pytest.importorskip("sqlite_vec")
    connection = sqlite3.connect(str(path))
    try:
        connection.enable_load_extension(True)
        sqlite_vec.load(connection)
        connection.enable_load_extension(False)
        connection.execute(f"CREATE VIRTUAL TABLE vec_episodes USING vec0(embedding float[{dimensions}])")
        for index in range(2):
            vector = struct.pack(f"<{dimensions}f", *(float(index + offset) for offset in range(dimensions)))
            connection.execute("INSERT INTO vec_episodes(rowid, embedding) VALUES (?, ?)",
                               (index + 1, vector))
        connection.commit()
    finally:
        connection.close()
    return path


def test_the_product_reader_opens_a_vec0_table_and_names_nothing_unreadable(tmp_path):
    from app.workspace import migrate

    database = _vec0_database(tmp_path / "with-vectors.sqlite")
    # Without the extension loaded this table is unreadable; with it, nothing is unreadable.
    assert migrate.unreadable_tables(database) == [], (
        "the product's own reader reports a vec0 table as unreadable, so a saved workspace would "
        "lose it even though the extension is installed")
    digest = migrate.content_hash(database)
    assert digest, "the content hash must cover the database that holds the readings"


def test_a_vec0_table_is_unreadable_exactly_when_the_extension_is_absent(tmp_path):
    """The failure is the module, not the table: opening it plainly reproduces the Rust reader's error.

    This is what makes the Rust `unqueried` entry correct as a statement about that reader, and
    wrong if read as a statement about the data.
    """
    pytest.importorskip("sqlite_vec")
    database = _vec0_database(tmp_path / "without-extension.sqlite")
    connection = sqlite3.connect(str(database))
    try:
        with pytest.raises(sqlite3.OperationalError, match="no such module: vec0"):
            connection.execute("SELECT count(*) FROM vec_episodes").fetchone()
    finally:
        connection.close()


def test_reading_a_vec0_table_leaves_the_database_bytes_unchanged(tmp_path):
    """A preservation read must not write; the legacy store is retained, never rewritten."""
    pytest.importorskip("sqlite_vec")
    from app.workspace import migrate

    database = _vec0_database(tmp_path / "read-only.sqlite")
    before = hashlib.sha256(database.read_bytes()).hexdigest()
    migrate.unreadable_tables(database)
    migrate.content_hash(database)
    assert hashlib.sha256(database.read_bytes()).hexdigest() == before
