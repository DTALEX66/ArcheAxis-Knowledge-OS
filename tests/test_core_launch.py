"""R13 (second slice): stop, save/restore and hash-to-tested-commit binding.

The launcher is allowed to be convenient, never credulous. These tests pin the
refusals that matter more than the happy path:

  * stop kills only a pid it can identify as the Core; a recycled pid is refused;
  * a backup proves the source database was not touched (sha256 before == after);
  * a restore moves the database it replaces aside instead of deleting it, and it
    refuses a backup that is unreadable or whose recorded hash does not match;
  * a manifest refuses to describe a commit while tracked files are dirty, and a
    missing artifact is a named failure, not a silent omission.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import sqlite3
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
MODULE = REPO / "scripts" / "launch" / "core_launch.py"


def _load():
    spec = importlib.util.spec_from_file_location("core_launch_under_test", MODULE)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


launcher = _load()


def _make_db(path: Path, rows: list[str]) -> None:
    connection = sqlite3.connect(str(path))
    try:
        connection.execute("CREATE TABLE IF NOT EXISTS knowledge(body TEXT)")
        connection.executemany("INSERT INTO knowledge(body) VALUES (?)", [(row,) for row in rows])
        connection.commit()
    finally:
        connection.close()


def _replace_db(path: Path, rows: list[str]) -> None:
    """Move the database on: drop what was there and store something else."""
    connection = sqlite3.connect(str(path))
    try:
        connection.execute("DELETE FROM knowledge")
        connection.executemany("INSERT INTO knowledge(body) VALUES (?)", [(row,) for row in rows])
        connection.commit()
    finally:
        connection.close()


def _rows(path: Path) -> list[str]:
    connection = sqlite3.connect(str(path))
    try:
        return [row[0] for row in connection.execute("SELECT body FROM knowledge ORDER BY body")]
    finally:
        connection.close()


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ---------------------------------------------------------------- dependencies


def test_dependency_report_names_every_check_and_never_hides_a_missing_one():
    checks = launcher.dependencies()
    assert len(checks) == 9
    assert all(set(check) == {"name", "ok", "detail"} for check in checks)
    assert all(isinstance(check["ok"], bool) for check in checks)
    # the repository's own tessdata is what OCR needs; the path is named, not guessed
    language = next(check for check in checks if check["name"] == "ocr language data")
    assert language["detail"] == "tools/tesseract/tessdata/eng.traineddata"


# ---------------------------------------------------------------------- stop


def test_stop_without_a_recorded_session_is_an_idempotent_no_op(tmp_path):
    code, report = launcher.stop_session(tmp_path / "absent.json")
    assert code == 0
    assert report["stopped"] is False
    assert "no launch session recorded" in report["reason"]


def test_stop_clears_a_session_whose_process_is_gone(tmp_path):
    state = tmp_path / "core-launch.json"
    state.write_text(json.dumps({"pid": 999_999_999, "db": "x.sqlite"}), encoding="utf-8")
    code, report = launcher.stop_session(state)
    assert code == 0
    assert report["stopped"] is False
    assert "already gone" in report["reason"]
    assert not state.exists()


def test_stop_refuses_a_pid_that_is_not_the_core(tmp_path):
    """A recorded pid may be reused by an unrelated process: refuse, never kill."""
    state = tmp_path / "core-launch.json"
    state.write_text(json.dumps({"pid": os.getpid(), "db": "x.sqlite"}), encoding="utf-8")
    code, report = launcher.stop_session(state)
    assert code == 4
    assert report["stopped"] is False
    assert report["refused"] is True
    assert "refusing to terminate" in report["reason"]
    # the refused session is left on disk for a human to look at, and we are alive
    assert state.exists()


def test_live_session_is_detected_only_while_the_pid_exists(tmp_path):
    state = tmp_path / "core-launch.json"
    state.write_text(json.dumps({"pid": os.getpid()}), encoding="utf-8")
    assert launcher.live_session(state)["pid"] == os.getpid()
    state.write_text(json.dumps({"pid": 999_999_999}), encoding="utf-8")
    assert launcher.live_session(state) is None


# ------------------------------------------------------------------- backup


def test_backup_copies_content_and_proves_the_source_was_not_touched(tmp_path):
    db = tmp_path / "core.sqlite"
    _make_db(db, ["alpha", "beta"])
    code, report = launcher.backup_database(db, tmp_path / "backups", state_path=tmp_path / "none.json")
    assert code == 0
    assert report["backed_up"] is True
    assert report["source_unchanged"] is True
    assert report["source_sha256_before"] == report["source_sha256_after"]
    backup = Path(report["backup"])
    assert _rows(backup) == ["alpha", "beta"]
    assert report["backup_sha256"] == _sha(backup)
    assert Path(report["sha256_sidecar"]).read_text(encoding="utf-8").startswith(report["backup_sha256"])


def test_backup_refuses_while_the_core_is_recorded_as_running(tmp_path):
    db = tmp_path / "core.sqlite"
    _make_db(db, ["alpha"])
    state = tmp_path / "core-launch.json"
    state.write_text(json.dumps({"pid": os.getpid()}), encoding="utf-8")
    code, report = launcher.backup_database(db, tmp_path / "backups", state_path=state)
    assert code == 5
    assert report["backed_up"] is False
    assert not (tmp_path / "backups").exists()


def test_backup_of_a_missing_database_is_a_named_failure(tmp_path):
    code, report = launcher.backup_database(
        tmp_path / "absent.sqlite", tmp_path / "backups", state_path=tmp_path / "none.json"
    )
    assert code == 6
    assert report["backed_up"] is False
    assert "does not exist" in report["reason"]


# ------------------------------------------------------------------ restore


def test_restore_puts_the_backup_back_and_preserves_what_it_replaced(tmp_path):
    db = tmp_path / "core.sqlite"
    _make_db(db, ["alpha", "beta"])
    code, backup = launcher.backup_database(db, tmp_path / "backups", state_path=tmp_path / "none.json")
    assert code == 0

    _replace_db(db, ["gamma"])  # the database moves on after the backup
    assert _rows(db) == ["gamma"]

    code, report = launcher.restore_database(db, Path(backup["backup"]), state_path=tmp_path / "none.json")
    assert code == 0
    assert report["restored"] is True
    assert report["sidecar_matched"] is True
    assert _rows(db) == ["alpha", "beta"]
    # nothing was deleted: the replaced database is still readable where it was put
    preserved = Path(report["preserved_previous"])
    assert preserved.is_file()
    assert _rows(preserved) == ["gamma"]
    assert report["preserved_previous_sha256"] == _sha(preserved)


def test_restore_refuses_a_backup_whose_hash_disagrees_with_its_record(tmp_path):
    db = tmp_path / "core.sqlite"
    _make_db(db, ["alpha"])
    _, backup = launcher.backup_database(db, tmp_path / "backups", state_path=tmp_path / "none.json")
    backup_path = Path(backup["backup"])
    _replace_db(backup_path, ["tampered"])

    code, report = launcher.restore_database(db, backup_path, state_path=tmp_path / "none.json")
    assert code == 7
    assert report["restored"] is False
    assert report["sidecar_matched"] is False
    assert _rows(db) == ["alpha"]  # the live database was not touched


def test_restore_refuses_a_file_that_is_not_a_database(tmp_path):
    db = tmp_path / "core.sqlite"
    _make_db(db, ["alpha"])
    junk = tmp_path / "not-a-backup.sqlite"
    junk.write_bytes(b"this is not sqlite")
    code, report = launcher.restore_database(db, junk, state_path=tmp_path / "none.json")
    assert code == 7
    assert report["restored"] is False
    assert "not a readable SQLite database" in report["reason"]


def test_restore_refuses_while_the_core_is_recorded_as_running(tmp_path):
    db = tmp_path / "core.sqlite"
    _make_db(db, ["alpha"])
    _, backup = launcher.backup_database(db, tmp_path / "backups", state_path=tmp_path / "none.json")
    state = tmp_path / "core-launch.json"
    state.write_text(json.dumps({"pid": os.getpid()}), encoding="utf-8")
    code, report = launcher.restore_database(db, Path(backup["backup"]), state_path=state)
    assert code == 7
    assert report["restored"] is False
    assert "still running" in report["reason"]


# ----------------------------------------------------------------- manifest


def test_manifest_refuses_a_dirty_tracked_worktree(tmp_path):
    artifact = tmp_path / "core.bin"
    artifact.write_bytes(b"deliverable")
    identity = {
        "tested_source_sha": "a" * 40,
        "tracked_worktree_clean": False,
        "tracked_changes": [" M crates/x.rs"],
        "untracked_present": [],
    }
    code, report = launcher.build_manifest([artifact], tmp_path / "manifest.json", identity=identity)
    assert code == 8
    assert report["written"] is False
    assert report["tracked_changes"] == [" M crates/x.rs"]
    assert not (tmp_path / "manifest.json").exists()


def test_manifest_binds_artifact_hashes_to_the_tested_sha(tmp_path):
    first = tmp_path / "archeaxis-api.exe"
    first.write_bytes(b"binary")
    second = tmp_path / "worker_pdf.py"
    second.write_bytes(b"worker")
    identity = {
        "tested_source_sha": "b" * 40,
        "tracked_worktree_clean": True,
        "tracked_changes": [],
        "untracked_present": ["?? scratch/"],
    }
    out = tmp_path / "manifest.json"
    code, report = launcher.build_manifest([first, second], out, identity=identity)
    assert code == 0
    assert report["written"] is True
    written = json.loads(out.read_text(encoding="utf-8"))
    assert written["tested_source_sha"] == "b" * 40
    assert {entry["name"]: entry["sha256"] for entry in written["artifacts"]} == {
        "archeaxis-api.exe": _sha(first),
        "worker_pdf.py": _sha(second),
    }
    assert written["untracked_present"] == ["?? scratch/"]
    assert any("not a signature" in line for line in written["limitations"])


def test_manifest_refuses_a_missing_artifact(tmp_path):
    code, report = launcher.build_manifest(
        [tmp_path / "absent.exe"],
        tmp_path / "manifest.json",
        identity={
            "tested_source_sha": "c" * 40,
            "tracked_worktree_clean": True,
            "tracked_changes": [],
            "untracked_present": [],
        },
    )
    assert code == 6
    assert report["written"] is False
    assert "does not exist" in report["reason"]


def test_manifest_refuses_when_no_artifact_is_given(tmp_path):
    code, report = launcher.build_manifest(
        [],
        tmp_path / "manifest.json",
        identity={
            "tested_source_sha": "c" * 40,
            "tracked_worktree_clean": True,
            "tracked_changes": [],
            "untracked_present": [],
        },
    )
    assert code == 6
    assert report["written"] is False
