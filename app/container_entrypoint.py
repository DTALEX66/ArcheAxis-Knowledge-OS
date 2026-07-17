"""Container command adapter for the packaged Cognitive-Loop-OS wheel."""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path
from typing import NoReturn

UVICORN_WORKER_ARGS = ["--workers", "1"]


def _exec_process(command: list[str]) -> NoReturn:
    if os.name == "posix":
        os.execvp(command[0], command)
    raise SystemExit(subprocess.call(command))


def _uvicorn_command(app_path: str, default_port: int) -> list[str]:
    return [
        sys.executable,
        "-m",
        "uvicorn",
        app_path,
        "--host",
        os.getenv("COGNITIVE_HOST", "0.0.0.0"),
        "--port",
        os.getenv("COGNITIVE_PORT", str(default_port)),
        *UVICORN_WORKER_ARGS,
        "--no-proxy-headers",
    ]


def _database_path() -> Path:
    from shared import storage

    return storage.DB_PATH


def _prepare_database_file() -> Path:
    database = _database_path()
    database.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(str(database)) as connection:
        if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise RuntimeError(f"SQLite integrity check failed for {database}")
    return database


def _validate_storage_schema() -> Path:
    from shared import storage

    storage.validate_schema()
    return storage.DB_PATH


def _json_default(value: object) -> str:
    if isinstance(value, Path):
        return str(value)
    return str(value)


def run_core(_: argparse.Namespace) -> NoReturn:
    from shared import backup

    backup.acquire_runtime_lock()
    backup.prepare_runtime_database()
    _validate_storage_schema()
    _exec_process(_uvicorn_command("app.main:app", 8000))


def run_migration(_: argparse.Namespace) -> int:
    from shared import backup, migration
    from shared.migration_runner import MigrationOperator

    with backup.runtime_lease():
        database = _prepare_database_file()
        backup.prepare_runtime_database()
        operator = MigrationOperator(db_path=database, backup_dir=migration.BACKUP_DIR)
        results = [
            operator.apply(owner.owner)
            for owner in operator.registry.owners
            if owner.kind.startswith("sqlite")
        ]
        backup.ensure_volume_identity(database)
    payload = {
        "database": str(database),
        "operator_results": results,
        "status": operator.status(),
    }
    print(json.dumps(payload, default=_json_default, sort_keys=True), flush=True)
    return 0


def run_migration_status(_: argparse.Namespace) -> int:
    from shared import migration
    from shared.migration_runner import MigrationOperator

    database = _database_path()
    operator = MigrationOperator(db_path=database, backup_dir=migration.BACKUP_DIR)
    print(
        json.dumps(
            {"database": str(database), "status": operator.status()},
            default=_json_default,
            sort_keys=True,
        ),
        flush=True,
    )
    return 0


def run_integrity(_: argparse.Namespace) -> int:
    database = _validate_storage_schema()
    with sqlite3.connect(f"{database.resolve().as_uri()}?mode=ro", uri=True) as connection:
        result = connection.execute("PRAGMA integrity_check").fetchone()[0]
    if result != "ok":
        raise RuntimeError(f"SQLite integrity check failed for {database}: {result}")
    print(json.dumps({"database": str(database), "integrity_check": result}), flush=True)
    return 0


def run_backup(_: argparse.Namespace) -> int:
    from shared import backup

    print(backup.backup(), flush=True)
    return 0


def run_restore_candidate(args: argparse.Namespace) -> int:
    from shared import backup

    source = args.backup_path or os.getenv("COGNITIVE_RESTORE_BACKUP", "")
    if not source:
        raise RuntimeError("restore-candidate requires COGNITIVE_RESTORE_BACKUP or a backup path")
    print(backup.restore(source), flush=True)
    return 0


def run_restore_activate(args: argparse.Namespace) -> int:
    from shared import backup

    source = args.candidate_path or os.getenv("COGNITIVE_RESTORE_CANDIDATE", "")
    if not source:
        raise RuntimeError(
            "restore-activate requires COGNITIVE_RESTORE_CANDIDATE or a candidate path"
        )
    print(backup.activate_restore(source), flush=True)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    core = subparsers.add_parser("core", help="run the core Cognitive-OS API")
    core.set_defaults(func=run_core)


    migrate = subparsers.add_parser("migrate", help="run the current SQLite migration adapter")
    migrate.set_defaults(func=run_migration)

    migration = subparsers.add_parser("migration", help="alias for migrate")
    migration.set_defaults(func=run_migration)

    status = subparsers.add_parser("migration-status", help="report current migration state")
    status.set_defaults(func=run_migration_status)

    integrity = subparsers.add_parser("integrity", help="run SQLite integrity_check")
    integrity.set_defaults(func=run_integrity)

    backup = subparsers.add_parser("backup", help="create a verified SQLite backup")
    backup.set_defaults(func=run_backup)

    restore = subparsers.add_parser(
        "restore-candidate",
        help="stage a verified offline restore candidate from a backup",
    )
    restore.add_argument("backup_path", nargs="?")
    restore.set_defaults(func=run_restore_candidate)

    activate = subparsers.add_parser(
        "restore-activate",
        help="offline atomically activate a verified restore candidate",
    )
    activate.add_argument("candidate_path", nargs="?")
    activate.set_defaults(func=run_restore_activate)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args) or 0)


if __name__ == "__main__":
    raise SystemExit(main())
