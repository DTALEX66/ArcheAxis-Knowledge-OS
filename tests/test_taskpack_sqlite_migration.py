from __future__ import annotations

import builtins
import importlib
import sqlite3
import sys
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing, suppress
from pathlib import Path
from threading import Barrier, BrokenBarrierError

import pytest


def test_migration_import_does_not_require_python311_datetime_utc(monkeypatch) -> None:
    """The supported Python 3.10 runtime does not expose datetime.UTC."""

    original_import = builtins.__import__
    existing_module = sys.modules.pop("shared.migration", None)

    def python310_compatible_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "datetime" and "UTC" in fromlist:
            raise ImportError("cannot import name 'UTC' from 'datetime'")
        return original_import(name, globals, locals, fromlist, level)

    try:
        monkeypatch.setattr(builtins, "__import__", python310_compatible_import)
        imported = importlib.import_module("shared.migration")
        assert imported is not None
    finally:
        sys.modules.pop("shared.migration", None)
        if existing_module is not None:
            sys.modules["shared.migration"] = existing_module


def _create_legacy_taskpack_database(path: Path) -> None:
    with closing(sqlite3.connect(path)) as conn:
        conn.execute(
            """
            CREATE TABLE kb_taskpacks (
                id TEXT PRIMARY KEY,
                goal TEXT NOT NULL,
                steps_json TEXT NOT NULL DEFAULT '[]',
                allowed_tools_json TEXT NOT NULL DEFAULT '[]',
                blocked_tools_json TEXT NOT NULL DEFAULT '[]',
                constraints_json TEXT NOT NULL DEFAULT '[]',
                success_criteria_json TEXT NOT NULL DEFAULT '[]',
                risk_level TEXT NOT NULL DEFAULT 'low',
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        conn.execute(
            """
            INSERT INTO kb_taskpacks (
                id, goal, steps_json, allowed_tools_json, blocked_tools_json,
                constraints_json, success_criteria_json, risk_level
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "task-legacy",
                "Preserve the legacy row",
                '[{"step_id":"s1","action":"inspect","tool":"file_read"}]',
                '["file_read"]',
                '["shell_exec"]',
                '["read only"]',
                '["all fields survive"]',
                "high",
            ),
        )
        conn.commit()


def test_taskpack_migration_backs_up_and_preserves_legacy_policy_fields(tmp_path: Path) -> None:
    from shared.migration import migrate

    database = tmp_path / "runtime.sqlite"
    backups = tmp_path / "backups"
    _create_legacy_taskpack_database(database)

    result = migrate(db_path=database, backup_dir=backups)

    assert result.applied == ("taskpack_contract_v1",)
    assert result.backup_path is not None
    assert result.backup_path.exists()
    with sqlite3.connect(result.backup_path) as backup:
        assert {row[1] for row in backup.execute("PRAGMA table_info(kb_taskpacks)")} == {
            "id",
            "goal",
            "steps_json",
            "allowed_tools_json",
            "blocked_tools_json",
            "constraints_json",
            "success_criteria_json",
            "risk_level",
            "created_at",
        }
    with sqlite3.connect(database) as conn:
        conn.row_factory = sqlite3.Row
        columns = {row[1] for row in conn.execute("PRAGMA table_info(kb_taskpacks)")}
        row = dict(conn.execute("SELECT * FROM kb_taskpacks WHERE id='task-legacy'").fetchone())
        migration = conn.execute(
            "SELECT version, name FROM schema_migrations WHERE version=2"
        ).fetchone()

    assert {"context_id", "requires_review"} <= columns
    assert row["context_id"] == ""
    assert row["requires_review"] == 1
    assert row["steps_json"] == '[{"step_id":"s1","action":"inspect","tool":"file_read"}]'
    assert row["allowed_tools_json"] == '["file_read"]'
    assert row["blocked_tools_json"] == '["shell_exec"]'
    assert row["risk_level"] == "high"
    assert tuple(migration) == (2, "taskpack_contract_v1")

    from app.adapters.taskpack import ContractMappingError, from_taskpack_row, project_to_runtime

    with pytest.raises(ContractMappingError, match="cannot bypass requires_review"):
        project_to_runtime(from_taskpack_row(row))


def test_taskpack_migration_is_idempotent_and_does_not_repeat_backup(tmp_path: Path) -> None:
    from shared.migration import migrate

    database = tmp_path / "runtime.sqlite"
    backups = tmp_path / "backups"
    _create_legacy_taskpack_database(database)

    first = migrate(db_path=database, backup_dir=backups)
    first_bytes = database.read_bytes()
    second = migrate(db_path=database, backup_dir=backups)

    assert first.applied == ("taskpack_contract_v1",)
    assert second.applied == ()
    assert second.backup_path is None
    assert database.read_bytes() == first_bytes
    assert list(backups.glob("*.sqlite")) == [first.backup_path]


def test_taskpack_migration_fails_closed_on_version_name_collision(tmp_path: Path) -> None:
    from shared.migration import migrate, status

    database = tmp_path / "runtime.sqlite"
    backups = tmp_path / "backups"
    _create_legacy_taskpack_database(database)
    with sqlite3.connect(database) as conn:
        conn.execute(
            """
            CREATE TABLE schema_migrations (
                version INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                applied_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        conn.execute(
            "INSERT INTO schema_migrations(version, name) VALUES (?, ?)",
            (2, "unrelated_local_migration"),
        )

    with pytest.raises(RuntimeError, match="migration version 2 name collision"):
        migrate(db_path=database, backup_dir=backups)
    with pytest.raises(RuntimeError, match="migration version 2 name collision"):
        status(db_path=database)

    with sqlite3.connect(database) as conn:
        columns = {row[1] for row in conn.execute("PRAGMA table_info(kb_taskpacks)")}
    assert "context_id" not in columns
    assert "requires_review" not in columns
    assert not backups.exists()


def test_taskpack_migration_rejects_applied_record_with_missing_columns(tmp_path: Path) -> None:
    from shared.migration import migrate

    database = tmp_path / "runtime.sqlite"
    backups = tmp_path / "backups"
    _create_legacy_taskpack_database(database)
    with sqlite3.connect(database) as conn:
        conn.execute(
            """
            CREATE TABLE schema_migrations (
                version INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                applied_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        conn.execute(
            "INSERT INTO schema_migrations(version, name) VALUES (?, ?)",
            (2, "taskpack_contract_v1"),
        )

    with pytest.raises(RuntimeError, match="recorded migration schema mismatch"):
        migrate(db_path=database, backup_dir=backups)

    assert not backups.exists()


def test_taskpack_migration_rejects_existing_review_column_without_fail_closed_schema(
    tmp_path: Path,
) -> None:
    from shared.migration import migrate

    database = tmp_path / "runtime.sqlite"
    backups = tmp_path / "backups"
    _create_legacy_taskpack_database(database)
    with sqlite3.connect(database) as conn:
        conn.execute("ALTER TABLE kb_taskpacks ADD COLUMN context_id TEXT NOT NULL DEFAULT ''")
        conn.execute("ALTER TABLE kb_taskpacks ADD COLUMN requires_review INTEGER DEFAULT 0")

    with pytest.raises(RuntimeError, match="requires_review schema is not fail closed"):
        migrate(db_path=database, backup_dir=backups)

    with sqlite3.connect(database) as conn:
        assert conn.execute(
            "SELECT requires_review FROM kb_taskpacks WHERE id='task-legacy'"
        ).fetchone()[0] == 0
        assert not conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='schema_migrations'"
        ).fetchone()
    assert not backups.exists()


def test_storage_startup_detects_version_collision_before_any_ddl(
    monkeypatch, tmp_path: Path
) -> None:
    from shared import migration, storage

    database = tmp_path / "runtime.sqlite"
    backups = tmp_path / "backups"
    with sqlite3.connect(database) as conn:
        conn.execute("CREATE TABLE existing_data (id TEXT PRIMARY KEY)")
        conn.execute(
            """
            CREATE TABLE schema_migrations (
                version INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                applied_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        conn.execute(
            "INSERT INTO schema_migrations(version, name) VALUES (?, ?)",
            (2, "unrelated_local_migration"),
        )
    monkeypatch.setattr(storage, "DB_PATH", database)
    monkeypatch.setattr(migration, "BACKUP_DIR", backups)

    with pytest.raises(RuntimeError, match="migration version 2 name collision"):
        storage.init()

    with sqlite3.connect(database) as conn:
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            )
        }
    assert tables == {"existing_data", "schema_migrations"}
    assert not backups.exists()


def test_taskpack_migration_serializes_concurrent_startup(monkeypatch, tmp_path: Path) -> None:
    from shared import migration

    database = tmp_path / "runtime.sqlite"
    backups = tmp_path / "backups"
    _create_legacy_taskpack_database(database)
    original_create_backup = migration._create_backup
    both_probes_reached_backup = Barrier(2)

    def synchronized_backup(database_path: Path, backup_dir: Path) -> Path:
        with suppress(BrokenBarrierError):
            both_probes_reached_backup.wait(timeout=0.5)
        return original_create_backup(database_path, backup_dir)

    monkeypatch.setattr(migration, "_create_backup", synchronized_backup)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(
            pool.map(
                lambda _: migration.migrate(db_path=database, backup_dir=backups),
                range(2),
            )
        )

    assert sorted(len(result.applied) for result in results) == [0, 1]
    assert len(list(backups.glob("pre_migration_*.sqlite"))) == 1


def test_migrated_taskpack_row_round_trips_canonical_safety_fields(tmp_path: Path) -> None:
    from app.adapters.taskpack import from_taskpack_row, to_taskpack_row
    from shared.migration import migrate

    database = tmp_path / "runtime.sqlite"
    _create_legacy_taskpack_database(database)
    migrate(db_path=database, backup_dir=tmp_path / "backups")
    with sqlite3.connect(database) as conn:
        conn.row_factory = sqlite3.Row
        conn.execute(
            """
            UPDATE kb_taskpacks
            SET context_id=?, requires_review=?, risk_level=?,
                allowed_tools_json=?, blocked_tools_json=?
            WHERE id=?
            """,
            (
                "ctx-reviewed",
                1,
                "critical",
                '["file_read"]',
                '["shell_exec","delete_file"]',
                "task-legacy",
            ),
        )
        row = dict(conn.execute("SELECT * FROM kb_taskpacks WHERE id='task-legacy'").fetchone())

    canonical = from_taskpack_row(row)
    restored = to_taskpack_row(canonical)

    assert canonical.context_id == "ctx-reviewed"
    assert canonical.requires_review is True
    assert canonical.risk_level == "critical"
    assert canonical.requested_tools == ["file_read"]
    assert canonical.declared_allowed_tools == ["file_read"]
    assert canonical.explicitly_blocked_tools == ["shell_exec", "delete_file"]
    assert restored == {
        "id": "task-legacy",
        "context_id": "ctx-reviewed",
        "goal": "Preserve the legacy row",
        "steps": [{"step_id": "s1", "action": "inspect", "tool": "file_read"}],
        "allowed_tools": ["file_read"],
        "blocked_tools": ["shell_exec", "delete_file"],
        "constraints": ["read only"],
        "success_criteria": ["all fields survive"],
        "risk_level": "critical",
        "requires_review": 1,
    }


def test_storage_startup_runs_backed_up_taskpack_migration(monkeypatch, tmp_path: Path) -> None:
    from shared import migration, storage

    database = tmp_path / "runtime.sqlite"
    backups = tmp_path / "backups"
    _create_legacy_taskpack_database(database)
    monkeypatch.setattr(storage, "DB_PATH", database)
    monkeypatch.setattr(migration, "BACKUP_DIR", backups)

    storage.init()

    with sqlite3.connect(database) as conn:
        columns = {row[1] for row in conn.execute("PRAGMA table_info(kb_taskpacks)")}
        applied = conn.execute(
            "SELECT name FROM schema_migrations WHERE version=2"
        ).fetchone()[0]
    assert {"context_id", "requires_review"} <= columns
    assert applied == "taskpack_contract_v1"
    backup_paths = list(backups.glob("pre_migration_*.sqlite"))
    assert len(backup_paths) == 1
    with sqlite3.connect(backup_paths[0]) as backup:
        backup_tables = {
            row[0]
            for row in backup.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            )
        }
    assert backup_tables == {"kb_taskpacks"}


def test_taskpack_migration_rollback_restores_backup_bytes(tmp_path: Path) -> None:
    from shared.migration import migrate, rollback

    database = tmp_path / "runtime.sqlite"
    _create_legacy_taskpack_database(database)
    result = migrate(db_path=database, backup_dir=tmp_path / "backups")
    assert result.backup_path is not None
    backup_bytes = result.backup_path.read_bytes()

    restored = rollback(backup_path=result.backup_path, db_path=database)

    assert restored == database
    assert database.read_bytes() == backup_bytes
    with sqlite3.connect(database) as conn:
        columns = {row[1] for row in conn.execute("PRAGMA table_info(kb_taskpacks)")}
        assert "context_id" not in columns
        assert "requires_review" not in columns
        assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"


def test_taskpack_rollback_rejects_backup_for_a_different_database(tmp_path: Path) -> None:
    from shared.migration import migrate, rollback

    database = tmp_path / "runtime.sqlite"
    wrong_database = tmp_path / "wrong.sqlite"
    _create_legacy_taskpack_database(database)
    _create_legacy_taskpack_database(wrong_database)
    result = migrate(db_path=database, backup_dir=tmp_path / "backups")
    assert result.backup_path is not None
    wrong_bytes = wrong_database.read_bytes()

    with pytest.raises(RuntimeError, match="backup target does not match"):
        rollback(backup_path=result.backup_path, db_path=wrong_database)

    assert wrong_database.read_bytes() == wrong_bytes


def test_taskpack_rollback_rejects_active_delete_journal_transaction(tmp_path: Path) -> None:
    from shared.migration import migrate, rollback

    database = tmp_path / "runtime.sqlite"
    _create_legacy_taskpack_database(database)
    result = migrate(db_path=database, backup_dir=tmp_path / "backups")
    assert result.backup_path is not None
    migrated_bytes = database.read_bytes()

    with sqlite3.connect(database) as active:
        active.execute("PRAGMA journal_mode=DELETE")
        active.execute("BEGIN IMMEDIATE")
        with pytest.raises(RuntimeError, match="database rollback requires offline mode"):
            rollback(backup_path=result.backup_path, db_path=database)

    assert database.read_bytes() == migrated_bytes


def test_taskpack_rollback_rejects_unprovenanced_sqlite_backup(tmp_path: Path) -> None:
    from shared.migration import rollback

    database = tmp_path / "runtime.sqlite"
    arbitrary_backup = tmp_path / "arbitrary.sqlite"
    _create_legacy_taskpack_database(database)
    _create_legacy_taskpack_database(arbitrary_backup)
    database_bytes = database.read_bytes()

    with pytest.raises(RuntimeError, match="backup provenance manifest"):
        rollback(backup_path=arbitrary_backup, db_path=database)

    assert database.read_bytes() == database_bytes


def test_taskpack_rollback_replace_failure_preserves_migrated_database(
    monkeypatch, tmp_path: Path
) -> None:
    from shared.migration import migrate, rollback

    database = tmp_path / "runtime.sqlite"
    _create_legacy_taskpack_database(database)
    result = migrate(db_path=database, backup_dir=tmp_path / "backups")
    assert result.backup_path is not None
    migrated_bytes = database.read_bytes()

    def fail_replace(_source: Path, _target: Path) -> Path:
        raise OSError("simulated atomic replace failure")

    monkeypatch.setattr(Path, "replace", fail_replace)
    with pytest.raises(OSError, match="simulated atomic replace failure"):
        rollback(backup_path=result.backup_path, db_path=database)

    assert database.read_bytes() == migrated_bytes


def test_fresh_storage_defaults_omitted_review_status_to_required(monkeypatch, tmp_path: Path) -> None:
    from shared import migration, storage

    database = tmp_path / "runtime.sqlite"
    monkeypatch.setattr(storage, "DB_PATH", database)
    monkeypatch.setattr(migration, "BACKUP_DIR", tmp_path / "backups")
    storage.init()

    storage.insert(
        "kb_taskpacks",
        {
            "id": "task-unknown-review",
            "goal": "Do not infer missing safety approval",
            "risk_level": "high",
        },
    )

    row = storage.select_one("kb_taskpacks", "task-unknown-review")
    assert row is not None
    assert row["requires_review"] == 1


def test_storage_insert_preserves_complete_knowledge_taskpack(monkeypatch, tmp_path: Path) -> None:
    from knowledge_base.taskpack import TaskPack
    from shared import migration, storage

    database = tmp_path / "runtime.sqlite"
    monkeypatch.setattr(storage, "DB_PATH", database)
    monkeypatch.setattr(migration, "BACKUP_DIR", tmp_path / "backups")
    storage.init()
    task = TaskPack(
        task_id="task-complete",
        context_id="ctx-complete",
        goal="Persist every safety field",
        steps=[{"step_id": "s1", "action": "inspect", "tool": "file_read"}],
        allowed_tools=["file_read"],
        blocked_tools=["shell_exec"],
        constraints=["read only"],
        success_criteria=["round trip"],
        risk_level="high",
        requires_review=True,
    )

    storage.insert("kb_taskpacks", task.to_dict())
    row = storage.select_one("kb_taskpacks", task.task_id)

    assert row == {
        "id": "task-complete",
        "context_id": "ctx-complete",
        "goal": "Persist every safety field",
        "steps": [{"step_id": "s1", "action": "inspect", "tool": "file_read"}],
        "allowed_tools": ["file_read"],
        "blocked_tools": ["shell_exec"],
        "constraints": ["read only"],
        "success_criteria": ["round trip"],
        "risk_level": "high",
        "requires_review": 1,
        "created_at": row["created_at"],
    }


def test_intake_bridge_persists_taskpack_context_link(monkeypatch, tmp_path: Path) -> None:
    from shared import migration, storage

    database = tmp_path / "runtime.sqlite"
    monkeypatch.setattr(storage, "DB_PATH", database)
    monkeypatch.setattr(migration, "BACKUP_DIR", tmp_path / "backups")
    storage.init()

    from shared.bridge import bridge_intake_to_kb

    result = bridge_intake_to_kb(
        {"id": "intake-1", "why": "Evaluate safely", "risk_level": "high"}
    )
    task = storage.select_one("kb_taskpacks", result["taskpack_id"])

    assert task is not None
    assert task["context_id"] == result["context_pack_id"]
    assert task["risk_level"] == "high"
    assert task["allowed_tools"] == ["echo", "file_read"]
    assert task["blocked_tools"] == ["shell_exec", "code_exec", "delete_file"]
