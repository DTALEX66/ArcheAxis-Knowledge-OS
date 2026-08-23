"""Lease-aware runtime command adapter for archeaxis-workspace."""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import subprocess
import sys
import threading
import time
from collections.abc import Iterator
from contextlib import closing
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
        os.getenv("ARCHEAXIS_HOST") or os.getenv("COGNITIVE_HOST", "127.0.0.1"),
        "--port",
        os.getenv("ARCHEAXIS_PORT") or os.getenv("COGNITIVE_PORT", str(default_port)),
        *UVICORN_WORKER_ARGS,
        "--no-proxy-headers",
    ]


def _database_path() -> Path:
    from shared import storage

    return storage.DB_PATH


def _prepare_database_file() -> Path:
    database = _database_path()
    database.parent.mkdir(parents=True, exist_ok=True)
    if not database.is_file():
        return database
    uri = f"{database.resolve().as_uri()}?mode=ro&immutable=1"
    with closing(sqlite3.connect(uri, uri=True, timeout=30.0)) as connection:
        if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise RuntimeError(f"SQLite integrity check failed for {database}")
    return database


def _ensure_database_file() -> Path:
    database = _database_path()
    database.parent.mkdir(parents=True, exist_ok=True)
    database.touch(exist_ok=True)
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
    if os.getenv("ARCHEAXIS_DESKTOP_CONTROL") or os.getenv("COGNITIVE_DESKTOP_CONTROL", "") == "stdio-v1":
        _run_desktop_core()
    _exec_process(_uvicorn_command("app.main:app", 8000))


def _run_desktop_core() -> NoReturn:
    import uvicorn

    host = os.getenv("ARCHEAXIS_HOST") or os.getenv("COGNITIVE_HOST", "127.0.0.1")
    if host != "127.0.0.1":
        raise RuntimeError("desktop core must bind exactly to 127.0.0.1")
    launch_token = os.getenv("ARCHEAXIS_DESKTOP_LAUNCH_TOKEN") or os.getenv("COGNITIVE_DESKTOP_LAUNCH_TOKEN", "")
    if len(launch_token) < 24:
        raise RuntimeError("desktop core requires a strong launch token")
    try:
        port = int(os.getenv("ARCHEAXIS_PORT") or os.getenv("COGNITIVE_PORT", "8000"))
    except ValueError as exc:
        raise RuntimeError("desktop core requires a valid port") from exc
    if not 1 <= port <= 65535:
        raise RuntimeError("desktop core port is outside the valid range")

    server = uvicorn.Server(
        uvicorn.Config(
            "app.main:app",
            host=host,
            port=port,
            workers=1,
            proxy_headers=False,
        )
    )
    shutdown_requested = threading.Event()

    def watch_parent_pipe() -> None:
        for command in _desktop_control_commands(sys.stdin):
            if command == "shutdown":
                shutdown_requested.set()
                server.should_exit = True
                return
        shutdown_requested.set()
        server.should_exit = True

    threading.Thread(
        target=watch_parent_pipe,
        name="desktop-parent-pipe",
        daemon=True,
    ).start()
    server.run()
    if not shutdown_requested.is_set() and not server.started:
        raise SystemExit(3)
    raise SystemExit(0)


def _desktop_control_commands(stream: object) -> Iterator[str]:
    """Yield commands without a blocking TextIOWrapper read on Windows pipes."""
    try:
        descriptor = stream.fileno()  # type: ignore[attr-defined]
    except (AttributeError, OSError):
        while True:
            line = stream.readline()  # type: ignore[attr-defined]
            if line == "":
                return
            yield line.rstrip("\r\n")
    else:
        if os.name == "nt":
            yield from _windows_desktop_control_commands(descriptor)
            return
        pending = b""
        while True:
            chunk = os.read(descriptor, 4096)
            if not chunk:
                return
            pending += chunk
            while b"\n" in pending:
                line, pending = pending.split(b"\n", 1)
                yield line.rstrip(b"\r").decode("utf-8", errors="replace")


def _windows_desktop_control_commands(descriptor: int) -> Iterator[str]:
    import ctypes
    import msvcrt
    from ctypes import wintypes

    peek_named_pipe = ctypes.WinDLL("kernel32", use_last_error=True).PeekNamedPipe
    peek_named_pipe.argtypes = [
        wintypes.HANDLE,
        wintypes.LPVOID,
        wintypes.DWORD,
        wintypes.LPVOID,
        ctypes.POINTER(wintypes.DWORD),
        wintypes.LPVOID,
    ]
    peek_named_pipe.restype = wintypes.BOOL
    handle = wintypes.HANDLE(msvcrt.get_osfhandle(descriptor))
    pending = b""
    while True:
        available = wintypes.DWORD()
        if not peek_named_pipe(handle, None, 0, None, ctypes.byref(available), None):
            error = ctypes.get_last_error()
            if error in {109, 232}:
                return
            raise OSError(error, "PeekNamedPipe failed for desktop parent pipe")
        if available.value == 0:
            time.sleep(0.05)
            continue
        chunk = os.read(descriptor, min(available.value, 4096))
        if not chunk:
            return
        pending += chunk
        while b"\n" in pending:
            line, pending = pending.split(b"\n", 1)
            yield line.rstrip(b"\r").decode("utf-8", errors="replace")


def run_migration(_: argparse.Namespace) -> int:
    from shared import backup, migration
    from shared.migration_runner import MigrationOperator

    with backup.runtime_lease():
        database = _ensure_database_file()
        backup.prepare_runtime_database()
        _prepare_database_file()
        operator = MigrationOperator(db_path=database, backup_dir=migration.BACKUP_DIR)
        results = []
        for owner in operator.registry.owners:
            if not owner.kind.startswith("sqlite"):
                continue
            results.append(operator.apply(owner.owner))
            backup.prepare_runtime_database()
        backup.ensure_volume_identity(database)
        status = operator.status()
    payload = {
        "database": str(database),
        "operator_results": results,
        "status": status,
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


def run_restore_backup(args: argparse.Namespace) -> int:
    from shared import backup

    candidate = backup.restore(args.backup_path)
    backup.activate_restore(candidate)
    print(json.dumps({"status": "restored"}, separators=(",", ":")), flush=True)
    return 0


def run_restore_candidate(args: argparse.Namespace) -> int:
    from shared import backup

    source = args.backup_path or os.getenv("ARCHEAXIS_RESTORE_BACKUP") or os.getenv("COGNITIVE_RESTORE_BACKUP", "")
    if not source:
        raise RuntimeError("restore-candidate requires COGNITIVE_RESTORE_BACKUP or a backup path")
    print(backup.restore(source), flush=True)
    return 0


def run_restore_activate(args: argparse.Namespace) -> int:
    from shared import backup

    source = args.candidate_path or os.getenv("ARCHEAXIS_RESTORE_CANDIDATE") or os.getenv("COGNITIVE_RESTORE_CANDIDATE", "")
    if not source:
        raise RuntimeError(
            "restore-activate requires COGNITIVE_RESTORE_CANDIDATE or a candidate path"
        )
    print(backup.activate_restore(source), flush=True)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    core = subparsers.add_parser("core", help="run the core ArcheAxis API")
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

    restore_backup = subparsers.add_parser(
        "restore-backup",
        help="stage and atomically activate a verified offline restore",
    )
    restore_backup.add_argument("backup_path")
    restore_backup.set_defaults(func=run_restore_backup)

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
