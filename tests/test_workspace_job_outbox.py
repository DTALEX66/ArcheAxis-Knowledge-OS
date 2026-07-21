from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path


def _workspace_database(tmp_path: Path) -> Path:
    from shared.migration_runner import MigrationOperator

    database = tmp_path / "workspace.sqlite"
    with closing(sqlite3.connect(database)) as connection:
        connection.execute("CREATE TABLE sentinel(id TEXT PRIMARY KEY)")
        connection.commit()
    MigrationOperator(db_path=database, backup_dir=tmp_path / "backups").apply("workspace.sqlite")
    return database


def test_enqueue_command_writes_receipt_job_and_outbox_atomically(tmp_path: Path) -> None:
    from app.workspace.job_outbox import enqueue_command

    database = _workspace_database(tmp_path)
    receipt = enqueue_command(
        command_id="cmd-001",
        command_type="intake.research",
        aggregate_id="package-001",
        payload={"package_id": "package-001"},
        db_path=database,
    )

    assert receipt["command_id"] == "cmd-001"
    assert receipt["job_id"]
    assert receipt["event_id"]
    with closing(sqlite3.connect(database)) as second_connection:
        job = second_connection.execute(
            "SELECT state, command_id, aggregate_id FROM workspace_jobs_v1 WHERE job_id=?",
            (receipt["job_id"],),
        ).fetchone()
        event = second_connection.execute(
            "SELECT state, job_id FROM workspace_outbox_v1 WHERE event_id=?",
            (receipt["event_id"],),
        ).fetchone()
        stored = second_connection.execute(
            "SELECT command_type, job_id FROM workspace_command_receipts_v1 WHERE command_id=?",
            ("cmd-001",),
        ).fetchone()
    assert job == ("queued", "cmd-001", "package-001")
    assert event == ("pending", receipt["job_id"])
    assert stored == ("intake.research", receipt["job_id"])


def test_enqueue_command_is_idempotent_and_rejects_conflicting_reuse(tmp_path: Path) -> None:
    import pytest

    from app.workspace.job_outbox import enqueue_command

    database = _workspace_database(tmp_path)
    request = {
        "command_id": "cmd-idempotent",
        "command_type": "intake.research",
        "aggregate_id": "package-001",
        "payload": {"package_id": "package-001"},
        "db_path": database,
    }

    first = enqueue_command(**request)
    assert enqueue_command(**request) == first
    with pytest.raises(RuntimeError, match="command id conflicts with recorded request"):
        enqueue_command(**{**request, "payload": {"package_id": "package-002"}})

    with closing(sqlite3.connect(database)) as connection:
        assert connection.execute("SELECT COUNT(*) FROM workspace_jobs_v1").fetchone()[0] == 1


def test_concurrent_enqueue_of_same_command_creates_one_record_set(tmp_path: Path) -> None:
    from concurrent.futures import ThreadPoolExecutor

    from app.workspace.job_outbox import enqueue_command

    database = _workspace_database(tmp_path)
    request = {
        "command_id": "cmd-concurrent",
        "command_type": "intake.research",
        "aggregate_id": "package-001",
        "payload": {"package_id": "package-001"},
        "db_path": database,
    }
    with ThreadPoolExecutor(max_workers=8) as executor:
        receipts = list(executor.map(lambda _: enqueue_command(**request), range(8)))

    assert len({receipt["job_id"] for receipt in receipts}) == 1
    with closing(sqlite3.connect(database)) as connection:
        assert connection.execute("SELECT COUNT(*) FROM workspace_jobs_v1").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM workspace_outbox_v1").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM workspace_command_receipts_v1").fetchone()[0] == 1


def test_idempotent_replay_rejects_damaged_job_outbox_or_receipt(tmp_path: Path) -> None:
    import pytest

    from app.workspace.job_outbox import enqueue_command

    mutations = (
        "DELETE FROM workspace_jobs_v1",
        "UPDATE workspace_outbox_v1 SET payload_json='{}'",
        "UPDATE workspace_command_receipts_v1 SET result_json='not-json'",
    )
    for index, mutation in enumerate(mutations):
        case_dir = tmp_path / str(index)
        case_dir.mkdir()
        database = _workspace_database(case_dir)
        request = {
            "command_id": f"cmd-damaged-{index}",
            "command_type": "intake.research",
            "aggregate_id": "package-001",
            "payload": {"package_id": "package-001"},
            "db_path": database,
        }
        enqueue_command(**request)
        with closing(sqlite3.connect(database)) as connection:
            connection.execute(mutation)
            connection.commit()

        with pytest.raises(RuntimeError, match="persisted bindings are invalid"):
            enqueue_command(**request)
