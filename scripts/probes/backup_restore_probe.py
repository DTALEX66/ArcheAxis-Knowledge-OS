"""Back up a store, restore it into an independently established store, and read it back.

This measures both halves of the backup and restore task with the sanctioned drivers rather than
hand-written SQL. It needs no core binary, unlike the actor probe, so it runs wherever the Python
runtime does. The receipt records what happened; the tests assert only what must hold anywhere.
"""

import hashlib, json, os, shutil, sqlite3, subprocess, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CONTENT_TABLES = ("core_objects", "kb_documents", "kb_cards", "schema_migrations")


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def inventory(path: Path) -> dict:
    if not path.is_file():
        return {"db_present": False}
    connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        tables = sorted(row[0] for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"))
        counts = {name: connection.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]
                  for name in CONTENT_TABLES if name in tables}
        return {"db_present": True, "bytes": path.stat().st_size, "table_count": len(tables),
                "integrity_check": connection.execute("PRAGMA integrity_check").fetchone()[0],
                "row_counts": counts}
    finally:
        connection.close()


def run() -> dict:
    runs = REPO / ".project-local" / "runs"
    runs.mkdir(parents=True, exist_ok=True)
    root = runs / "backup-restore-probe-run"
    if root.exists():
        shutil.rmtree(root, ignore_errors=True)
    source = root / "source"
    target = root / "target"
    for directory in (source, target):
        directory.mkdir(parents=True)

    receipt = {"scope": "backup_restore_probe", "steps": []}

    def environment(directory: Path) -> dict:
        env = dict(os.environ)
        env["PYTHONPATH"] = str(REPO); env["PYTHONIOENCODING"] = "utf-8"
        env["ARCHEAXIS_DB_PATH"] = str(directory / "archeaxis.sqlite")
        env["ARCHEAXIS_DATA_DIR"] = str(directory)
        return env

    def drive(directory: Path, *argv, timeout=900):
        result = subprocess.run([sys.executable, "-m", "app.runtime_entrypoint", *argv],
                                cwd=str(REPO), env=environment(directory), capture_output=True,
                                text=True, encoding="utf-8", errors="replace", timeout=timeout)
        tail = (result.stdout or "").strip().splitlines()
        return {"argv": list(argv), "exit": result.returncode, "stderr_tail": (result.stderr or "")[-300:],
                "stdout_tail": tail[-1][:300] if tail else ""}

    receipt["steps"].append(drive(source, "migrate"))
    receipt["steps"].append(drive(source, "backup"))
    backups = sorted((source / "backups").glob("cognitive_os_*.sqlite"))
    receipt["backup_count"] = len(backups)
    if not backups:
        receipt["ok"] = False; receipt["failed_step"] = "backup produced nothing"; return receipt
    backup = backups[-1]
    receipt["backup_name"] = backup.name
    receipt["backup_sha256"] = sha256_of(backup)
    receipt["backup_bytes"] = backup.stat().st_size

    manifest_path = backup.with_suffix(backup.suffix + ".manifest.json")
    if manifest_path.is_file():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except Exception as error:
            manifest = None
            receipt["manifest_error"] = f"{type(error).__name__}"
        if isinstance(manifest, dict):
            receipt["manifest_sha256"] = (manifest.get("backup") or {}).get("sha256")
            receipt["manifest_bytes"] = (manifest.get("backup") or {}).get("size_bytes")
            receipt["manifest_kind"] = manifest.get("kind")
            receipt["manifest_version"] = manifest.get("manifest_version")
            receipt["manifest_required_tables"] = sorted(
                ((manifest.get("domain_invariants") or {}).get("required_tables") or []))

    # The target must be established before a candidate can bind to it - measured in an earlier round.
    receipt["steps"].append(drive(target, "migrate"))
    receipt["target_before_restore"] = inventory(target / "archeaxis.sqlite")
    receipt["steps"].append(drive(target, "restore-backup", str(backup)))
    receipt["after_restore"] = inventory(target / "archeaxis.sqlite")

    # A separate process, so the read-back happens after the restoring process has gone.
    receipt["steps"].append(drive(target, "migration-status"))
    receipt["after_cold_start"] = inventory(target / "archeaxis.sqlite")

    restored = target / "archeaxis.sqlite"
    receipt["restored_sha256"] = sha256_of(restored) if restored.is_file() else None
    receipt["restore_is_byte_identical_to_backup"] = (receipt["restored_sha256"] == receipt["backup_sha256"])
    receipt["survives_cold_start"] = (
        receipt["after_restore"].get("table_count") == receipt["after_cold_start"].get("table_count")
        and receipt["after_restore"].get("integrity_check") == receipt["after_cold_start"].get("integrity_check")
        and receipt["after_restore"].get("row_counts") == receipt["after_cold_start"].get("row_counts"))
    receipt["restore_integrity_ok"] = receipt["after_restore"].get("integrity_check") == "ok"
    receipt["ok"] = bool(receipt["after_restore"].get("db_present"))
    shutil.rmtree(root, ignore_errors=True)
    return receipt


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--json-out", type=Path)
    options = parser.parse_args()
    receipt = run()
    text = json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True)
    if options.json_out:
        options.json_out.parent.mkdir(parents=True, exist_ok=True)
        options.json_out.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if receipt.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
