"""A WAL database left behind by a killed writer is recovered at the next app start.

`docs/current/AAOS01-CROSS-STACK-WAL-BLOCKER.md` records a hard cross-stack constraint: the Rust
Core runs WAL, its `-wal`/`-shm` sidecars appear, and the Python side then refuses to read the same
database — from which it concluded that the two stacks cannot share one file at all.

The first half is true and the conclusion does not follow. `backup._require_offline_database`, which
`prepare_runtime_database` runs on every app start after taking the sole runtime lease, opens the
database read-write (which recovers a residual WAL), runs `wal_checkpoint(TRUNCATE)`, proves no other
writer holds it with `BEGIN EXCLUSIVE`, and removes the sidecars. So the obstacle is not the sidecar
files: it is a *live* writer holding the database, which is a deliberate refusal rather than an
inability. These tests hold each half of that apart.

Both cases are reproduced with real files and real processes — a killed writer really does leave a
non-empty WAL — because the difference between "sidecars exist" and "a writer holds it" is the whole
point, and a mock would erase it.
"""

from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

# Run in a child that dies without closing, the way a killed Core leaves its WAL behind.
_KILLED_WRITER = """
import os, sqlite3, sys
connection = sqlite3.connect(sys.argv[1])
connection.execute("PRAGMA journal_mode=WAL")
connection.execute("CREATE TABLE IF NOT EXISTS notes(id INTEGER PRIMARY KEY, body TEXT)")
connection.execute("INSERT INTO notes(body) VALUES('written but not checkpointed')")
connection.commit()
os._exit(0)
"""


def kill_a_writer(database: Path) -> None:
    """Leave a WAL database exactly as a killed writer leaves it: sidecars, content not checkpointed."""
    finished = subprocess.run([sys.executable, "-B", "-c", _KILLED_WRITER, str(database)],
                              capture_output=True, text=True)
    assert finished.returncode == 0, finished.stderr
    assert database.with_name(database.name + "-wal").is_file(), \
        "the child was supposed to die before checkpointing; there is no WAL to recover"


def test_a_killed_writers_sidecars_are_recovered_at_the_next_start(tmp_path, monkeypatch):
    from shared import backup

    database = tmp_path / "archeaxis.sqlite"
    kill_a_writer(database)
    wal = database.with_name(database.name + "-wal")
    assert wal.stat().st_size > 0, "the WAL must hold uncheckpointed frames for this to mean anything"

    monkeypatch.setattr(backup, "DB_PATH", database)
    # This is what the app runs on startup, after acquiring the sole runtime lease.
    backup.prepare_runtime_database()

    assert not wal.exists(), "the residual WAL should be checkpointed away"
    assert not database.with_name(database.name + "-shm").exists()
    # And the row the killed writer committed is still there — recovery, not discard.
    with sqlite3.connect(str(database)) as connection:
        assert connection.execute("SELECT body FROM notes").fetchone()[0] == (
            "written but not checkpointed")


def test_a_live_writer_is_refused_because_it_is_live_and_not_because_of_a_sidecar(tmp_path, monkeypatch):
    from shared import backup

    database = tmp_path / "archeaxis.sqlite"
    with sqlite3.connect(str(database)) as connection:
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("CREATE TABLE notes(id INTEGER PRIMARY KEY, body TEXT)")

    holder = sqlite3.connect(str(database), timeout=0.0)
    holder.execute("PRAGMA busy_timeout=0")
    holder.execute("BEGIN EXCLUSIVE")
    try:
        sidecars = [database.with_name(database.name + suffix) for suffix in ("-wal", "-shm")]
        assert any(sidecar.exists() for sidecar in sidecars), "a live writer leaves sidecars"
        monkeypatch.setattr(backup, "DB_PATH", database)
        with pytest.raises(RuntimeError, match="requires the app to be offline"):
            backup.prepare_runtime_database()
    finally:
        holder.rollback()
        holder.close()

    # With the writer gone the same call succeeds: the refusal was about the writer, not the files.
    backup.prepare_runtime_database()
    wal = database.with_name(database.name + "-wal")
    # This connection was opened in-process, so an emptied sidecar can outlive the call here; what
    # must hold either way is that nothing uncheckpointed remains. The fresh-process case above
    # asserts the stronger property, because there the files really are gone.
    assert not wal.exists() or wal.stat().st_size == 0
