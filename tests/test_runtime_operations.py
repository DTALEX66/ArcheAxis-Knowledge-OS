from __future__ import annotations

import json
import os
import sqlite3
from argparse import Namespace
from contextlib import contextmanager
from pathlib import Path

import pytest

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10 compatibility
    import tomli as tomllib

ROOT = Path(__file__).resolve().parents[1]


def test_runtime_entrypoint_defaults_to_loopback_and_allows_explicit_host_override(monkeypatch):
    from app import runtime_entrypoint

    monkeypatch.delenv("COGNITIVE_HOST", raising=False)
    assert runtime_entrypoint._uvicorn_command("app.main:app", 8000)[5] == "127.0.0.1"

    monkeypatch.setenv("COGNITIVE_HOST", "0.0.0.0")
    assert runtime_entrypoint._uvicorn_command("app.main:app", 8000)[5] == "0.0.0.0"


def test_runtime_entrypoint_delegates_to_existing_migration_and_backup_apis():
    entrypoint = (ROOT / "app" / "runtime_entrypoint.py").read_text(encoding="utf-8")
    assert "MigrationOperator" in entrypoint
    assert "for owner in operator.registry.owners" in entrypoint
    assert 'if not owner.kind.startswith("sqlite"):' in entrypoint
    assert "operator.apply(owner.owner)" in entrypoint
    assert 'operator.apply("taskpack.sqlite")' not in entrypoint
    assert "migration.migrate" not in entrypoint
    assert "from shared import backup" in entrypoint
    assert "backup.backup" in entrypoint
    assert "backup.restore" in entrypoint
    assert "backup.activate_restore" in entrypoint
    assert "core_runtime_guard" in entrypoint
    assert "with backup.runtime_lease()" in entrypoint
    assert "storage.init()" not in entrypoint
    assert "memory_database.init_db()" not in entrypoint
    assert "CREATE TABLE schema_migrations" not in entrypoint
    assert "INSERT INTO schema_migrations" not in entrypoint


def test_core_restart_checkpoints_residual_sidecars_after_acquiring_runtime_lock(monkeypatch):
    from app import runtime_entrypoint
    from shared import backup

    events: list[str] = []

    class ExecReachedError(RuntimeError):
        pass

    monkeypatch.setattr(backup, "acquire_runtime_lock", lambda: events.append("lock"))
    monkeypatch.setattr(
        backup,
        "prepare_runtime_database",
        lambda: events.append("checkpoint"),
        raising=False,
    )
    monkeypatch.setattr(
        runtime_entrypoint,
        "_validate_storage_schema",
        lambda: events.append("validate"),
    )

    def stop_at_exec(_command):
        events.append("exec")
        raise ExecReachedError

    monkeypatch.setattr(runtime_entrypoint, "_exec_process", stop_at_exec)

    with pytest.raises(ExecReachedError):
        runtime_entrypoint.run_core(Namespace())
    assert events == ["lock", "checkpoint", "validate", "exec"]


def test_core_launcher_uses_the_shared_runtime_guard(monkeypatch):
    from app import runtime_entrypoint

    events: list[str] = []

    @contextmanager
    def recording_guard(*, validate):
        events.append("guard-enter")
        validate()
        try:
            yield
        finally:
            events.append("guard-exit")

    monkeypatch.setattr(runtime_entrypoint, "core_runtime_guard", recording_guard)
    monkeypatch.setattr(runtime_entrypoint, "_validate_storage_schema", lambda: events.append("validate"))
    monkeypatch.setattr(
        runtime_entrypoint,
        "_exec_process",
        lambda _command: (_ for _ in ()).throw(RuntimeError("exec reached")),
    )

    with pytest.raises(RuntimeError, match="exec reached"):
        runtime_entrypoint.run_core(Namespace())

    assert events == ["guard-enter", "validate", "guard-exit"]


def test_core_runtime_guard_releases_its_lease_after_validation_failure(monkeypatch):
    from shared import backup
    from shared.runtime_guard import core_runtime_guard

    events: list[str] = []
    monkeypatch.setattr(backup, "acquire_runtime_lock", lambda: events.append("lock"))
    monkeypatch.setattr(backup, "prepare_runtime_database", lambda: events.append("checkpoint"))
    monkeypatch.setattr(backup, "release_runtime_lock", lambda: events.append("release"))

    def fail_validation() -> None:
        events.append("validate")
        raise RuntimeError("schema unavailable")

    with pytest.raises(RuntimeError, match="schema unavailable"):
        with core_runtime_guard(validate=fail_validation):
            pytest.fail("guard must not enter when validation fails")

    assert events == ["lock", "checkpoint", "validate", "release"]


def test_migration_checkpoints_wal_before_constructing_operator(monkeypatch, tmp_path):
    from types import SimpleNamespace

    from app import runtime_entrypoint
    from shared import backup, migration, migration_runner

    database = tmp_path / "runtime.sqlite"
    backup_dir = tmp_path / "backups"
    database.touch()
    events: list[str] = []

    @contextmanager
    def recording_lease():
        events.append("lease-enter")
        try:
            yield
        finally:
            events.append("lease-exit")

    def ensure_file():
        events.append("ensure-file")
        return database

    def integrity_check():
        events.append("integrity")

    def checkpoint():
        events.append("checkpoint")

    class RecordingOperator:
        def __init__(self, *, db_path, backup_dir):
            assert Path(db_path) == database
            assert Path(backup_dir) == backup_dir_path
            assert events == ["lease-enter", "ensure-file", "checkpoint", "integrity"]
            events.append("operator-init")
            self.registry = SimpleNamespace(
                owners=(
                    SimpleNamespace(owner="core.sqlite", kind="sqlite_core"),
                    SimpleNamespace(owner="research.sqlite", kind="sqlite_research"),
                )
            )

        def apply(self, owner):
            if owner == "core.sqlite":
                assert events == [
                    "lease-enter",
                    "ensure-file",
                    "checkpoint",
                    "integrity",
                    "operator-init",
                ]
                events.append("apply-core")
            elif owner == "research.sqlite":
                assert events == [
                    "lease-enter",
                    "ensure-file",
                    "checkpoint",
                    "integrity",
                    "operator-init",
                    "apply-core",
                    "checkpoint",
                ]
                events.append("apply-research")
            else:  # pragma: no cover - guards the contract fixture
                raise AssertionError(owner)
            return {"owner": owner, "state": "applied"}

        def status(self):
            assert events == [
                "lease-enter",
                "ensure-file",
                "checkpoint",
                "integrity",
                "operator-init",
                "apply-core",
                "checkpoint",
                "apply-research",
                "checkpoint",
                "identity",
            ]
            events.append("status")
            return []

    backup_dir_path = backup_dir
    monkeypatch.setattr(backup, "runtime_lease", recording_lease)
    monkeypatch.setattr(backup, "prepare_runtime_database", checkpoint)
    monkeypatch.setattr(migration, "BACKUP_DIR", backup_dir)
    monkeypatch.setattr(runtime_entrypoint, "_ensure_database_file", ensure_file)
    monkeypatch.setattr(runtime_entrypoint, "_prepare_database_file", integrity_check)
    monkeypatch.setattr(migration_runner, "MigrationOperator", RecordingOperator)
    monkeypatch.setattr(
        backup, "ensure_volume_identity", lambda _database: events.append("identity")
    )

    assert runtime_entrypoint.run_migration(Namespace()) == 0
    assert events == [
        "lease-enter",
        "ensure-file",
        "checkpoint",
        "integrity",
        "operator-init",
        "apply-core",
        "checkpoint",
        "apply-research",
        "checkpoint",
        "identity",
        "status",
        "lease-exit",
    ]


def test_runtime_migration_records_operator_provenance_and_backup(
    monkeypatch, tmp_path, capsys
):
    from app import runtime_entrypoint
    from app.memory import database as memory_database
    from shared import backup, migration, storage

    database = tmp_path / "runtime" / "cognitive.sqlite"
    backup_dir = tmp_path / "backups"
    for module in (storage, memory_database, backup, migration):
        monkeypatch.setattr(module, "DB_PATH", database)
    monkeypatch.setattr(backup, "BACKUP_DIR", backup_dir)
    monkeypatch.setattr(migration, "BACKUP_DIR", backup_dir)

    assert runtime_entrypoint.run_migration(Namespace()) == 0
    payload = json.loads(capsys.readouterr().out)
    owners = {result["owner"] for result in payload["operator_results"]}
    assert owners == {
        "core.sqlite",
        "knowledge-governance.sqlite",
        "research.sqlite",
        "taskpack.sqlite",
        "workspace.sqlite",
    }
    assert all(result["state"] == "applied" for result in payload["operator_results"])
    with sqlite3.connect(database) as connection:
        rows = set(
            connection.execute(
                "SELECT owner, state, operation FROM migration_operator_runs "
                "WHERE operation='apply'"
            ).fetchall()
        )
        research_table = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='research_packages_v1'"
        ).fetchone()
    assert {(owner, "applied", "apply") for owner in owners} <= rows
    assert research_table == (1,)
    assert list(backup_dir.glob("*.sqlite"))


def test_runtime_migration_status_uses_current_authoritative_backup_dir(
    monkeypatch, tmp_path, capsys
):
    from app import runtime_entrypoint
    from shared import migration, migration_runner, storage

    database = tmp_path / "runtime" / "cognitive.sqlite"
    backup_dir = tmp_path / "configured-backups"
    monkeypatch.setattr(storage, "DB_PATH", database)
    monkeypatch.setattr(migration, "BACKUP_DIR", backup_dir)

    class RecordingOperator:
        def __init__(self, *, db_path, backup_dir):
            assert Path(db_path).resolve() == database.resolve()
            assert Path(backup_dir).resolve() == backup_dir_path

        def status(self):
            return [{"owner": "core.sqlite", "state": "pending"}]

    backup_dir_path = backup_dir.resolve()
    monkeypatch.setattr(migration_runner, "MigrationOperator", RecordingOperator)

    assert runtime_entrypoint.run_migration_status(Namespace()) == 0
    assert json.loads(capsys.readouterr().out) == {
        "database": str(database),
        "status": [{"owner": "core.sqlite", "state": "pending"}],
    }


def test_core_schema_validation_requires_phase4_research_migration(
    monkeypatch, tmp_path, capsys
):
    from app import runtime_entrypoint
    from app.memory import database as memory_database
    from shared import backup, migration, storage

    database = tmp_path / "runtime" / "cognitive.sqlite"
    backup_dir = tmp_path / "backups"
    for module in (storage, memory_database, backup, migration):
        monkeypatch.setattr(module, "DB_PATH", database)
    monkeypatch.setattr(backup, "BACKUP_DIR", backup_dir)
    monkeypatch.setattr(migration, "BACKUP_DIR", backup_dir)

    assert runtime_entrypoint.run_migration(Namespace()) == 0
    capsys.readouterr()
    with sqlite3.connect(database) as connection:
        connection.execute("DROP TABLE research_packages_v1")

    with pytest.raises(RuntimeError, match="research migration schema"):
        storage.validate_schema()


def test_core_schema_validation_requires_baseline_operator_provenance(
    monkeypatch, tmp_path, capsys
):
    from app import runtime_entrypoint
    from app.memory import database as memory_database
    from shared import backup, migration, storage

    database = tmp_path / "runtime" / "cognitive.sqlite"
    backup_dir = tmp_path / "backups"
    for module in (storage, memory_database, backup, migration):
        monkeypatch.setattr(module, "DB_PATH", database)
    monkeypatch.setattr(backup, "BACKUP_DIR", backup_dir)
    monkeypatch.setattr(migration, "BACKUP_DIR", backup_dir)

    assert runtime_entrypoint.run_migration(Namespace()) == 0
    capsys.readouterr()
    with sqlite3.connect(database) as connection:
        connection.execute("DELETE FROM migration_operator_runs WHERE owner='core.sqlite'")

    with pytest.raises(RuntimeError, match="operator provenance"):
        storage.validate_schema()


def test_core_schema_validation_rejects_named_but_malformed_baseline_table(
    monkeypatch, tmp_path, capsys
):
    from app import runtime_entrypoint
    from app.memory import database as memory_database
    from shared import backup, migration, storage

    database = tmp_path / "runtime" / "cognitive.sqlite"
    backup_dir = tmp_path / "backups"
    for module in (storage, memory_database, backup, migration):
        monkeypatch.setattr(module, "DB_PATH", database)
    monkeypatch.setattr(backup, "BACKUP_DIR", backup_dir)
    monkeypatch.setattr(migration, "BACKUP_DIR", backup_dir)

    assert runtime_entrypoint.run_migration(Namespace()) == 0
    capsys.readouterr()
    with sqlite3.connect(database) as connection:
        connection.execute("DROP TABLE permission_decisions")
        connection.execute("CREATE TABLE permission_decisions (id TEXT PRIMARY KEY)")

    with pytest.raises(RuntimeError, match="baseline schema"):
        storage.validate_schema()


def test_core_schema_validation_uses_readonly_research_connection(
    monkeypatch, tmp_path, capsys
):
    from app import runtime_entrypoint
    from app.memory import database as memory_database
    from shared import backup, migration, research_migration, storage

    database = tmp_path / "runtime" / "cognitive.sqlite"
    backup_dir = tmp_path / "backups"
    for module in (storage, memory_database, backup, migration):
        monkeypatch.setattr(module, "DB_PATH", database)
    monkeypatch.setattr(backup, "BACKUP_DIR", backup_dir)
    monkeypatch.setattr(migration, "BACKUP_DIR", backup_dir)
    assert runtime_entrypoint.run_migration(Namespace()) == 0
    capsys.readouterr()

    with sqlite3.connect(database) as connection:
        connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        connection.execute("PRAGMA journal_mode=DELETE")
    sidecars = [Path(f"{database}{suffix}") for suffix in ("-wal", "-shm")]
    assert all(not path.exists() for path in sidecars)
    calls: list[Path] = []
    original_connect = sqlite3.connect

    def recording_connect(target: Path):
        calls.append(target)
        uri = f"{target.resolve().as_uri()}?mode=ro&immutable=1"
        connection = original_connect(uri, uri=True, timeout=30.0)
        connection.execute("PRAGMA busy_timeout=30000")
        connection.execute("PRAGMA query_only=ON")
        connection.row_factory = sqlite3.Row
        return connection

    def forbidden_connect(target, *args, **kwargs):
        if str(target) == ":memory:":
            return original_connect(target, *args, **kwargs)
        raise AssertionError("startup validation bypassed the unified readonly connector")

    def forbidden_status(*_args, **_kwargs):
        raise AssertionError("startup validation opened a second migration status connection")

    monkeypatch.setattr(
        research_migration, "_connect_readonly", recording_connect, raising=False
    )
    monkeypatch.setattr(storage.sqlite3, "connect", forbidden_connect)
    monkeypatch.setattr(migration, "status", forbidden_status)
    storage.validate_schema()

    assert calls == [database]
    assert all(not path.exists() for path in sidecars)


def test_cli_pipeline_holds_target_runtime_lease(monkeypatch):
    from app.cli import cmd_pipeline
    from shared import backup, pipeline, storage

    events: list[tuple[str, Path]] = []

    @contextmanager
    def recording_lease(target):
        resolved = Path(target).resolve()
        events.append(("enter", resolved))
        try:
            yield
        finally:
            events.append(("exit", resolved))

    def recording_pipeline(*, source, input_data):
        assert events == [("enter", storage.DB_PATH.resolve())]
        return {"source": source, "input": input_data}

    monkeypatch.setattr(backup, "runtime_lease", recording_lease)
    monkeypatch.setattr(pipeline, "run_pipeline", recording_pipeline)

    cmd_pipeline("text", "payload")

    assert events == [
        ("enter", storage.DB_PATH.resolve()),
        ("exit", storage.DB_PATH.resolve()),
    ]


@pytest.mark.parametrize("action", ("apply", "rollback"))
def test_cli_effectful_migration_holds_explicit_target_runtime_lease(
    action, monkeypatch, tmp_path, capsys
):
    from app.cli import cmd_migrate
    from shared import backup, migration_runner

    database = tmp_path / "explicit.sqlite"
    backup_dir = tmp_path / "backups"
    events: list[tuple[str, Path]] = []

    @contextmanager
    def recording_lease(target):
        resolved = Path(target).resolve()
        events.append(("enter", resolved))
        try:
            yield
        finally:
            events.append(("exit", resolved))

    class RecordingOperator:
        def __init__(self, *, db_path, backup_dir):
            assert Path(db_path).resolve() == database.resolve()
            assert Path(backup_dir).resolve() == backup_dir_path

        def apply(self, owner):
            assert events == [("enter", database.resolve())]
            return {"action": "apply", "owner": owner}

        def rollback(self, owner):
            assert events == [("enter", database.resolve())]
            return {"action": "rollback", "owner": owner}

    backup_dir_path = backup_dir.resolve()
    monkeypatch.setattr(backup, "runtime_lease", recording_lease)
    monkeypatch.setattr(migration_runner, "MigrationOperator", RecordingOperator)
    monkeypatch.delenv("COGNITIVE_DB_PATH", raising=False)

    cmd_migrate(
        [
            action,
            "--owner",
            "taskpack.sqlite",
            "--db",
            str(database),
            "--backup-dir",
            str(backup_dir),
        ]
    )

    assert events == [
        ("enter", database.resolve()),
        ("exit", database.resolve()),
    ]
    assert "COGNITIVE_DB_PATH" not in os.environ
    assert json.loads(capsys.readouterr().out)["action"] == action


def test_requirements_txt_matches_pyproject_runtime_dependencies():
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    declared = pyproject["project"]["dependencies"]
    requirements = [
        line.strip()
        for line in (ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    assert requirements == declared


def test_all_ci_actions_are_commit_pinned():
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "actions/checkout@v" not in workflow
    assert "actions/setup-python@v" not in workflow
    assert "astral-sh/setup-uv@v" not in workflow
    for action in (
        "actions/checkout@34e114876b0b11c390a56381ad16ebd13914f8d5",
        "actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065",
        "astral-sh/setup-uv@d0cc045d04ccac9d8b7881df0226f9e82c39688e",
    ):
        assert action in workflow


def test_migration_restored_wal_database_accepts_all_owners_and_passes_integrity(
    monkeypatch, tmp_path, capsys
):
    from app import runtime_entrypoint
    from app.memory import database as memory_database
    from shared import backup, migration, storage

    database = tmp_path / "runtime" / "cognitive_os.sqlite"
    backup_dir = tmp_path / "backups"
    database.parent.mkdir(parents=True)

    for module in (storage, memory_database, backup, migration):
        monkeypatch.setattr(module, "DB_PATH", database)
    monkeypatch.setattr(backup, "BACKUP_DIR", backup_dir)
    monkeypatch.setattr(migration, "BACKUP_DIR", backup_dir)

    # Simulate a database freshly restored from backup: the SQLite backup()
    # API creates a clean copy in DELETE journal mode.  The migration entry
    # point must accept whichever journal mode the restored copy has.
    sqlite3.connect(database).close()

    # Run the real runtime migration entry point on the restored db
    assert runtime_entrypoint.run_migration(Namespace()) == 0
    payload = json.loads(capsys.readouterr().out)

    # All owners report non-failed terminal state
    for result in payload["operator_results"]:
        assert result["state"] == "applied", f"{result['owner']} state: {result['state']}"
    status = payload["status"]
    assert isinstance(status, list)
    for entry in status:
        assert entry["state"] != "failed", f"{entry['owner']} status: {entry['state']}"

    # Integrity is ok
    with sqlite3.connect(database) as connection:
        assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"

    # No production DB path is touched
    assert database == migration.DB_PATH or Path(migration.DB_PATH) == database
