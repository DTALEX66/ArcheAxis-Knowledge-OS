"""Independent API/CLI verification of Core backup and restore integrity.

Uses only the real artefacts: the source-current `archeaxis-api` binary and the
documented maintenance CLI from `crates/archeaxis-api/src/main.rs`:

    archeaxis-api --maintenance-backup  <workspace-db-path> <artifact-path>
    archeaxis-api --maintenance-restore <workspace-db-path> <artifact-path>

Sequence, with a negative control that must fail closed:

  1. start the Core on a fresh workspace, import one real source, stop the Core
  2. `--maintenance-backup` and read the receipt (schema_version, objects dir)
  3. **negative:** restore from a path that is not a backup, and from a corrupted
     copy of the real backup - both must report ok:false and must not damage the
     workspace
  4. mutate the live workspace, then `--maintenance-restore` the real backup and
     confirm the mutation is reverted and `verified` is true
  5. restart the Core on the restored workspace and read the source back over HTTP

Nothing here upgrades a status or claims product qualification; it records what
the real binary does.
"""

from __future__ import annotations

import contextlib
import importlib.util
import json
import shutil
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


core = _load("core_client_backup", REPO / "shared" / "core_client.py")
runtime = _load("runtime_backup", REPO / "scripts" / "runtime" / "dev.py")

TOKEN = "b" * 64
SESSION = "a" * 32
BINARY = REPO / ".project-local" / "build" / "cargo" / "debug" / "archeaxis-api.exe"


def row_counts(db: Path) -> dict[str, int]:
    """Best-effort row counts for the tables that carry workspace content."""
    names = ("sources", "knowledge_items", "transforms", "workspace_jobs_v1", "learning_events")
    counts: dict[str, int] = {}
    with contextlib.closing(sqlite3.connect(f"file:{db}?mode=ro", uri=True)) as connection:
        present = {
            row[0]
            for row in connection.execute(
                "select name from sqlite_master where type='table'"
            )
        }
        for name in names:
            if name in present:
                counts[name] = connection.execute(f"select count(*) from {name}").fetchone()[0]
        if "workspace_meta" in present:
            row = connection.execute(
                "select value from workspace_meta where key='schema_version'"
            ).fetchone()
            counts["schema_version"] = row[0] if row else "absent"
    return counts


def start_core(db: Path, staging: Path) -> tuple[subprocess.Popen, str]:
    worker = {
        "python": str(Path(sys.executable).resolve()),
        "script": str((REPO / "services/python-workers/transport/text_ndjson.py").resolve()),
        "staging": str(staging.resolve()),
    }
    child = subprocess.Popen(
        [str(BINARY), str(db), "0"],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        text=True, encoding="utf-8",
    )
    child.stdin.write(json.dumps({"launch_token": TOKEN, "session_id": SESSION, "text_worker": worker}) + "\n")
    child.stdin.flush()
    child.stdin.close()
    deadline = time.time() + 20
    line = ""
    while time.time() < deadline:
        line = child.stdout.readline()
        if "127.0.0.1:" in line:
            break
    if "127.0.0.1:" not in line:
        child.kill()
        raise SystemExit(f"core did not report readiness: {line[:120]!r}")
    port = line.split("127.0.0.1:", 1)[1].split()[0].strip()
    return child, f"http://127.0.0.1:{port}"


def maintenance(action: str, db: Path, artifact: Path) -> tuple[int, dict]:
    result = subprocess.run(
        [str(BINARY), f"--maintenance-{action}", str(db), str(artifact)],
        capture_output=True, text=True, encoding="utf-8", cwd=REPO,
    )
    line = (result.stdout or "").strip().splitlines()
    payload = {}
    if line:
        with contextlib.suppress(json.JSONDecodeError):
            payload = json.loads(line[-1])
    if not payload:
        payload = {"raw_stdout": result.stdout[-400:], "raw_stderr": result.stderr[-400:]}
    return result.returncode, payload


def main() -> int:
    with contextlib.suppress(Exception):
        sys.stdout.reconfigure(encoding="utf-8")
    if not BINARY.is_file():
        print(json.dumps({"ok": False, "blocked": "core binary not built", "path": str(BINARY)}))
        return 2

    work = runtime.artifact_directory(REPO, "backup-restore-smoke")
    db = work / "workspace.sqlite"
    staging = work / "worker-staging"
    backup = work / "workspace-backup.sqlite"
    receipt: dict[str, object] = {"ok": False, "workdir": str(work), "steps": []}

    def note(step: str, **fields: object) -> None:
        receipt["steps"].append({"step": step, **fields})  # type: ignore[union-attr]

    # 1. Fresh workspace with real content.
    child, base = start_core(db, staging)
    try:
        status, imported = core.call(base, "POST", "/api/v1/imports", TOKEN,
                                    core.import_request("backup-probe.md", b"baseline marker 4821"))
        note("seed_import", status=status, source_id=imported.get("source_id") if isinstance(imported, dict) else None)
        if status not in (200, 201, 202):
            receipt["failed_step"] = "seed_import"
            print(json.dumps(receipt, ensure_ascii=False))
            return 1
    finally:
        child.kill()
        child.wait()

    before = row_counts(db)
    receipt["counts_before_backup"] = before

    # 2. Backup.
    code, payload = maintenance("backup", db, backup)
    note("backup", exit_code=code, receipt=payload)
    if code != 0 or not backup.is_file():
        receipt["failed_step"] = "backup"
        print(json.dumps(receipt, ensure_ascii=False, indent=2))
        return 1

    # 3. Negative controls: a non-backup file and a corrupted copy must both fail
    #    closed, and must leave the live workspace usable.
    not_a_backup = work / "not-a-backup.sqlite"
    not_a_backup.write_bytes(b"this is not a sqlite backup")
    code_missing, payload_missing = maintenance("restore", db, not_a_backup)
    note("negative_not_a_backup", exit_code=code_missing,
         ok=payload_missing.get("ok"), error=str(payload_missing.get("error"))[:160])

    corrupted = work / "corrupted-backup.sqlite"
    shutil.copyfile(backup, corrupted)
    with contextlib.closing(sqlite3.connect(corrupted)) as connection:
        connection.execute("drop table if exists sources")
        connection.commit()
    code_corrupt, payload_corrupt = maintenance("restore", db, corrupted)
    note("negative_corrupted_backup", exit_code=code_corrupt,
         ok=payload_corrupt.get("ok"), rolled_back=payload_corrupt.get("rolled_back"),
         error=str(payload_corrupt.get("error"))[:160])

    after_negatives = row_counts(db)
    negative_ok = (
        code_missing != 0 and payload_missing.get("ok") is False
        and code_corrupt != 0 and payload_corrupt.get("ok") is False
        and after_negatives == before
    )
    receipt["negatives_fail_closed"] = negative_ok

    # 4. Mutate the live workspace, then restore and expect the mutation reverted.
    with contextlib.closing(sqlite3.connect(db)) as connection:
        connection.execute("delete from sources")
        connection.commit()
    mutated = row_counts(db)
    code_restore, payload_restore = maintenance("restore", db, backup)
    note("restore", exit_code=code_restore, receipt=payload_restore)
    restored = row_counts(db)
    receipt["counts_mutated"] = mutated
    receipt["counts_after_restore"] = restored
    receipt["restore_verified"] = bool(payload_restore.get("verified"))
    receipt["mutation_reverted"] = restored == before

    # 5. Restart the Core on the restored workspace and read the source back.
    child, base = start_core(db, staging)
    try:
        status, found = core.call(base, "GET", core.search_path("baseline marker 4821"), TOKEN)
        items = found.get("items") if isinstance(found, dict) else None
        transforms = found.get("transforms") if isinstance(found, dict) else None
        note("restart_readback", status=status,
             knowledge_items=len(items) if isinstance(items, list) else None,
             transforms=len(transforms) if isinstance(transforms, list) else None)
        receipt["restart_readback_status"] = status
    finally:
        child.kill()
        child.wait()

    receipt["ok"] = bool(
        negative_ok
        and receipt["restore_verified"]
        and receipt["mutation_reverted"]
        and receipt["restart_readback_status"] == 200
    )
    out = work / "backup-restore-receipt.json"
    out.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, ensure_ascii=False, indent=2))
    print(f"\nreceipt: {out}")
    return 0 if receipt["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
