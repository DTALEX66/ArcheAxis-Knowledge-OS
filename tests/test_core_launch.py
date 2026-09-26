"""R13 (second slice): stop, save/restore and hash-to-tested-commit binding.

The launcher is allowed to be convenient, never credulous. These tests pin the
refusals that matter more than the happy path:

  * stop kills only a pid it can identify as the Core; a recycled pid is refused;
  * backup/restore SQL is delegated to the Rust Core writer, never Python sqlite;
  * restore preserves the replaced canonical workspace and refuses a backup whose
    application identity or recorded hash does not match;
  * a manifest refuses to describe a commit while tracked files are dirty, and a
    missing artifact is a named failure, not a silent omission.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
MODULE = REPO / "scripts" / "launch" / "core_launch.py"


def _load():
    spec = importlib.util.spec_from_file_location("core_launch_under_test", MODULE)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


launcher = _load()


def test_probe_does_not_use_persistent_database_or_session(tmp_path, monkeypatch, capsys):
    legacy = tmp_path / 'legacy-launch'
    legacy.mkdir()
    database = legacy / 'core.sqlite'
    database.write_bytes(b'preserved synthetic database')
    state = legacy / 'core-launch.json'
    state.write_text('{"pid": 1, "fixture": true}', encoding='utf-8')
    before = state.read_bytes()
    binary = tmp_path / 'core.exe'
    binary.write_bytes(b'fixture')
    seen = []

    class Child:
        pid = 123456

        def kill(self):
            pass

        def wait(self):
            return 0

    def spawn(db, port):
        seen.append(db)
        return Child(), {}

    monkeypatch.setattr(launcher, 'RUNDIR', legacy)
    monkeypatch.setattr(launcher, 'STATE_PATH', state)
    monkeypatch.setattr(launcher, 'CORE_BINARY', binary)
    monkeypatch.setattr(launcher, 'dependencies', lambda: [])
    monkeypatch.setattr(launcher, 'port_in_use', lambda port: False)
    monkeypatch.setattr(launcher, 'spawn_core', spawn)
    monkeypatch.setattr(launcher, 'wait_ready', lambda child: '12345')
    assert launcher.main(['--probe']) == 0
    assert seen[0] != database
    assert seen[0].is_relative_to(Path(os.environ['ARCHEAXIS_RUN_ROOT']) / 'artifacts')
    assert state.read_bytes() == before
    assert database.read_bytes() == b'preserved synthetic database'
    assert json.loads(capsys.readouterr().out)['ok'] is True


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


# -------------------------------------------------------- Core-owned backup


def _stub_core(monkeypatch, tmp_path, *, maintenance_result=None):
    binary = tmp_path / "archeaxis-api.exe"
    binary.write_bytes(b"core fixture")
    monkeypatch.setattr(launcher, "CORE_BINARY", binary)
    calls = []

    def run(command, **kwargs):
        calls.append(command)
        if command[1] == "--maintenance-backup":
            Path(command[3]).write_bytes(b"rust-owned canonical backup")
            Path(command[3] + ".objects").mkdir()
            result = {
                "ok": True,
                "schema_version": "5",
                "objects_directory": command[3] + ".objects",
            }
        else:
            result = maintenance_result or {
                "ok": True,
                "verified": True,
                "preserved_previous": str(tmp_path / "core.pre-restore.sqlite"),
                "preserved_previous_sha256": "b" * 64,
            }
            if result.get("ok") and result.get("preserved_previous"):
                Path(result["preserved_previous"]).write_bytes(b"previous database snapshot")
        return subprocess.CompletedProcess(command, 0 if result["ok"] else 1,
                                            json.dumps(result), "" if result["ok"] else "Core refused")

    monkeypatch.setattr(launcher.subprocess, "run", run)
    return binary, calls


def test_launcher_backup_delegates_database_work_to_rust_core(tmp_path, monkeypatch):
    db = tmp_path / "core.sqlite"
    db.write_bytes(b"database fixture; launcher must not parse it")
    binary, calls = _stub_core(monkeypatch, tmp_path)
    code, report = launcher.backup_database(db, tmp_path / "backups", state_path=tmp_path / "none.json")

    assert code == 0 and report["backed_up"] is True
    assert calls[0][:3] == [str(binary), "--maintenance-backup", str(db)]
    backup = Path(report["backup"])
    assert backup.read_bytes() == b"rust-owned canonical backup"
    assert Path(str(backup) + ".objects").is_dir()
    assert report["backup_sha256"] == _sha(backup)
    assert json.loads(Path(str(backup) + ".meta.json").read_text(encoding="utf-8"))["app_id"] == "archeaxis.core"
    assert db.read_bytes() == b"database fixture; launcher must not parse it"


def test_backup_refuses_while_core_is_recorded_as_running(tmp_path, monkeypatch):
    db = tmp_path / "core.sqlite"
    db.write_bytes(b"db")
    _, calls = _stub_core(monkeypatch, tmp_path)
    state = tmp_path / "core-launch.json"
    state.write_text(json.dumps({"pid": os.getpid()}), encoding="utf-8")
    code, report = launcher.backup_database(db, tmp_path / "backups", state_path=state)
    assert code == 5 and report["backed_up"] is False
    assert calls == []


def test_restore_validates_receipt_then_delegates_to_rust_core(tmp_path, monkeypatch):
    db = tmp_path / "core.sqlite"
    db.write_bytes(b"database fixture")
    backup = tmp_path / "backup.sqlite"
    backup.write_bytes(b"canonical snapshot")
    digest = _sha(backup)
    Path(str(backup) + ".sha256").write_text(f"{digest}  {backup.name}\n", encoding="utf-8")
    Path(str(backup) + ".meta.json").write_text(json.dumps({
        "schema": "archeaxis.core-backup/v1", "app_id": "archeaxis.core", "backup_sha256": digest,
    }), encoding="utf-8")
    binary, calls = _stub_core(monkeypatch, tmp_path)

    code, report = launcher.restore_database(db, backup, state_path=tmp_path / "none.json")

    assert code == 0 and report["restored"] is True
    assert calls == [[str(binary), "--maintenance-restore", str(db), str(backup)]]
    assert report["sidecar_matched"] is True
    assert report["preserved_previous_sha256"] == _sha(Path(report["preserved_previous"]))


def test_restore_refuses_hash_mismatch_without_calling_core(tmp_path, monkeypatch):
    db = tmp_path / "core.sqlite"
    db.write_bytes(b"keep")
    backup = tmp_path / "backup.sqlite"
    backup.write_bytes(b"snapshot")
    Path(str(backup) + ".sha256").write_text(f"{'0' * 64}  {backup.name}\n", encoding="utf-8")
    Path(str(backup) + ".meta.json").write_text(json.dumps({
        "schema": "archeaxis.core-backup/v1", "app_id": "archeaxis.core", "backup_sha256": _sha(backup),
    }), encoding="utf-8")
    _stub_core(monkeypatch, tmp_path)
    code, report = launcher.restore_database(db, backup, state_path=tmp_path / "none.json")
    assert code == 7 and report["restored"] is False
    assert db.read_bytes() == b"keep"


def test_launcher_has_no_sqlite_driver_or_sql_operations():
    source = MODULE.read_text(encoding="utf-8")
    assert "import sqlite3" not in source
    assert "VACUUM INTO" not in source
    assert "sqlite3.connect" not in source


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
