"""Independent verification of the legacy single-database migration (AXW-DATA-403).

The mandate requires the legacy path to be exercised on an **authorised copy** with
a dry-run and a semantic diff, never against the original database. This probe
enforces that literally:

  * the original `data/cognitive_os.sqlite` is hashed before and after, and must be
    byte-identical and still present - the only file the probe reads from it is a copy
  * `backup()` takes the consistent `VACUUM INTO` snapshot
  * `dry_run()` produces the read-only plan, and the plan's `source_hash` is checked
    against an independently computed hash of the copy
  * `migrate()` runs on the copy, and its recorded dispositions are diffed against the
    plan: every planned table is accounted for, ledger rows copied equal planned ledger
    rows, and one file is produced per non-ledger row
  * the migration is idempotent: a second call returns the recorded result and creates
    no second backup
  * `rollback_readback()` verifies the backup and exposes the restore candidate
  * the produced `ledger.sqlite` is opened and its tables counted

It signs no product qualification: this verifies one legacy asset on one machine.
"""

from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import json
import shutil
import sqlite3
import sys
import uuid
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


runtime = _load("runtime_migration", REPO / "scripts" / "runtime" / "dev.py")
LEGACY = REPO / "data" / "cognitive_os.sqlite"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 256), b""):
            digest.update(chunk)
    return digest.hexdigest()


def table_counts(db: Path) -> dict[str, int]:
    with contextlib.closing(sqlite3.connect(f"file:{db}?mode=ro", uri=True)) as connection:
        names = [
            row[0]
            for row in connection.execute(
                "select name from sqlite_master where type='table' order by name"
            )
        ]
        counts: dict[str, int] = {}
        for name in names:
            with contextlib.suppress(sqlite3.OperationalError):
                counts[name] = connection.execute(f'select count(*) from "{name}"').fetchone()[0]
        return counts


def _shallow_workdir() -> Path:
    """A deliberately shallow scratch root.

    The workspace layout nests `<domain>/<table>/<sha256>.bin`. Under the deep
    `.project-local/runs/<run>/<id>/artifacts/<namespace>/<uuid>` allocation this
    probe would otherwise exceed 260 characters, and this repository documents that
    a **plain** path over 260 characters fails closed on Windows - long paths need
    the `\\\\?\\` extended form (see `tests/test_axw_long_path.py`). Using a short
    root keeps the run inside the documented plain-path limit.
    """
    root = REPO / ".project-local" / "mig" / uuid.uuid4().hex[:8]
    root.mkdir(parents=True, exist_ok=True)
    return root


def main() -> int:
    with contextlib.suppress(Exception):
        sys.stdout.reconfigure(encoding="utf-8")
    if not LEGACY.is_file():
        print(json.dumps({"ok": False, "blocked": "legacy database not present", "path": str(LEGACY)}))
        return 2

    sys.path.insert(0, str(REPO))
    from app.workspace import migrate as migrator
    from shared.workspace_manifest import create_workspace

    original_before = {
        "path": str(LEGACY),
        "size": LEGACY.stat().st_size,
        "mtime": LEGACY.stat().st_mtime,
        "sha256": sha256_file(LEGACY),
    }

    work = _shallow_workdir()
    copy = work / "legacy-copy.sqlite"
    shutil.copyfile(LEGACY, copy)
    backup_dir = work / "backups"
    workspace_root = work / "workspace"
    create_workspace(work, "workspace")

    receipt: dict[str, object] = {"ok": False, "workdir": str(work), "original_before": original_before}

    copy_hash = sha256_file(copy)
    # `content_hash` is a LOGICAL hash (tables + rows), deliberately not the file's
    # byte hash: VACUUM INTO snapshots differ in bytes but not in content. Keep the
    # two separate - conflating them was a bug in the first draft of this probe.
    logical_hash = migrator.content_hash(copy)
    receipt["authorised_copy"] = {"path": str(copy), "sha256": copy_hash,
                                  "matches_original": copy_hash == original_before["sha256"],
                                  "logical_hash": logical_hash}

    # 1. Consistent snapshot.
    backup_result = migrator.backup(copy, backup_dir)
    receipt["backup"] = backup_result
    backups_after_first = sorted(p.name for p in backup_dir.glob("*.sqlite"))

    # 2. Read-only plan.
    plan_result = migrator.dry_run(copy, workspace_root)
    plan = plan_result.get("plan") or {}
    planned_tables = plan.get("tables", []) if isinstance(plan, dict) else []
    receipt["dry_run"] = {
        "status": plan_result.get("status"),
        "skipped": plan_result.get("skipped"),
        "source_hash": plan.get("source_hash") if isinstance(plan, dict) else None,
        "source_hash_is_the_logical_hash": isinstance(plan, dict) and plan.get("source_hash") == logical_hash,
        "unreadable_tables": plan.get("unreadable_tables") if isinstance(plan, dict) else None,
        "table_count": len(planned_tables),
        "tables_with_rows": [
            {"name": t["name"], "rows": t["rows"], "kind": t["kind"]}
            for t in planned_tables if t["rows"]
        ],
        "targets": plan.get("targets") if isinstance(plan, dict) else None,
    }

    # 3. Migrate the copy.
    migration = migrator.migrate(copy, workspace_root, backup_dir=backup_dir)
    copied = migration.get("copied") or []
    files = migration.get("files") or []
    ledger_planned = [t for t in planned_tables if t["kind"] == "ledger"]
    other_planned = [t for t in planned_tables if t["kind"] != "ledger"]
    planned_ledger_rows = sum(t["rows"] for t in ledger_planned)
    planned_other_rows = sum(t["rows"] for t in other_planned)
    copied_names = {str(e.get("name")) for e in copied if isinstance(e, dict)}
    skipped = [e for e in copied if isinstance(e, dict) and e.get("disposition") == "skipped"]
    skipped_names = {str(e.get("name")) for e in skipped}
    copied_rows = sum(int(e.get("rows") or 0) for e in copied if isinstance(e, dict))
    skipped_planned_rows = sum(t["rows"] for t in ledger_planned if t["name"] in skipped_names)
    file_tables = {str(f.get("table")) for f in files if isinstance(f, dict)}
    # Only a table that actually holds rows must be accounted for: an empty table
    # legitimately yields no ledger entry and no file. Comparing set sizes instead
    # of per-table rows was a bug in the first draft of this probe.
    unaccounted = [
        t["name"] for t in planned_tables
        if t["rows"] > 0 and t["name"] not in copied_names and t["name"] not in file_tables
    ]
    empty_tables = [t["name"] for t in planned_tables if not t["rows"]]
    receipt["semantic_diff"] = {
        "planned_tables": len(planned_tables),
        "planned_ledger_tables": len(ledger_planned),
        "planned_non_ledger_tables": len(other_planned),
        "copied_entries": len(copied),
        "virtual_tables_recorded_as_skipped": sorted(skipped_names),
        "skipped_reasons": sorted({str(e.get("reason")) for e in skipped}),
        "planned_ledger_rows": planned_ledger_rows,
        "copied_rows": copied_rows,
        "skipped_planned_rows": skipped_planned_rows,
        "ledger_rows_accounted_for": copied_rows + skipped_planned_rows == planned_ledger_rows,
        "planned_non_ledger_rows": planned_other_rows,
        "files_written": len(files),
        "one_file_per_non_ledger_row": len(files) == planned_other_rows,
        "every_planned_table_accounted_for": not unaccounted,
        "unaccounted_tables": sorted(unaccounted),
        "empty_table_count": len(empty_tables),
    }
    receipt["migration_status"] = migration.get("status")
    receipt["legacy_db_kept"] = migration.get("legacy_db_kept")
    receipt["migration_manifest"] = migration.get("migration_manifest")
    receipt["migration_unreadable_tables"] = migration.get("unreadable_tables")

    # 4. Idempotency: the second call must not re-back-up.
    second = migrator.migrate(copy, workspace_root, backup_dir=backup_dir)
    backups_after_second = sorted(p.name for p in backup_dir.glob("*.sqlite"))
    receipt["idempotency"] = {
        "second_already_migrated": second.get("already_migrated"),
        "second_status": second.get("status"),
        "backup_count_first": len(backups_after_first),
        "backup_count_second": len(backups_after_second),
        "no_second_backup": len(backups_after_second) == len(backups_after_first),
    }

    # 5. Rollback readback against the recorded source hash.
    backup_path = migration.get("backup_path") or (backup_result.get("backup_path") if isinstance(backup_result, dict) else None)
    receipt["rollback"] = (
        migrator.rollback_readback(backup_path, expected_source_hash=logical_hash)
        if backup_path else {"status": "error", "reason": "no backup path recorded"}
    )

    # 6. The produced ledger must open and hold the copied tables.
    targets = migration.get("targets") or {}
    ledger_path = Path(str(targets.get("evidence_ledger", ""))) / "ledger.sqlite"
    if ledger_path.is_file():
        counts = table_counts(ledger_path)
        receipt["ledger"] = {"path": str(ledger_path), "tables": len(counts),
                             "rows": sum(counts.values())}
    else:
        receipt["ledger"] = {"path": str(ledger_path), "present": False}

    # 7. The original must be untouched and still present.
    original_after = {
        "path": str(LEGACY),
        "size": LEGACY.stat().st_size if LEGACY.is_file() else None,
        "mtime": LEGACY.stat().st_mtime if LEGACY.is_file() else None,
        "sha256": sha256_file(LEGACY) if LEGACY.is_file() else None,
    }
    receipt["original_after"] = original_after
    receipt["original_untouched"] = (
        original_after["sha256"] == original_before["sha256"]
        and original_after["size"] == original_before["size"]
        and original_after["mtime"] == original_before["mtime"]
    )

    diff = receipt["semantic_diff"]
    receipt["ok"] = bool(
        receipt["authorised_copy"]["matches_original"]
        and receipt["dry_run"]["source_hash_is_the_logical_hash"]
        and receipt["migration_status"] == "ok"
        and receipt["legacy_db_kept"] is True
        and diff["every_planned_table_accounted_for"]
        and diff["ledger_rows_accounted_for"]
        and diff["one_file_per_non_ledger_row"]
        and receipt["idempotency"]["no_second_backup"]
        and receipt["rollback"].get("rollback_eligible") is True
        and receipt["original_untouched"]
    )
    out = work / "legacy-migration-receipt.json"
    out.write_text(json.dumps(receipt, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    print(json.dumps(receipt, ensure_ascii=False, indent=2, default=str))
    print(f"\nreceipt: {out}")
    return 0 if receipt["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
