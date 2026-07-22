from __future__ import annotations

import pytest


def _dependent_task() -> dict[str, object]:
    return {
        "id": "sleep-dependent-read",
        "run_id": "run-dependent",
        "title": "Read a governed file after its parent completes",
        "content": "Read AGENTS after the parent is complete",
        "status": "running",
        "executor": "file_read",
        "payload": {"path": "AGENTS.md"},
        "dependencies": ["parent-task"],
        "risk_level": "low",
        "requires_review": False,
    }


def test_sleep_runtime_requires_scheduler_dependency_proof():
    from app.adapters.taskpack import ContractMappingError
    from app.sleep_runtime import execute_sleep_runtime_task

    with pytest.raises(ContractMappingError, match="scheduler dependency proof"):
        execute_sleep_runtime_task(_dependent_task(), satisfied_dependency_ids=[])


def test_sleep_runtime_rejects_caller_supplied_dependency_ids_even_when_they_match():
    from app.adapters.taskpack import ContractMappingError
    from app.sleep_runtime import execute_sleep_runtime_task

    with pytest.raises(ContractMappingError, match="scheduler dependency proof"):
        execute_sleep_runtime_task(
            _dependent_task(),
            satisfied_dependency_ids=["parent-task"],
        )


def test_scheduler_dependency_proof_requires_durable_task_state():
    from shared import sleep_loop_engine as sl

    task = {
        "id": "forged-child",
        "run_id": "forged-run",
        "dependencies": ["forged-parent"],
        "lease_token": "forged-lease-token",
    }
    forged = sl._SchedulerDependencyProof(
        task_id="forged-child",
        run_id="forged-run",
        dependency_ids=frozenset({"forged-parent"}),
        lease_token="forged-lease-token",
        capability=sl._SCHEDULER_PROOF_CAPABILITY,
    )

    with pytest.raises(ValueError, match="durable dependency state"):
        sl.require_scheduler_dependency_proof(task, forged)


def test_scheduler_dependency_proof_requires_matching_durable_lease():
    from shared import sleep_loop_engine as sl

    sl.stop_loop("test_cleanup")
    started = sl.start_loop(
        "lease-bound proof",
        {
            "tasks": [
                {
                    "title": "lease-bound read",
                    "content": "Read a governed file",
                    "executor": "file_read",
                    "payload": {"path": "AGENTS.md"},
                }
            ]
        },
    )
    try:
        claimed = sl.claim_next_task(
            started["run_id"],
            sl.SleepLoopConfig.from_payload(started["config"]),
            worker_id="proof-test-worker",
        )
        assert claimed is not None
        forged = sl._SchedulerDependencyProof(
            task_id=claimed["id"],
            run_id=started["run_id"],
            dependency_ids=frozenset(),
            lease_token="forged-lease-token",
            capability=sl._SCHEDULER_PROOF_CAPABILITY,
        )

        with pytest.raises(ValueError, match="durable lease"):
            sl.require_scheduler_dependency_proof(claimed, forged)
    finally:
        sl.stop_loop("test_done")


def test_scheduler_proof_rejects_forged_dependencies_against_durable_task_row():
    from datetime import datetime, timedelta

    from shared import sleep_loop_engine as sl

    sl.stop_loop("test_cleanup")
    started = sl.start_loop(
        "durable dependency authority",
        {
            "tasks": [
                {
                    "title": "pending parent",
                    "content": "Read the parent evidence",
                    "executor": "file_read",
                    "payload": {"path": "AGENTS.md"},
                }
            ]
        },
    )
    try:
        parent = sl.list_tasks(started["run_id"], limit=10)[0]
        child = sl.add_task(
            started["run_id"],
            {
                "title": "dependent child",
                "content": "Read only after parent evidence is complete",
                "executor": "file_read",
                "payload": {"path": "AGENTS.md"},
                "dependencies": [parent["id"]],
            },
            sl.SleepLoopConfig.from_payload(started["config"]),
        )
        lease_token = "forged-proof-real-lease"
        conn = sl._conn()
        try:
            conn.execute(
                "UPDATE sleep_loop_tasks SET status=?, lease_token=?, lease_expires_at=? "
                "WHERE id=? AND run_id=?",
                (
                    sl.TASK_RUNNING,
                    lease_token,
                    (datetime.now() + timedelta(minutes=1)).isoformat(timespec="microseconds"),
                    child["id"],
                    started["run_id"],
                ),
            )
            conn.commit()
        finally:
            conn.close()
        forged_task = {
            "id": child["id"],
            "run_id": started["run_id"],
            "dependencies": [],
            "lease_token": lease_token,
        }
        forged_proof = sl._SchedulerDependencyProof(
            task_id=child["id"],
            run_id=started["run_id"],
            dependency_ids=frozenset(),
            lease_token=lease_token,
            capability=sl._SCHEDULER_PROOF_CAPABILITY,
        )

        with pytest.raises(ValueError, match="durable task dependencies"):
            sl.require_scheduler_dependency_proof(forged_task, forged_proof)
    finally:
        sl.stop_loop("test_done")


def test_sleep_scheduler_passes_verified_dependency_proof_to_runtime():
    from app.sleep_runtime import configure_sleep_runtime
    from shared import sleep_loop_engine as sl

    configure_sleep_runtime()
    sl.stop_loop("test_cleanup")
    started = sl.start_loop(
        "verified dependency handoff",
        {
            "tasks": [
                {
                    "title": "parent read",
                    "content": "Read the parent evidence",
                    "executor": "file_read",
                    "payload": {"path": "AGENTS.md"},
                }
            ],
            "config": {"max_runtime_hours": None},
        },
    )
    try:
        assert sl.tick_once(worker_id="parent-worker")["success"] is True
        parent = sl.list_tasks(started["run_id"], limit=10)[0]
        child = sl.add_task(
            started["run_id"],
            {
                "title": "child read",
                "content": "Read only after parent evidence is complete",
                "executor": "file_read",
                "payload": {"path": "AGENTS.md"},
                "dependencies": [parent["id"]],
            },
            sl.SleepLoopConfig.from_payload(started["config"]),
        )

        tick = sl.tick_once(worker_id="child-worker")

        persisted = next(
            task for task in sl.list_tasks(started["run_id"], limit=10) if task["id"] == child["id"]
        )
        assert tick["success"] is True
        assert persisted["status"] == "done"
        assert persisted["result"]["runtime_status"] == "done"
        assert persisted["terminal_trace_id"] == persisted["result"]["trace_id"]
    finally:
        sl.stop_loop("test_done")
