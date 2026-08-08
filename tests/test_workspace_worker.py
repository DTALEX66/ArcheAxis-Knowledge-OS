from __future__ import annotations

from pathlib import Path

from tests.test_workspace_outbox_dispatcher import _workspace_database


def _enqueue(database: Path, command_id: str) -> None:
    from app.workspace.job_outbox import enqueue_command

    enqueue_command(
        command_id=command_id,
        command_type="intake.research",
        aggregate_id=f"package-{command_id}",
        payload={"package_id": f"package-{command_id}"},
        db_path=database,
    )


def test_worker_drains_events_and_records_durable_summary(tmp_path: Path) -> None:
    from app.workspace.worker import run_worker

    database = _workspace_database(tmp_path)
    _enqueue(database, "worker-001")
    _enqueue(database, "worker-002")

    def receive(event: dict[str, object]) -> dict[str, object]:
        return {
            "event_id": event["event_id"],
            "lease_token": event["lease_token"],
            "proof": {"consumer": "worker-test"},
        }

    result = run_worker(
        db_path=database,
        worker_name="workspace-background-test",
        handler=receive,
        max_events=10,
    )

    assert result == {"status": "idle", "processed": 2, "failed": 0}
    resumed = run_worker(
        db_path=database,
        worker_name="workspace-background-test",
        handler=receive,
        max_events=10,
    )
    assert resumed == {"status": "idle", "processed": 0, "failed": 0}


def test_worker_stops_at_max_events_without_losing_pending_work(tmp_path: Path) -> None:
    from app.workspace.worker import run_worker

    database = _workspace_database(tmp_path)
    _enqueue(database, "worker-limit-001")
    _enqueue(database, "worker-limit-002")

    def receive(event: dict[str, object]) -> dict[str, object]:
        return {
            "event_id": event["event_id"],
            "lease_token": event["lease_token"],
            "proof": {"consumer": "worker-test"},
        }

    result = run_worker(
        db_path=database,
        worker_name="workspace-background-limit-test",
        handler=receive,
        max_events=1,
    )
    assert result == {"status": "max_events", "processed": 1, "failed": 0}

    resumed = run_worker(
        db_path=database,
        worker_name="workspace-background-limit-test",
        handler=receive,
        max_events=10,
    )
    assert resumed == {"status": "idle", "processed": 1, "failed": 0}
