from __future__ import annotations

import sqlite3
from contextlib import closing
from inspect import getsource
from pathlib import Path

import pytest

_LEGACY_SCHEMA_SQL = """
CREATE TABLE sleep_loop_runs (
    id TEXT PRIMARY KEY, status TEXT NOT NULL DEFAULT 'idle', goal TEXT NOT NULL DEFAULT '',
    cycle_no INTEGER NOT NULL DEFAULT 0, failure_streak INTEGER NOT NULL DEFAULT 0,
    next_cycle_at TEXT, started_at TEXT NOT NULL, updated_at TEXT NOT NULL, stopped_at TEXT,
    stop_reason TEXT NOT NULL DEFAULT '', config_json TEXT NOT NULL DEFAULT '{}',
    seed_tasks_json TEXT NOT NULL DEFAULT '[]'
);
CREATE TABLE sleep_loop_tasks (
    id TEXT PRIMARY KEY, run_id TEXT NOT NULL, parent_id TEXT NOT NULL DEFAULT '',
    cycle_no INTEGER NOT NULL DEFAULT 0, title TEXT NOT NULL, content TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending', priority INTEGER NOT NULL DEFAULT 100,
    executor TEXT NOT NULL DEFAULT 'kb_search', payload_json TEXT NOT NULL DEFAULT '{}',
    dependencies_json TEXT NOT NULL DEFAULT '[]', retries INTEGER NOT NULL DEFAULT 0,
    max_retries INTEGER NOT NULL DEFAULT 3, derived_count INTEGER NOT NULL DEFAULT 0,
    risk_level TEXT NOT NULL DEFAULT 'low', result_json TEXT NOT NULL DEFAULT '{}',
    error TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL, started_at TEXT, finished_at TEXT
);
CREATE INDEX idx_sleep_loop_tasks_run_status
ON sleep_loop_tasks(run_id, status, priority, created_at);
CREATE INDEX idx_sleep_loop_tasks_parent ON sleep_loop_tasks(parent_id);
CREATE TABLE sleep_loop_events (
    id TEXT PRIMARY KEY, run_id TEXT NOT NULL DEFAULT '', task_id TEXT NOT NULL DEFAULT '',
    level TEXT NOT NULL DEFAULT 'info', event_type TEXT NOT NULL, message TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}', created_at TEXT NOT NULL
);
CREATE INDEX idx_sleep_loop_events_run_created
ON sleep_loop_events(run_id, created_at DESC);
"""


def _state(items: list[dict[str, object]], owner: str) -> dict[str, object]:
    return next(item for item in items if item["owner"] == owner)


def _migrate_all_sqlite_owners(database: Path, backups: Path):
    from shared.migration_runner import MigrationOperator

    operator = MigrationOperator(db_path=database, backup_dir=backups)
    for owner in operator.registry.owners:
        if owner.kind.startswith("sqlite"):
            operator.apply(owner.owner)
    return operator


def test_sleep_loop_owner_creates_lease_schema_with_provenance_and_rollback(
    tmp_path: Path,
) -> None:
    from shared.migration_runner import MigrationOperator

    database = tmp_path / "runtime.sqlite"
    backups = tmp_path / "backups"
    with closing(sqlite3.connect(database)):
        pass
    operator = MigrationOperator(db_path=database, backup_dir=backups)

    assert _state(operator.status(), "sleep-loop.sqlite")["state"] == "pending"
    applied = operator.apply("sleep-loop.sqlite")
    assert applied["state"] == "applied"
    assert applied["provenance"]["backup_sha256"]
    assert operator.apply("sleep-loop.sqlite")["state"] == "applied"

    with closing(sqlite3.connect(database)) as connection:
        columns = {
            str(row[1]) for row in connection.execute("PRAGMA table_info(sleep_loop_tasks)")
        }
        assert {
            "requires_review",
            "idempotency_key",
            "request_fingerprint",
            "attempt_no",
            "lease_owner",
            "lease_token",
            "lease_expires_at",
            "heartbeat_at",
            "next_attempt_at",
            "terminal_trace_id",
        }.issubset(columns)

    rolled_back = operator.rollback("sleep-loop.sqlite")
    assert rolled_back["state"] == "rolled_back"
    with closing(sqlite3.connect(database)) as connection:
        assert connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='sleep_loop_tasks'"
        ).fetchone() is None


def test_sleep_loop_runtime_refuses_to_create_an_unmigrated_schema(
    monkeypatch, tmp_path: Path
) -> None:
    from shared import sleep_loop_engine as sleep_loop

    database = tmp_path / "unmigrated.sqlite"
    with closing(sqlite3.connect(database)):
        pass
    monkeypatch.setattr(sleep_loop, "DB_PATH", database)
    monkeypatch.setattr(sleep_loop, "_conn", lambda: sqlite3.connect(database))

    with pytest.raises(RuntimeError, match="sleep loop schema migration is pending"):
        sleep_loop.init_sleep_loop_schema()

    with closing(sqlite3.connect(database)) as connection:
        assert connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='sleep_loop_tasks'"
        ).fetchone() is None


def test_sleep_loop_schema_rejects_second_active_run(tmp_path: Path) -> None:
    from shared.migration_runner import MigrationOperator

    database = tmp_path / "single-active.sqlite"
    with closing(sqlite3.connect(database)):
        pass
    MigrationOperator(db_path=database, backup_dir=tmp_path / "backups").apply(
        "sleep-loop.sqlite"
    )
    with closing(sqlite3.connect(database)) as connection:
        connection.execute(
            "INSERT INTO sleep_loop_runs(id, status, started_at, updated_at) "
            "VALUES ('active-1', 'running', '2026-01-01', '2026-01-01')"
        )
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "INSERT INTO sleep_loop_runs(id, status, started_at, updated_at) "
                "VALUES ('active-2', 'paused', '2026-01-01', '2026-01-01')"
            )


def test_sleep_loop_runtime_accepts_applied_schema_with_live_wal_sidecars(tmp_path: Path) -> None:
    from shared import sleep_loop_migration
    from shared.migration_runner import MigrationOperator

    database = tmp_path / "runtime.sqlite"
    with closing(sqlite3.connect(database)):
        pass
    MigrationOperator(db_path=database, backup_dir=tmp_path / "backups").apply(
        "sleep-loop.sqlite"
    )
    writer = sqlite3.connect(database)
    try:
        writer.execute("PRAGMA journal_mode=WAL")
        writer.execute("BEGIN IMMEDIATE")
        sleep_loop_migration.require_applied(db_path=database)
    finally:
        writer.rollback()
        writer.close()


def test_sleep_loop_owner_upgrades_recorded_v12_to_review_gate_v13(tmp_path: Path) -> None:
    from shared import migration, sleep_loop_migration
    from shared.migration_runner import MigrationOperator

    database = tmp_path / "lease-v12.sqlite"
    with closing(sqlite3.connect(database)) as connection:
        connection.executescript(sleep_loop_migration.PREVIOUS_SCHEMA_SQL)
        connection.execute(migration.MIGRATIONS_TABLE)
        connection.execute(
            "INSERT INTO schema_migrations(version, name) VALUES (?, ?)",
            (12, migration.SLEEP_LOOP_MIGRATIONS[12]),
        )
        connection.execute(
            "INSERT INTO sleep_loop_runs(id, status, goal, started_at, updated_at) "
            "VALUES ('run-v12', 'stopped', 'upgrade', '2026-01-01', '2026-01-01')"
        )
        connection.execute(
            "INSERT INTO sleep_loop_tasks(id, run_id, title, content, created_at) "
            "VALUES ('task-v12', 'run-v12', 'review', 'review', '2026-01-01')"
        )
        connection.commit()

    operator = MigrationOperator(db_path=database, backup_dir=tmp_path / "backups")
    applied = operator.apply("sleep-loop.sqlite")

    assert applied["state"] == "applied"
    assert applied["provenance"]["applied_migrations"] == [
        migration.SLEEP_LOOP_MIGRATIONS[13]
    ]
    with closing(sqlite3.connect(database)) as connection:
        assert connection.execute(
            "SELECT requires_review FROM sleep_loop_tasks WHERE id='task-v12'"
        ).fetchone()[0] == 1
        assert connection.execute(
            "SELECT version, name FROM schema_migrations WHERE version IN (12, 13) "
            "ORDER BY version"
        ).fetchall() == list(migration.SLEEP_LOOP_MIGRATIONS.items())


def test_sleep_loop_owner_upgrades_legacy_ledger_without_losing_rows(tmp_path: Path) -> None:
    from shared.migration_runner import MigrationOperator

    database = tmp_path / "legacy.sqlite"
    with closing(sqlite3.connect(database)) as connection:
        connection.executescript(_LEGACY_SCHEMA_SQL)
        connection.execute(
            "INSERT INTO sleep_loop_runs(id, status, goal, started_at, updated_at) "
            "VALUES ('run-1', 'running', 'preserve', '2026-01-01', '2026-01-01')"
        )
        connection.execute(
            "INSERT INTO sleep_loop_tasks(id, run_id, title, content, created_at) "
            "VALUES ('task-1', 'run-1', 'preserve', 'preserve', '2026-01-01')"
        )
        connection.execute(
            "INSERT INTO sleep_loop_tasks(id, run_id, title, content, status, executor, "
            "created_at) VALUES ('task-read', 'run-1', 'read', 'read', 'running', "
            "'file_read', '2026-01-01')"
        )
        connection.execute(
            "INSERT INTO sleep_loop_tasks(id, run_id, title, content, status, executor, "
            "created_at) VALUES ('task-write', 'run-1', 'write', 'write', 'running', "
            "'safe_write', '2026-01-01')"
        )
        connection.execute(
            "INSERT INTO sleep_loop_events(id, run_id, task_id, event_type, message, created_at) "
            "VALUES ('event-1', 'run-1', 'task-1', 'queued', 'preserve', '2026-01-01')"
        )
        connection.commit()

    operator = MigrationOperator(db_path=database, backup_dir=tmp_path / "backups")
    applied = operator.apply("sleep-loop.sqlite")

    assert applied["state"] == "applied"
    with closing(sqlite3.connect(database)) as connection:
        connection.row_factory = sqlite3.Row
        task = connection.execute(
            "SELECT * FROM sleep_loop_tasks WHERE id='task-1'"
        ).fetchone()
        assert task is not None
        assert task["requires_review"] == 1
        assert task["lease_token"] == ""
        assert task["attempt_no"] == 0
        recovered = {
            str(row["id"]): (str(row["status"]), str(row["error"]))
            for row in connection.execute(
                "SELECT id, status, error FROM sleep_loop_tasks WHERE id IN ('task-read', 'task-write')"
            )
        }
        assert recovered["task-read"] == ("pending", "legacy_running_requeued")
        assert recovered["task-write"] == (
            "blocked",
            "unknown_outcome_requires_reconciliation",
        )
        assert connection.execute("SELECT COUNT(*) FROM sleep_loop_runs").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM sleep_loop_events").fetchone()[0] == 1

    operator.rollback("sleep-loop.sqlite")
    with closing(sqlite3.connect(database)) as connection:
        columns = {
            str(row[1]) for row in connection.execute("PRAGMA table_info(sleep_loop_tasks)")
        }
        assert "lease_token" not in columns
        assert connection.execute("SELECT COUNT(*) FROM sleep_loop_tasks").fetchone()[0] == 3


def test_sleep_loop_runtime_rejects_missing_operator_provenance(tmp_path: Path) -> None:
    from shared import sleep_loop_migration
    from shared.migration_runner import MigrationOperator

    database = tmp_path / "missing-provenance.sqlite"
    with closing(sqlite3.connect(database)):
        pass
    operator = MigrationOperator(db_path=database, backup_dir=tmp_path / "backups")
    operator.apply("sleep-loop.sqlite")
    with closing(sqlite3.connect(database)) as connection:
        connection.execute(
            "DELETE FROM migration_operator_runs WHERE owner='sleep-loop.sqlite'"
        )
        connection.commit()

    with pytest.raises(RuntimeError, match="operator provenance"):
        sleep_loop_migration.require_applied(db_path=database)
    assert _state(operator.status(), "sleep-loop.sqlite")["state"] == "failed"


@pytest.mark.parametrize(
    "mutation",
    [
        "DROP TABLE sleep_loop_attempts",
        "CREATE INDEX unexpected_sleep_runtime_index ON sleep_loop_tasks(title)",
        (
            "CREATE TRIGGER unexpected_sleep_runtime_trigger "
            "AFTER UPDATE ON sleep_loop_tasks BEGIN SELECT 1; END"
        ),
    ],
)
def test_core_schema_validation_rejects_sleep_owner_drift(
    monkeypatch, tmp_path: Path, mutation: str
) -> None:
    from shared import storage

    database = tmp_path / "core-sleep-drift.sqlite"
    with closing(sqlite3.connect(database)):
        pass
    _migrate_all_sqlite_owners(database, tmp_path / "backups")
    with closing(sqlite3.connect(database)) as connection:
        connection.execute(mutation)
        connection.commit()
    monkeypatch.setattr(storage, "DB_PATH", database)

    with pytest.raises(RuntimeError, match="sleep loop recorded schema drift"):
        storage.validate_schema()


def test_standalone_sleep_worker_runs_unified_schema_gate_before_loop(monkeypatch) -> None:
    from scripts import sleep_loop_worker
    from shared import storage

    calls = []
    monkeypatch.setattr(storage, "validate_schema_online", lambda: calls.append("validated"))

    sleep_loop_worker._validate_runtime_schema()

    assert calls == ["validated"]
    main_source = getsource(sleep_loop_worker.main)
    assert main_source.index("_validate_runtime_schema()") < main_source.index("while True")
