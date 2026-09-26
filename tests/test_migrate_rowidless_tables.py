"""AXW-DATA-403 robustness: real saved workspaces are not all plain tables.

The migration's fixtures contain only three ordinary tables, so CI never exercised
the shapes a real saved workspace has. Driving the real legacy asset
(`data/cognitive_os.sqlite`) found two:

* **FTS5 shadow tables are `WITHOUT ROWID`.** FTS5 creates ``*_fts_config`` and
  ``*_fts_idx`` as ``CREATE TABLE ... WITHOUT ROWID``, and ``content_hash`` used to
  abort with ``no such column: rowid`` the moment it met one.
* **A `vec0` virtual table needs its extension loaded.** Without it the module is
  unknown and every read fails with ``no such module: vec0``, which aborted both the
  content hash and the dry-run plan.

Both are fixed in `app/workspace/migrate.py`. These tests pin the fixes and, just as
importantly, pin that a workspace made only of ordinary tables hashes **exactly as it
did before** - a changed digest would invalidate every recorded migration manifest.
"""
from __future__ import annotations

import hashlib
import sqlite3

import pytest

from app.workspace.migrate import content_hash, dry_run, unreadable_tables
from shared.workspace_manifest import create_workspace


def _reference_hash_for_rowid_tables(path) -> str:
    """The pre-fix algorithm, valid only for tables that all have a rowid.

    Keeping a copy here is the point of the test: if the new implementation ever
    changes the digest of an ordinary workspace, this comparison fails.
    """
    hasher = hashlib.sha256()
    connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        names = [
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' "
                "AND name NOT LIKE 'sqlite_%' ORDER BY name"
            )
        ]
        for name in names:
            hasher.update(b"table\0")
            hasher.update(name.encode("utf-8"))
            for row in connection.execute(f'SELECT * FROM "{name}" ORDER BY rowid'):
                for value in row:
                    if isinstance(value, bytes):
                        hasher.update(b"b")
                        hasher.update(value)
                    else:
                        hasher.update(b"s")
                        hasher.update(repr(value).encode("utf-8"))
    finally:
        connection.close()
    return hasher.hexdigest()


def _make_plain_db(path) -> None:
    connection = sqlite3.connect(path)
    connection.execute("CREATE TABLE claims (id INTEGER PRIMARY KEY, body TEXT)")
    connection.execute("INSERT INTO claims (body) VALUES ('radius 6371 km')")
    connection.execute("CREATE TABLE blobs (id INTEGER PRIMARY KEY, payload BLOB)")
    connection.execute("INSERT INTO blobs (payload) VALUES (?)", (b"\x00\x01\x02",))
    connection.commit()
    connection.close()


def test_plain_workspace_hashes_exactly_as_before(tmp_path) -> None:
    """Backwards compatibility: an ordinary workspace must keep its old digest."""
    db = tmp_path / "plain.sqlite"
    _make_plain_db(db)
    assert content_hash(db) == _reference_hash_for_rowid_tables(db)
    assert unreadable_tables(db) == []


def test_content_hash_handles_without_rowid_tables(tmp_path) -> None:
    """FTS5 shadow tables are WITHOUT ROWID; hashing must not abort on them."""
    db = tmp_path / "rowidless.sqlite"
    connection = sqlite3.connect(db)
    connection.execute(
        "CREATE TABLE kv (k TEXT PRIMARY KEY, v TEXT) WITHOUT ROWID"
    )
    connection.execute("INSERT INTO kv (k, v) VALUES ('a', '1'), ('b', '2')")
    connection.execute("CREATE TABLE notes (id INTEGER PRIMARY KEY, body TEXT)")
    connection.execute("INSERT INTO notes (body) VALUES ('a note')")
    connection.commit()
    connection.close()

    first = content_hash(db)
    assert isinstance(first, str) and len(first) == 64
    assert content_hash(db) == first, "hashing must be deterministic"
    assert unreadable_tables(db) == [], "a WITHOUT ROWID table is still readable"


def test_the_old_rowid_only_hash_cannot_read_a_without_rowid_table(tmp_path) -> None:
    """RED pin: the pre-fix algorithm this change replaced genuinely fails.

    Without this, the fix could be reverted and every other test here would still
    pass, because they only exercise the new implementation.
    """
    db = tmp_path / "red.sqlite"
    connection = sqlite3.connect(db)
    connection.execute("CREATE TABLE kv (k TEXT PRIMARY KEY, v TEXT) WITHOUT ROWID")
    connection.execute("INSERT INTO kv (k, v) VALUES ('a', '1')")
    connection.commit()
    connection.close()
    with pytest.raises(sqlite3.OperationalError):
        _reference_hash_for_rowid_tables(db)


def test_content_hash_still_detects_a_change_in_a_without_rowid_table(tmp_path) -> None:
    db = tmp_path / "rowidless2.sqlite"
    connection = sqlite3.connect(db)
    connection.execute("CREATE TABLE kv (k TEXT PRIMARY KEY, v TEXT) WITHOUT ROWID")
    connection.execute("INSERT INTO kv (k, v) VALUES ('a', '1')")
    connection.commit()
    before = content_hash(db)
    connection.execute("UPDATE kv SET v = '2' WHERE k = 'a'")
    connection.commit()
    connection.close()
    assert content_hash(db) != before


def test_content_hash_is_stable_across_vacuum_into(tmp_path) -> None:
    """The documented property: a VACUUM INTO snapshot keeps the logical hash."""
    db = tmp_path / "source.sqlite"
    connection = sqlite3.connect(db)
    connection.execute("CREATE TABLE kv (k TEXT PRIMARY KEY, v TEXT) WITHOUT ROWID")
    connection.execute("INSERT INTO kv (k, v) VALUES ('a', '1'), ('b', '2')")
    connection.execute("CREATE TABLE notes (id INTEGER PRIMARY KEY, body TEXT)")
    connection.execute("INSERT INTO notes (body) VALUES ('kept')")
    connection.commit()
    snapshot = tmp_path / "snapshot.sqlite"
    connection.execute("VACUUM INTO ?", (str(snapshot),))
    connection.close()
    assert content_hash(snapshot) == content_hash(db)


def test_dry_run_plans_a_legacy_db_containing_fts_shadow_tables(tmp_path) -> None:
    """An FTS5 table brings WITHOUT ROWID shadow tables into the plan."""
    db = tmp_path / "fts.sqlite"
    connection = sqlite3.connect(db)
    connection.execute("CREATE TABLE documents (id INTEGER PRIMARY KEY, body TEXT)")
    connection.execute("INSERT INTO documents (body) VALUES ('searchable text')")
    connection.execute("CREATE VIRTUAL TABLE documents_fts USING fts5(body)")
    connection.execute("INSERT INTO documents_fts (body) VALUES ('searchable text')")
    connection.commit()
    connection.close()

    workspace = tmp_path / "ws"
    create_workspace(tmp_path, "ws")
    result = dry_run(db, workspace)
    assert result["status"] == "ok"
    assert result["skipped"] is False
    plan = result["plan"]
    names = {entry["name"] for entry in plan["tables"]}
    assert "documents" in names
    assert "documents_fts" in names
    assert plan["unreadable_tables"] == []
    assert content_hash(db)


def test_unreadable_table_is_reported_when_its_module_is_absent(tmp_path, monkeypatch) -> None:
    """A virtual table whose module cannot load is reported, not fatal."""
    sqlite_vec = pytest.importorskip("sqlite_vec")
    db = tmp_path / "vec.sqlite"
    connection = sqlite3.connect(db)
    connection.enable_load_extension(True)
    sqlite_vec.load(connection)
    connection.execute("CREATE VIRTUAL TABLE vectors USING vec0(embedding float[4])")
    connection.execute("INSERT INTO vectors (embedding) VALUES (?)", (b"\x00" * 16,))
    connection.execute("CREATE TABLE notes (id INTEGER PRIMARY KEY, body TEXT)")
    connection.commit()
    connection.close()

    # With the extension available it is readable and hashed.
    assert unreadable_tables(db) == []

    def _unavailable(_connection):
        raise RuntimeError("extension unavailable in this environment")

    monkeypatch.setattr(sqlite_vec, "load", _unavailable)
    assert unreadable_tables(db) == ["vectors"]
    # The hash must still be produced rather than raising.
    assert len(content_hash(db)) == 64
