"""The gap-filling export composes with the Rust one instead of contradicting it.

Two things have to hold for the pair to be usable: the file the filler writes must be the name the
Rust verifier expects (it rejects any `.jsonl` a manifest does not list), and the digest it stores
must be the value the Rust verifier recomputes — a manifest whose digest does not match its own
contents is rejected before anything is staged.

The digest layout was checked once against a Rust-produced manifest: for the real export, whose
Rust-recorded digest was `5ed6c025aef744f6adcdac2b16f43674de4a9d2933b00be6809953167cb3cbc3`, this
module's algorithm reproduced that exact value. These tests pin the parts that can be checked
without a Rust build; the recorded equality is noted in the round's ledger entry.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sqlite3
import struct
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
FILLER = REPO / "scripts" / "maintenance" / "fill_unqueried_tables.py"


def load_filler():
    spec = importlib.util.spec_from_file_location("fill_unqueried_tables", FILLER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def rust_digest(tables: dict, unqueried: dict) -> str:
    """The Rust `manifest_digest`, written out independently of the module under test."""
    by_bytes = lambda item: item[0].encode("utf-8")
    hasher = hashlib.sha256()
    for name, table in sorted(tables.items(), key=by_bytes):
        hasher.update(name.encode("utf-8"))
        hasher.update(int(table["rows"]).to_bytes(8, "little"))
        hasher.update(str(table["sha256"]).encode("utf-8"))
    for name, reason in sorted(unqueried.items(), key=by_bytes):
        hasher.update(b"unqueried:")
        hasher.update(name.encode("utf-8"))
        hasher.update(str(reason).encode("utf-8"))
    return hasher.hexdigest()


def make_export(tmp_path: Path, *, with_vector: bool) -> tuple[Path, Path]:
    """A database with a readable table, plus optionally a vec0 table, and a Rust-style export."""
    sqlite_vec = pytest.importorskip("sqlite_vec")
    database = tmp_path / "legacy.sqlite"
    connection = sqlite3.connect(str(database))
    try:
        connection.execute("CREATE TABLE notes(id INTEGER PRIMARY KEY, body TEXT)")
        connection.execute("INSERT INTO notes(body) VALUES('kept')")
        if with_vector:
            connection.enable_load_extension(True)
            sqlite_vec.load(connection)
            connection.enable_load_extension(False)
            connection.execute("CREATE VIRTUAL TABLE vec_episodes USING vec0(embedding float[4])")
            connection.execute("INSERT INTO vec_episodes(rowid, embedding) VALUES (1, ?)",
                               (struct.pack("<4f", 1.0, 2.0, 3.0, 4.0),))
        connection.commit()
    finally:
        connection.close()

    out = tmp_path / "export"
    out.mkdir()
    payload = b'{"id": 1, "body": "kept"}\n'
    (out / "notes.jsonl").write_bytes(payload)
    tables = {"notes": {"rows": 1, "sha256": hashlib.sha256(payload).hexdigest()}}
    unqueried = {"vec_episodes": "no such module: vec0"} if with_vector else {}
    (out / "export-manifest.json").write_text(json.dumps({
        "exported_at_unix": 0, "tables": tables, "unqueried_tables": unqueried,
        "manifest_sha256": rust_digest(tables, unqueried),
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return database, out


def test_the_digest_layout_is_pinned_so_a_silent_change_is_caught() -> None:
    """A golden value for the Rust digest layout.

    It is a golden value because the layout must not drift: the Rust verifier recomputes it and
    rejects a manifest that disagrees. The Python side was checked against a real Rust-produced
    manifest — for digest `5ed6c025…` recorded by the Rust export of the legacy store, this
    algorithm reproduced that exact value — so a change here means the two languages have parted.
    """
    tables = {"a": {"rows": 2, "sha256": "d" * 64}, "b": {"rows": 0, "sha256": "c" * 64}}
    unqueried = {"y": "no such table: y", "z": "no such module: vec0"}
    assert rust_digest(tables, unqueried) == (
        "27439e9551da123564da22be495f75b44c8e9a42085e333ed6934d8c58de856d")
    # And the same value whatever order the entries arrive in.
    assert rust_digest(dict(reversed(list(tables.items()))), dict(reversed(list(unqueried.items())))) == (
        "27439e9551da123564da22be495f75b44c8e9a42085e333ed6934d8c58de856d")


@pytest.fixture
def workspace():
    """A scratch directory *inside* the project.

    The tool refuses paths outside it on purpose, and pytest's temporary root is outside this
    worktree, so the fixtures live under the sanctioned ignored development root like every other
    run artifact.
    """
    import shutil
    import uuid

    directory = REPO / ".project-local" / "task-runtime" / f"fill-unqueried-test-{uuid.uuid4().hex[:8]}"
    directory.mkdir(parents=True)
    try:
        yield directory
    finally:
        shutil.rmtree(directory, ignore_errors=True)


def test_the_filler_fills_a_named_gap_and_updates_the_manifest(workspace) -> None:
    database, out = make_export(workspace, with_vector=True)
    before = json.loads((out / "export-manifest.json").read_text(encoding="utf-8"))
    assert before["unqueried_tables"] == {"vec_episodes": "no such module: vec0"}

    finished = subprocess.run([sys.executable, "-B", str(FILLER), str(database), str(out)],
                              capture_output=True, text=True, encoding="utf-8", errors="surrogateescape")
    assert finished.returncode == 0, finished.stdout + finished.stderr

    after = json.loads((out / "export-manifest.json").read_text(encoding="utf-8"))
    assert after["unqueried_tables"] == {}, after["unqueried_tables"]
    assert set(after["tables"]) == {"notes", "vec_episodes"}, after["tables"]
    assert after["tables"]["vec_episodes"]["rows"] == 1

    # The file name is the one the Rust verifier expects to find, and its digest was recomputed.
    written = out / "vec_episodes.jsonl"
    assert written.is_file(), sorted(p.name for p in out.iterdir())
    assert hashlib.sha256(written.read_bytes()).hexdigest() == after["tables"]["vec_episodes"]["sha256"]
    assert after["manifest_sha256"] == rust_digest(after["tables"], after["unqueried_tables"])
    assert after["manifest_sha256"] != before["manifest_sha256"]


def test_a_finished_export_is_left_alone(workspace) -> None:
    database, out = make_export(workspace, with_vector=False)
    before = (out / "export-manifest.json").read_bytes()
    finished = subprocess.run([sys.executable, "-B", str(FILLER), str(database), str(out)],
                              capture_output=True, text=True, encoding="utf-8", errors="surrogateescape")
    assert finished.returncode == 0
    assert "nothing unqueried" in finished.stdout
    assert (out / "export-manifest.json").read_bytes() == before


def test_it_refuses_paths_outside_the_project(tmp_path) -> None:
    database, out = make_export(tmp_path, with_vector=True)
    filler = load_filler()
    with pytest.raises(ValueError):
        filler.reject_private(Path("E:/elsewhere/legacy.sqlite"))
    with pytest.raises(ValueError):
        filler.reject_private(Path.home() / ".codex" / "legacy.sqlite")
    assert filler.reject_private(database) == database.resolve()
