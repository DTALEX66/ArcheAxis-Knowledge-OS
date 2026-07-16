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


def _create_partially_migrated_taskpack_database(path: Path, *, review_default: int = 0) -> None:
    _create_legacy_taskpack_database(path)
    with closing(sqlite3.connect(path)) as conn:
        conn.execute("ALTER TABLE kb_taskpacks ADD COLUMN context_id TEXT NOT NULL DEFAULT ''")
        conn.execute(
            "ALTER TABLE kb_taskpacks ADD COLUMN requires_review INTEGER NOT NULL "
            f"DEFAULT {review_default} CHECK(requires_review IN (0, 1))"
        )
        conn.execute(
            """
            CREATE TABLE schema_migrations (
                version INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                applied_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        conn.executemany(
            "INSERT INTO schema_migrations(version, name) VALUES (?, ?)",
            [(1, "initial_schema"), (2, "taskpack_contract_v1")],
        )
        conn.commit()


def test_taskpack_migration_backs_up_and_preserves_legacy_policy_fields(tmp_path: Path) -> None:
    from shared.migration import migrate

    database = tmp_path / "runtime.sqlite"
    backups = tmp_path / "backups"
    _create_legacy_taskpack_database(database)

    result = migrate(db_path=database, backup_dir=backups)

    assert result.applied == (
        "taskpack_contract_v1",
        "taskpack_review_fail_closed_v1",
    )
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

    assert first.applied == (
        "taskpack_contract_v1",
        "taskpack_review_fail_closed_v1",
    )
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


def test_taskpack_migration_rejects_repair_name_collision_before_backup(
    tmp_path: Path,
) -> None:
    from shared.migration import migrate, status

    database = tmp_path / "runtime.sqlite"
    backups = tmp_path / "backups"
    _create_partially_migrated_taskpack_database(database)
    with closing(sqlite3.connect(database)) as connection:
        connection.execute(
            "INSERT INTO schema_migrations(version, name) VALUES (?, ?)",
            (4, "taskpack_review_fail_closed_v1"),
        )
        before_sql = connection.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='kb_taskpacks'"
        ).fetchone()[0]
        connection.commit()

    with pytest.raises(RuntimeError, match="migration version/name collision"):
        migrate(db_path=database, backup_dir=backups)
    with pytest.raises(RuntimeError, match="migration version/name collision"):
        status(db_path=database)

    with closing(sqlite3.connect(database)) as connection:
        after_sql = connection.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='kb_taskpacks'"
        ).fetchone()[0]
        assert (
            connection.execute("SELECT COUNT(*) FROM schema_migrations WHERE version=3").fetchone()[
                0
            ]
            == 0
        )
    assert before_sql == after_sql
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


def test_taskpack_v3_normalizes_old_zero_even_when_schema_is_already_strict(
    tmp_path: Path,
) -> None:
    from shared.migration import migrate

    database = tmp_path / "runtime.sqlite"
    backups = tmp_path / "backups"
    _create_partially_migrated_taskpack_database(database, review_default=1)
    with closing(sqlite3.connect(database)) as connection:
        connection.execute("UPDATE kb_taskpacks SET requires_review=0 WHERE id='task-legacy'")
        connection.commit()

    result = migrate(db_path=database, backup_dir=backups)

    assert result.applied == ("taskpack_review_fail_closed_v1",)
    assert result.backup_path is not None
    with closing(sqlite3.connect(database)) as connection:
        assert (
            connection.execute(
                "SELECT requires_review FROM kb_taskpacks WHERE id='task-legacy'"
            ).fetchone()[0]
            == 1
        )
        assert (
            connection.execute("SELECT name FROM schema_migrations WHERE version=3").fetchone()[0]
            == "taskpack_review_fail_closed_v1"
        )
        connection.execute("UPDATE kb_taskpacks SET requires_review=0 WHERE id='task-legacy'")
        connection.commit()

    second = migrate(db_path=database, backup_dir=backups)
    assert second.applied == ()
    assert second.backup_path is None
    with closing(sqlite3.connect(database)) as connection:
        assert (
            connection.execute(
                "SELECT requires_review FROM kb_taskpacks WHERE id='task-legacy'"
            ).fetchone()[0]
            == 0
        )


def test_taskpack_migration_repairs_existing_review_column_without_fail_closed_schema(
    tmp_path: Path,
) -> None:
    from shared.migration import migrate

    database = tmp_path / "runtime.sqlite"
    backups = tmp_path / "backups"
    _create_partially_migrated_taskpack_database(database)
    with closing(sqlite3.connect(database)) as connection:
        connection.execute(
            """
            INSERT INTO kb_taskpacks (
                id, context_id, goal, steps_json, allowed_tools_json,
                blocked_tools_json, constraints_json, success_criteria_json,
                risk_level, requires_review, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "task-reviewed",
                "ctx-reviewed",
                "Preserve every distinct field",
                '[{"step_id":"s2"}]',
                '["network"]',
                '["shell"]',
                '["offline"]',
                '["verified"]',
                "high",
                1,
                "2026-07-15 12:00:00",
            ),
        )
        connection.commit()

    result = migrate(db_path=database, backup_dir=backups)

    assert result.applied == ("taskpack_review_fail_closed_v1",)
    assert result.backup_path is not None
    with sqlite3.connect(database) as conn:
        conn.row_factory = sqlite3.Row
        table_sql = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='kb_taskpacks'"
        ).fetchone()[0]
        columns = {
            str(row["name"]): row
            for row in conn.execute("PRAGMA table_info(kb_taskpacks)").fetchall()
        }
        rows = conn.execute("SELECT * FROM kb_taskpacks ORDER BY id").fetchall()
        applied = conn.execute(
            "SELECT version, name FROM schema_migrations ORDER BY version"
        ).fetchall()

    assert columns["requires_review"]["notnull"] == 1
    assert columns["requires_review"]["dflt_value"] == "1"
    assert "CHECK(requires_review IN (0, 1))" in table_sql
    assert [row["requires_review"] for row in rows] == [1, 1]
    legacy_row, reviewed_row = rows
    assert legacy_row["goal"] == "Preserve the legacy row"
    assert legacy_row["allowed_tools_json"] == '["file_read"]'
    assert tuple(reviewed_row) == (
        "task-reviewed",
        "ctx-reviewed",
        "Preserve every distinct field",
        '[{"step_id":"s2"}]',
        '["network"]',
        '["shell"]',
        '["offline"]',
        '["verified"]',
        "high",
        1,
        "2026-07-15 12:00:00",
    )
    assert [tuple(item) for item in applied] == [
        (1, "initial_schema"),
        (2, "taskpack_contract_v1"),
        (3, "taskpack_review_fail_closed_v1"),
    ]


def test_taskpack_repair_enforces_review_constraint_behavior(tmp_path: Path) -> None:
    from shared.migration import migrate

    database = tmp_path / "runtime.sqlite"
    _create_partially_migrated_taskpack_database(database)
    migrate(db_path=database, backup_dir=tmp_path / "backups")

    with closing(sqlite3.connect(database)) as connection:
        connection.execute(
            "INSERT INTO kb_taskpacks(id, goal) VALUES (?, ?)",
            ("task-default-review", "Default review must fail closed"),
        )
        assert (
            connection.execute(
                "SELECT requires_review FROM kb_taskpacks WHERE id='task-default-review'"
            ).fetchone()[0]
            == 1
        )
        for index, invalid_value in enumerate((None, 2, -1)):
            with pytest.raises(sqlite3.IntegrityError):
                connection.execute(
                    "INSERT INTO kb_taskpacks(id, goal, requires_review) VALUES (?, ?, ?)",
                    (f"task-invalid-{index}", "Reject invalid review", invalid_value),
                )


def test_taskpack_repair_validation_failure_rolls_back_atomically(
    monkeypatch, tmp_path: Path
) -> None:
    from shared import migration

    database = tmp_path / "runtime.sqlite"
    backups = tmp_path / "backups"
    _create_partially_migrated_taskpack_database(database)
    with closing(sqlite3.connect(database)) as connection:
        before_sql = connection.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='kb_taskpacks'"
        ).fetchone()[0]
        before_rows = connection.execute("SELECT * FROM kb_taskpacks ORDER BY id").fetchall()
        before_migrations = connection.execute(
            "SELECT version, name FROM schema_migrations ORDER BY version"
        ).fetchall()

    def reject_copy(_connection: sqlite3.Connection) -> None:
        raise RuntimeError("injected copy verification failure")

    monkeypatch.setattr(migration, "_validate_taskpack_repair_copy", reject_copy)
    with pytest.raises(RuntimeError, match="injected copy verification failure"):
        migration.migrate(db_path=database, backup_dir=backups)

    with closing(sqlite3.connect(database)) as connection:
        after_sql = connection.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='kb_taskpacks'"
        ).fetchone()[0]
        after_rows = connection.execute("SELECT * FROM kb_taskpacks ORDER BY id").fetchall()
        after_migrations = connection.execute(
            "SELECT version, name FROM schema_migrations ORDER BY version"
        ).fetchall()
        assert (
            connection.execute(
                "SELECT COUNT(*) FROM sqlite_master WHERE name='kb_taskpacks__repair'"
            ).fetchone()[0]
            == 0
        )
    assert after_sql == before_sql
    assert after_rows == before_rows
    assert after_migrations == before_migrations
    assert len(list(backups.glob("pre_migration_*.sqlite"))) == 1


def test_taskpack_repair_preserves_explicit_indexes(tmp_path: Path) -> None:
    from shared.migration import migrate

    database = tmp_path / "runtime.sqlite"
    _create_partially_migrated_taskpack_database(database)
    with closing(sqlite3.connect(database)) as connection:
        connection.execute("CREATE INDEX idx_taskpack_goal ON kb_taskpacks(goal)")

    migrate(db_path=database, backup_dir=tmp_path / "backups")

    with closing(sqlite3.connect(database)) as connection:
        index_sql = connection.execute(
            "SELECT sql FROM sqlite_master WHERE type='index' AND name='idx_taskpack_goal'"
        ).fetchone()
    assert index_sql is not None
    assert "kb_taskpacks(goal)" in index_sql[0]


def test_taskpack_repair_rejects_extra_implicit_unique_constraint_without_replacement(
    tmp_path: Path,
) -> None:
    from shared.migration import migrate

    database = tmp_path / "runtime.sqlite"
    backups = tmp_path / "backups"
    with closing(sqlite3.connect(database)) as connection:
        connection.executescript(
            """
            CREATE TABLE kb_taskpacks (
                id TEXT PRIMARY KEY,
                context_id TEXT NOT NULL DEFAULT '',
                goal TEXT NOT NULL,
                steps_json TEXT NOT NULL DEFAULT '[]',
                allowed_tools_json TEXT NOT NULL DEFAULT '[]',
                blocked_tools_json TEXT NOT NULL DEFAULT '[]',
                constraints_json TEXT NOT NULL DEFAULT '[]',
                success_criteria_json TEXT NOT NULL DEFAULT '[]',
                risk_level TEXT NOT NULL DEFAULT 'low',
                requires_review INTEGER NOT NULL DEFAULT 0 CHECK(requires_review IN (0, 1)),
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                UNIQUE(goal)
            );
            CREATE TABLE schema_migrations (
                version INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                applied_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
            INSERT INTO schema_migrations(version, name)
            VALUES (2, 'taskpack_contract_v1');
            INSERT INTO kb_taskpacks(id, goal)
            VALUES ('task-unique', 'unique goal must remain constrained');
            """
        )
        connection.commit()
        before_schema = connection.execute(
            "SELECT type, name, tbl_name, sql FROM sqlite_master "
            "WHERE tbl_name='kb_taskpacks' OR name='kb_taskpacks' "
            "ORDER BY type, name"
        ).fetchall()
        before_rows = connection.execute("SELECT * FROM kb_taskpacks ORDER BY id").fetchall()
        before_migrations = connection.execute(
            "SELECT version, name FROM schema_migrations ORDER BY version"
        ).fetchall()

    with pytest.raises(RuntimeError, match="unsupported kb_taskpacks table constraints"):
        migrate(db_path=database, backup_dir=backups)

    with closing(sqlite3.connect(database)) as connection:
        after_schema = connection.execute(
            "SELECT type, name, tbl_name, sql FROM sqlite_master "
            "WHERE tbl_name='kb_taskpacks' OR name='kb_taskpacks' "
            "ORDER BY type, name"
        ).fetchall()
        after_rows = connection.execute("SELECT * FROM kb_taskpacks ORDER BY id").fetchall()
        after_migrations = connection.execute(
            "SELECT version, name FROM schema_migrations ORDER BY version"
        ).fetchall()
        assert (
            connection.execute("SELECT COUNT(*) FROM schema_migrations WHERE version=3").fetchone()[
                0
            ]
            == 0
        )
    assert after_schema == before_schema
    assert after_rows == before_rows
    assert after_migrations == before_migrations


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


def test_taskpack_migration_connection_waits_for_long_running_peer(tmp_path: Path) -> None:
    from shared import migration

    database = tmp_path / "runtime.sqlite"
    _create_legacy_taskpack_database(database)

    with closing(migration._connect(database)) as connection:
        assert connection.execute("PRAGMA busy_timeout").fetchone()[0] == 30_000


def test_taskpack_migration_serializes_concurrent_startup(monkeypatch, tmp_path: Path) -> None:
    from shared import migration

    database = tmp_path / "runtime.sqlite"
    backups = tmp_path / "backups"
    _create_legacy_taskpack_database(database)
    original_create_backup = migration._create_backup
    both_probes_reached_backup = Barrier(2)

    def synchronized_backup(
        database_path: Path,
        backup_dir: Path,
        migration_name: str,
        *,
        operator_run_id: str | None = None,
    ) -> Path:
        with suppress(BrokenBarrierError):
            both_probes_reached_backup.wait(timeout=0.5)
        return original_create_backup(
            database_path,
            backup_dir,
            migration_name,
            operator_run_id=operator_run_id,
        )

    monkeypatch.setattr(migration, "_create_backup", synchronized_backup)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(
            pool.map(
                lambda _: migration.migrate(db_path=database, backup_dir=backups),
                range(2),
            )
        )

    assert sorted(len(result.applied) for result in results) == [0, 2]
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
        applied = conn.execute("SELECT name FROM schema_migrations WHERE version=2").fetchone()[0]
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


def test_storage_startup_repairs_partial_v2_once(monkeypatch, tmp_path: Path) -> None:
    from shared import migration, storage

    database = tmp_path / "runtime.sqlite"
    backups = tmp_path / "backups"
    _create_partially_migrated_taskpack_database(database)
    monkeypatch.setattr(storage, "DB_PATH", database)
    monkeypatch.setattr(migration, "BACKUP_DIR", backups)

    storage.init()
    first_backups = list(backups.glob("pre_migration_*.sqlite"))
    storage.init()

    with closing(sqlite3.connect(database)) as connection:
        table_sql = connection.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='kb_taskpacks'"
        ).fetchone()[0]
        migrations = connection.execute(
            "SELECT version, name FROM schema_migrations WHERE version IN (2, 3) ORDER BY version"
        ).fetchall()
        review = connection.execute(
            "SELECT requires_review FROM kb_taskpacks WHERE id='task-legacy'"
        ).fetchone()[0]
    assert "DEFAULT 1" in table_sql
    assert review == 1
    assert migrations == [
        (2, "taskpack_contract_v1"),
        (3, "taskpack_review_fail_closed_v1"),
    ]
    assert len(first_backups) == 1
    assert list(backups.glob("pre_migration_*.sqlite")) == first_backups


def test_taskpack_repair_rollback_handles_idle_wal_sidecars(tmp_path: Path) -> None:
    from shared.migration import migrate, rollback

    database = tmp_path / "runtime.sqlite"
    _create_partially_migrated_taskpack_database(database)
    with closing(sqlite3.connect(database)) as connection:
        assert connection.execute("PRAGMA journal_mode=WAL").fetchone()[0] == "wal"

    result = migrate(db_path=database, backup_dir=tmp_path / "backups")
    assert result.backup_path is not None
    backup_bytes = result.backup_path.read_bytes()

    restored = rollback(backup_path=result.backup_path, db_path=database)

    assert restored == database
    assert database.read_bytes() == backup_bytes
    with sqlite3.connect(database) as connection:
        sql = connection.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='kb_taskpacks'"
        ).fetchone()[0]
    assert "DEFAULT 0" in sql


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


def test_fresh_storage_defaults_omitted_review_status_to_required(
    monkeypatch, tmp_path: Path
) -> None:
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


def test_intake_bridge_fails_closed_without_phase5_review_provenance(
    monkeypatch, tmp_path: Path
) -> None:
    from shared import migration, storage

    database = tmp_path / "runtime.sqlite"
    monkeypatch.setattr(storage, "DB_PATH", database)
    monkeypatch.setattr(migration, "BACKUP_DIR", tmp_path / "backups")
    storage.init()

    from shared.bridge import bridge_intake_to_kb

    with sqlite3.connect(database) as connection:
        before = tuple(
            connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in ("kb_context_packs", "kb_taskpacks")
        )
    with pytest.raises(RuntimeError, match="server-owned review provenance"):
        bridge_intake_to_kb({"id": "intake-1", "why": "Evaluate safely", "risk_level": "high"})
    with sqlite3.connect(database) as connection:
        after = tuple(
            connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in ("kb_context_packs", "kb_taskpacks")
        )
    assert after == before
