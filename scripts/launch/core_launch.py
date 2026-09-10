"""ArcheAxis one-command launcher, diagnostics, stop and save/restore (R13).

Does what a candidate package entry point must do, without pretending to be one:

  --check      dependency + port diagnostics (never an empty success)
  --probe      launch the Core, report its readiness port, then stop it
  (no flag)    start the Core and keep it in the foreground until interrupted
  --stop       stop the launch session this tool recorded earlier
  --backup     consistent copy of the Core database (VACUUM INTO) plus its hash
  --restore    put a backup back, preserving the database it replaces
  --manifest   bind deliverable hashes to the tested source commit (refuses to
               emit a manifest from a dirty tracked worktree)

Every path is resolved relative to the repository root, never from an installer
directory, and no path is guessed from a shell. A missing dependency, a refused
action or a mismatched hash is reported as a named failure with an exit code.

Honesty rules kept here:
  * the launcher only kills a pid it can identify as the Core; an unrelated
    process that reuses a recorded pid is refused, not killed;
  * a backup proves it did not touch its source (sha256 before == after);
  * a restore never deletes the database it replaces, it moves it aside;
  * a manifest refuses to claim a tested commit while tracked files are dirty.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
import secrets
import shutil
import socket
import sqlite3
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CORE_BINARY = REPO / ".project-local" / "build" / "cargo" / "debug" / "archeaxis-api.exe"
RUNDIR = REPO / ".project-local" / "runs" / "launch"
STATE_PATH = RUNDIR / "core-launch.json"
CORE_IMAGE_STEM = "archeaxis-api"


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def port_in_use(port: int) -> bool:
    with socket.socket() as probe:
        probe.settimeout(0.5)
        return probe.connect_ex(("127.0.0.1", port)) == 0


def dependencies() -> list[dict]:
    """The things the Core needs before it can serve, checked by name."""
    checks = [
        ("core binary", CORE_BINARY.is_file(), str(CORE_BINARY)),
        ("python interpreter", Path(sys.executable).is_file(), sys.executable),
        ("text worker", (REPO / "services/python-workers/document/worker_text.py").is_file(), "worker_text.py"),
        ("pdf worker", (REPO / "services/python-workers/document/worker_pdf.py").is_file(), "worker_pdf.py"),
        ("ocr worker", (REPO / "services/python-workers/vision/worker_ocr.py").is_file(), "worker_ocr.py"),
        ("pdf engine", _importable("pymupdf") or _importable("fitz"), "pymupdf"),
        ("ocr engine", _which("tesseract"), "tesseract executable"),
        (
            "ocr language data",
            (REPO / "tools/tesseract/tessdata/eng.traineddata").is_file(),
            "tools/tesseract/tessdata/eng.traineddata",
        ),
        ("cargo wrapper", (REPO / ".project-local/runs/cargo-full-workspace.bat").is_file(), "cargo-full-workspace.bat"),
    ]
    return [{"name": name, "ok": bool(ok), "detail": detail} for name, ok, detail in checks]


def _importable(name: str) -> bool:
    try:
        __import__(name)
        return True
    except ImportError:
        return False


def _which(name: str) -> bool:
    from shutil import which

    return which(name) is not None


# --------------------------------------------------------------------------
# hashing and source identity
# --------------------------------------------------------------------------


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git(*args: str) -> tuple[int, str]:
    result = subprocess.run(
        ["git", *args], cwd=str(REPO), capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    return result.returncode, (result.stdout or "").strip()


def source_identity() -> dict:
    """The commit a deliverable is built from, plus tracked-tree cleanliness."""
    code, head = git("rev-parse", "HEAD")
    sha = head if code == 0 else None
    code, dirty = git("status", "--porcelain", "--untracked-files=no")
    tracked_dirty = [line for line in dirty.splitlines() if line.strip()] if code == 0 else []
    code, untracked = git("status", "--porcelain", "--untracked-files=all")
    untracked_only = [line for line in untracked.splitlines() if line.startswith("??")] if code == 0 else []
    return {
        "tested_source_sha": sha,
        "tracked_worktree_clean": not tracked_dirty and code == 0,
        "tracked_changes": tracked_dirty,
        # untracked paths are recorded as a limitation, they never change the sha
        "untracked_present": untracked_only,
    }


# --------------------------------------------------------------------------
# launch session bookkeeping
# --------------------------------------------------------------------------


def record_session(state_path: Path, pid: int, port: int, db: Path) -> dict:
    state = {
        "pid": pid,
        "port": port,
        "db": str(db),
        "source_sha": source_identity()["tested_source_sha"],
        "started_at": utc_stamp(),
    }
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    return state


def read_session(state_path: Path) -> dict | None:
    if not state_path.is_file():
        return None
    with contextlib.suppress(Exception):
        return json.loads(state_path.read_text(encoding="utf-8"))
    return {"pid": None, "unreadable": True}


def clear_session(state_path: Path) -> None:
    with contextlib.suppress(FileNotFoundError):
        state_path.unlink()


def pid_alive(pid: int | None) -> bool:
    if not pid or pid <= 0:
        return False
    if pid == os.getpid():
        return True
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False
    except Exception:  # pragma: no cover - platform specific
        return False


def process_image(pid: int) -> str | None:
    """Image name for a pid, or None when the pid cannot be inspected."""
    result = subprocess.run(
        ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    for line in (result.stdout or "").splitlines():
        fields = [field.strip().strip('"') for field in line.split('","')]
        if fields and fields[0]:
            return fields[0].strip('"')
    return None


def live_session(state_path: Path = STATE_PATH) -> dict | None:
    """The recorded session when its process is still alive, else None."""
    state = read_session(state_path)
    if not state or state.get("unreadable"):
        return None
    return state if pid_alive(state.get("pid")) else None


def stop_session(state_path: Path = STATE_PATH, timeout: float = 10.0) -> tuple[int, dict]:
    """Stop only the pid we started; refuse to kill anything else."""
    report: dict = {"action": "stop", "state_path": str(state_path)}
    state = read_session(state_path)
    if state is None:
        report.update({"stopped": False, "reason": "no launch session recorded by this tool"})
        return 0, report
    if state.get("unreadable"):
        report.update({"stopped": False, "reason": "the recorded session file could not be read", "exit": 4})
        return 4, report

    pid = state.get("pid")
    report["recorded_pid"] = pid
    report["recorded_db"] = state.get("db")
    if not pid_alive(pid):
        clear_session(state_path)
        report.update({"stopped": False, "reason": "the recorded process is already gone"})
        return 0, report

    image = process_image(pid)
    report["recorded_image"] = image
    if image is None or CORE_IMAGE_STEM not in image.lower():
        # a recycled pid must never be killed on our account
        report.update(
            {
                "stopped": False,
                "refused": True,
                "reason": f"pid {pid} is not the Core (image={image!r}); refusing to terminate it",
            }
        )
        return 4, report

    subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True, text=True)
    deadline = time.time() + timeout
    while time.time() < deadline and pid_alive(pid):
        time.sleep(0.2)
    if pid_alive(pid):
        report.update({"stopped": False, "reason": f"pid {pid} is still alive after {timeout:.0f}s"})
        return 4, report
    clear_session(state_path)
    report.update({"stopped": True})
    return 0, report


# --------------------------------------------------------------------------
# save and restore
# --------------------------------------------------------------------------


def _free_path(path: Path) -> Path:
    """A path that does not exist yet, so nothing is ever overwritten."""
    if not path.exists():
        return path
    for index in range(1, 1000):
        candidate = path.with_name(f"{path.name}.{index}")
        if not candidate.exists():
            return candidate
    raise RuntimeError(f"cannot find a free name near {path}")


def _read_only_uri(path: Path) -> str:
    """A `file:` URI that forbids SQLite to write to `path`."""
    return path.resolve().as_uri() + "?mode=ro"


def _wal_facts(db: Path) -> dict:
    """Side-car journal facts, so a change to the main file can be explained."""
    facts = {}
    for suffix in ("-wal", "-shm"):
        side = Path(str(db) + suffix)
        facts[f"{suffix.lstrip('-')}_bytes"] = side.stat().st_size if side.is_file() else None
    return facts


def backup_database(db: Path, out_dir: Path, state_path: Path = STATE_PATH) -> tuple[int, dict]:
    """Copy the Core database with VACUUM INTO and prove the source was untouched."""
    report: dict = {"action": "backup", "db": str(db), "out_dir": str(out_dir)}
    session = live_session(state_path)
    if session:
        report.update(
            {
                "backed_up": False,
                "reason": "the Core launch session is still running; stop it before backing up",
                "running_pid": session.get("pid"),
            }
        )
        return 5, report
    if not db.is_file():
        report.update({"backed_up": False, "reason": "the Core database does not exist yet"})
        return 6, report

    before = sha256_file(db)
    wal_before = _wal_facts(db)
    out_dir.mkdir(parents=True, exist_ok=True)
    target = _free_path(out_dir / f"core-backup-{utc_stamp()}.sqlite")
    connection = None
    opened_read_only = True
    try:
        try:
            connection = sqlite3.connect(_read_only_uri(db), uri=True)
        except sqlite3.Error:
            # a hot write-ahead log can refuse a read-only open; opening normally
            # is then the only way to get a consistent copy, and the receipts
            # below will show that the source file changed.
            connection = sqlite3.connect(str(db))
            opened_read_only = False
        connection.execute("VACUUM INTO ?", (str(target),))
    except sqlite3.Error as error:
        report.update({"backed_up": False, "reason": f"sqlite refused the backup: {error}"})
        return 5, report
    finally:
        if connection is not None:
            connection.close()

    after = sha256_file(db)
    wal_after = _wal_facts(db)
    digest = sha256_file(target)
    sidecar = target.with_name(target.name + ".sha256")
    sidecar.write_text(f"{digest}  {target.name}\n", encoding="utf-8")
    report.update(
        {
            "backed_up": True,
            "backup": str(target),
            "backup_sha256": digest,
            "backup_bytes": target.stat().st_size,
            "sha256_sidecar": str(sidecar),
            "opened_read_only": opened_read_only,
            "source_sha256_before": before,
            "source_sha256_after": after,
            "source_unchanged": before == after,
            "wal_before": wal_before,
            "wal_after": wal_after,
        }
    )
    if before != after:
        # do not claim the source was untouched: say what was observed instead
        checkpointed = wal_before["wal_bytes"] and not wal_after["wal_bytes"]
        report["source_change_note"] = (
            "sqlite had a write-ahead log to replay/checkpoint when the database was opened "
            "(wal_bytes "
            f"{wal_before['wal_bytes']} -> {wal_after['wal_bytes']}); the backup reads the database "
            "and writes no rows, but a checkpoint rewrites the main file"
            if checkpointed
            else "the source file changed while it was being read; treat this backup as unproven"
        )
    return 0, report


def restore_database(db: Path, backup: Path, state_path: Path = STATE_PATH) -> tuple[int, dict]:
    """Put a backup back in place, moving the current database aside first."""
    report: dict = {"action": "restore", "db": str(db), "backup": str(backup)}
    session = live_session(state_path)
    if session:
        report.update(
            {
                "restored": False,
                "reason": "the Core launch session is still running; stop it before restoring",
                "running_pid": session.get("pid"),
            }
        )
        return 7, report
    if not backup.is_file():
        report.update({"restored": False, "reason": "the backup file does not exist"})
        return 6, report

    try:
        # read-only: validating a backup must not modify the file being validated
        check = sqlite3.connect(_read_only_uri(backup), uri=True)
        try:
            check.execute("PRAGMA schema_version").fetchone()
        finally:
            check.close()
    except sqlite3.Error as error:
        report.update({"restored": False, "reason": f"the backup is not a readable SQLite database: {error}"})
        return 7, report

    backup_digest = sha256_file(backup)
    sidecar = backup.with_name(backup.name + ".sha256")
    if sidecar.is_file():
        expected = sidecar.read_text(encoding="utf-8").split()[0]
        report["sidecar_sha256"] = expected
        report["sidecar_matched"] = expected == backup_digest
        if expected != backup_digest:
            report.update({"restored": False, "reason": "the backup hash does not match its recorded hash"})
            return 7, report
    else:
        report["sidecar_sha256"] = None
        report["sidecar_matched"] = None

    preserved: Path | None = None
    preserved_journals: list[str] = []
    if db.exists():
        preserved = _free_path(db.with_name(f"{db.name}.replaced-{utc_stamp()}"))
        db.replace(preserved)
    # a write-ahead log belongs to the database it was written for: leaving it
    # behind would make SQLite replay an old journal into the restored file
    for suffix in ("-wal", "-shm"):
        side = Path(str(db) + suffix)
        if side.is_file():
            if preserved is not None:
                aside = _free_path(Path(str(preserved) + suffix))
            else:
                aside = _free_path(db.with_name(f"{db.name}.orphaned-{utc_stamp()}{suffix}"))
            side.replace(aside)
            preserved_journals.append(str(aside))
    db.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(backup, db)
    restored_digest = sha256_file(db)
    report.update(
        {
            "restored": restored_digest == backup_digest,
            "preserved_previous": str(preserved) if preserved else None,
            "preserved_previous_sha256": sha256_file(preserved) if preserved else None,
            "preserved_journals": preserved_journals,
            "backup_sha256": backup_digest,
            "restored_sha256": restored_digest,
            "bytes": db.stat().st_size,
        }
    )
    if not report["restored"]:
        report["reason"] = "the restored file does not hash to the backup"
        return 7, report
    return 0, report


# --------------------------------------------------------------------------
# package manifest: deliverable hashes bound to the tested commit
# --------------------------------------------------------------------------


def build_manifest(artifacts: list[Path], out: Path, identity: dict | None = None) -> tuple[int, dict]:
    identity = identity or source_identity()
    report: dict = {
        "manifest_version": 1,
        "generated_at": utc_stamp(),
        "tested_source_sha": identity.get("tested_source_sha"),
        "tracked_worktree_clean": identity.get("tracked_worktree_clean"),
        "limitations": [
            "a hash binds an artifact to a tested commit; it is not a signature and not an installer",
            "untracked paths are recorded but never change the tested sha",
        ],
        "untracked_present": identity.get("untracked_present", []),
    }
    if not identity.get("tested_source_sha"):
        report.update({"written": False, "reason": "the source commit could not be read"})
        return 8, report
    if not identity.get("tracked_worktree_clean"):
        report.update(
            {
                "written": False,
                "reason": "tracked files are modified; a manifest must describe a tested commit",
                "tracked_changes": identity.get("tracked_changes", []),
            }
        )
        return 8, report
    if not artifacts:
        report.update({"written": False, "reason": "no artifact was given"})
        return 6, report

    entries = []
    for artifact in artifacts:
        if not artifact.is_file():
            report.update({"written": False, "reason": f"artifact does not exist: {artifact}"})
            return 6, report
        entries.append(
            {
                "path": str(artifact),
                "name": artifact.name,
                "bytes": artifact.stat().st_size,
                "sha256": sha256_file(artifact),
            }
        )
    report["artifacts"] = entries
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report["written"] = True
    report["manifest_path"] = str(out)
    return 0, report


# --------------------------------------------------------------------------
# launching
# --------------------------------------------------------------------------


def spawn_core(db: Path, port: int) -> tuple[subprocess.Popen, dict]:
    """Start the Core with a fresh launch claim and return (process, claim)."""
    claim = {
        "launch_token": secrets.token_hex(32),
        "session_id": secrets.token_hex(16),
    }
    child = subprocess.Popen(
        [str(CORE_BINARY), str(db), str(port)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
    )
    child.stdin.write(json.dumps(claim) + "\n")
    child.stdin.flush()
    child.stdin.close()  # the Core reads its claim to EOF
    return child, claim


def wait_ready(child: subprocess.Popen, seconds: float = 20.0) -> str | None:
    deadline = time.time() + seconds
    while time.time() < deadline:
        line = child.stdout.readline()
        if not line:
            if child.poll() is not None:
                return None
            continue
        if "127.0.0.1:" in line:
            return line.split("127.0.0.1:", 1)[1].split()[0].strip()
    return None


def main(argv: list[str] | None = None) -> int:
    with contextlib.suppress(Exception):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="dependency and port diagnostics only")
    parser.add_argument("--probe", action="store_true", help="launch, report the readiness port, then stop")
    parser.add_argument("--stop", action="store_true", help="stop the launch session recorded earlier")
    parser.add_argument("--backup", action="store_true", help="consistent copy of the Core database plus its hash")
    parser.add_argument("--restore", action="store_true", help="restore a backup, preserving the current database")
    parser.add_argument("--manifest", action="store_true", help="bind artifact hashes to the tested commit")
    parser.add_argument("--from", dest="source", type=Path, help="backup file to restore from")
    parser.add_argument("--artifact", type=Path, action="append", default=[], help="deliverable to hash (repeatable)")
    parser.add_argument("--out", type=Path, help="output file or directory for backup/manifest")
    parser.add_argument("--db", type=Path, default=RUNDIR / "core.sqlite")
    parser.add_argument("--port", type=int, default=0)
    args = parser.parse_args(argv)

    if args.stop:
        code, report = stop_session()
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return code

    if args.backup:
        out_dir = args.out or (RUNDIR / "backups")
        code, report = backup_database(args.db, out_dir)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return code

    if args.restore:
        if args.source is None:
            print(json.dumps({"action": "restore", "restored": False, "reason": "--from is required"}, ensure_ascii=False))
            return 2
        code, report = restore_database(args.db, args.source)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return code

    if args.manifest:
        out = args.out or (RUNDIR / "package-manifest.json")
        code, report = build_manifest(list(args.artifact), out)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return code

    report: dict = {"repository": str(REPO)}
    checks = dependencies()
    report["dependencies"] = checks
    report["dependencies_ok"] = all(c["ok"] for c in checks)

    for name, port in (("deeptutor backend", 8001), ("deeptutor frontend", 3782), ("ollama", 11434)):
        report[f"port_{port}_{name.replace(' ', '_')}"] = port_in_use(port)

    if args.check:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["dependencies_ok"] else 1

    if not CORE_BINARY.is_file():
        report["error"] = "the Core binary is not built; run the cargo wrapper first"
        print(json.dumps(report, ensure_ascii=False))
        return 2

    args.db.parent.mkdir(parents=True, exist_ok=True)
    port = args.port or free_port()
    report["requested_port"] = port
    child, claim = spawn_core(args.db, port)
    try:
        ready = wait_ready(child)
        report["ready_port"] = ready
        report["claim_actor"] = "human (default launch claim)"
        if ready is None:
            report["error"] = "the Core did not report readiness"
            return 3
        report["ok"] = True
        report["session_state"] = str(record_session(STATE_PATH, child.pid, int(ready), args.db))
        print(json.dumps(report, ensure_ascii=False))
        if args.probe:
            return 0
        print(f"ArcheAxis Core listening on http://127.0.0.1:{ready} - press Ctrl+C to stop", file=sys.stderr)
        try:
            return child.wait()
        except KeyboardInterrupt:
            return 0
    finally:
        child.kill()
        child.wait()
        clear_session(STATE_PATH)


if __name__ == "__main__":
    raise SystemExit(main())
