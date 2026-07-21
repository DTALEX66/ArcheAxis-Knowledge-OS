import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module", autouse=True)
def _migrated_sleep_loop_schema():
    from app.sleep_runtime import configure_sleep_runtime

    configure_sleep_runtime()
    yield


def test_sleep_loop_config_clamps_boundaries():
    from shared.sleep_loop_engine import SleepLoopConfig

    cfg = SleepLoopConfig.from_payload(
        {
            "max_split_tasks": 999,
            "global_queue_limit": 999,
            "derived_task_limit": 99,
            "max_retries": 99,
            "max_parallel_tasks": 99,
            "task_timeout_seconds": 999,
        }
    )

    assert cfg.max_split_tasks == 50
    assert cfg.global_queue_limit == 200
    assert cfg.derived_task_limit == 8
    assert cfg.max_retries == 3
    assert cfg.max_parallel_tasks == 4
    assert cfg.task_timeout_seconds == 120


def test_sleep_loop_runtime_wait_heartbeats_until_completion(monkeypatch):
    import time

    from shared import sleep_loop_engine as sl

    def slow_runtime(_task):
        time.sleep(0.4)
        return {"runtime_status": "done"}

    heartbeats: list[bool] = []
    monkeypatch.setattr(sl, "_execute_runtime_task", slow_runtime)

    result = sl._run_with_timeout({}, 1, heartbeat=lambda: heartbeats.append(True))

    assert result["runtime_status"] == "done"
    assert heartbeats


def test_sleep_loop_enqueue_is_idempotent_and_rejects_key_reuse_conflicts():
    import pytest

    from shared import sleep_loop_engine as sl

    sl.stop_loop("test_cleanup")
    started = sl.start_loop(
        "idempotent enqueue",
        {
            "tasks": [
                {
                    "title": "seed",
                    "content": "seed",
                    "executor": "file_read",
                    "payload": {"path": "AGENTS.md"},
                }
            ],
            "config": {"max_runtime_hours": None},
        },
    )
    cfg = sl.SleepLoopConfig.from_payload(started["config"])
    request = {
        "title": "deduplicated",
        "content": "deduplicated",
        "executor": "file_read",
        "payload": {"path": "AGENTS.md"},
        "idempotency_key": "request-001",
    }

    first = sl.add_task(started["run_id"], request, cfg, cycle_no=1)
    second = sl.add_task(started["run_id"], request, cfg, cycle_no=1)

    assert second["id"] == first["id"]
    assert second["deduplicated"] is True
    with pytest.raises(ValueError, match="idempotency key was reused with a different request"):
        sl.add_task(
            started["run_id"],
            {**request, "content": "conflicting payload"},
            cfg,
            cycle_no=1,
        )
    matching = [
        task
        for task in sl.list_tasks(started["run_id"], limit=10)
        if task["idempotency_key"] == "request-001"
    ]
    assert len(matching) == 1
    assert matching[0]["request_fingerprint"]
    sl.stop_loop("test_done")


def test_sleep_loop_dependencies_are_same_run_and_terminal_failures_propagate():
    import pytest

    from shared import sleep_loop_engine as sl

    sl.stop_loop("test_cleanup")
    started = sl.start_loop(
        "dependency propagation",
        {
            "tasks": [
                {
                    "title": "blocked parent",
                    "content": "blocked parent",
                    "executor": "echo",
                    "payload": {},
                }
            ],
            "config": {"max_runtime_hours": None},
        },
    )
    cfg = sl.SleepLoopConfig.from_payload(started["config"])
    parent = sl.list_tasks(started["run_id"], limit=1)[0]
    assert parent["status"] == "blocked"

    with pytest.raises(ValueError, match="dependencies must exist in the same run"):
        sl.add_task(
            started["run_id"],
            {
                "title": "unknown dependency",
                "content": "unknown dependency",
                "executor": "file_read",
                "payload": {"path": "AGENTS.md"},
                "dependencies": ["missing-task"],
            },
            cfg,
        )
    child = sl.add_task(
        started["run_id"],
        {
            "title": "dependent child",
            "content": "dependent child",
            "executor": "file_read",
            "payload": {"path": "AGENTS.md"},
            "dependencies": [parent["id"]],
        },
        cfg,
    )

    assert sl.claim_next_task(started["run_id"], cfg, worker_id="dependency-worker") is None
    child_row = next(
        task for task in sl.list_tasks(started["run_id"], limit=10) if task["id"] == child["id"]
    )
    assert child_row["status"] == "blocked"
    assert "dependency_terminal_failure" in child_row["error"]
    sl.stop_loop("test_done")


def test_sleep_loop_claim_is_atomic_and_lease_owned_across_workers():
    from concurrent.futures import ThreadPoolExecutor

    from shared import sleep_loop_engine as sl

    sl.stop_loop("test_cleanup")
    started = sl.start_loop(
        "single claim",
        {
            "tasks": [
                {
                    "title": "one task",
                    "content": "one task",
                    "executor": "file_read",
                    "payload": {"path": "AGENTS.md"},
                }
            ],
            "config": {"max_runtime_hours": None, "task_timeout_seconds": 30},
        },
    )
    cfg = sl.SleepLoopConfig.from_payload(started["config"])

    with ThreadPoolExecutor(max_workers=2) as pool:
        claims = list(
            pool.map(
                lambda owner: sl.claim_next_task(started["run_id"], cfg, worker_id=owner),
                ("worker-a", "worker-b"),
            )
        )

    claimed = [claim for claim in claims if claim is not None]
    assert len(claimed) == 1
    assert claimed[0]["status"] == "running"
    assert claimed[0]["lease_owner"] in {"worker-a", "worker-b"}
    assert claimed[0]["lease_token"]
    assert claimed[0]["lease_expires_at"]
    assert claimed[0]["attempt_no"] == 1
    sl.stop_loop("test_done")


def test_sleep_loop_heartbeat_extends_only_the_owned_lease():
    from datetime import datetime, timedelta

    from shared import sleep_loop_engine as sl

    sl.stop_loop("test_cleanup")
    started = sl.start_loop(
        "heartbeat",
        {
            "tasks": [
                {
                    "title": "heartbeat task",
                    "content": "heartbeat task",
                    "executor": "file_read",
                    "payload": {"path": "AGENTS.md"},
                }
            ],
            "config": {"max_runtime_hours": None, "task_timeout_seconds": 30},
        },
    )
    cfg = sl.SleepLoopConfig.from_payload(started["config"])
    claimed = sl.claim_next_task(started["run_id"], cfg, worker_id="heartbeat-worker")
    assert claimed is not None
    heartbeat_at = datetime.now() + timedelta(seconds=5)

    assert sl.heartbeat_task(
        claimed["id"],
        lease_token=claimed["lease_token"],
        worker_id="heartbeat-worker",
        extend_seconds=30,
        now=heartbeat_at,
    )
    assert not sl.heartbeat_task(
        claimed["id"],
        lease_token="wrong-token",
        worker_id="heartbeat-worker",
        extend_seconds=60,
        now=heartbeat_at + timedelta(seconds=1),
    )
    task = sl.list_tasks(started["run_id"], limit=1)[0]
    assert task["heartbeat_at"] == heartbeat_at.isoformat(timespec="microseconds")
    assert task["lease_expires_at"] == (heartbeat_at + timedelta(seconds=30)).isoformat(
        timespec="microseconds"
    )
    sl.stop_loop("test_done")


def test_sleep_loop_stop_clears_inflight_lease():
    from shared import sleep_loop_engine as sl

    sl.stop_loop("test_cleanup")
    started = sl.start_loop(
        "stop inflight",
        {
            "tasks": [
                {
                    "title": "claimed before stop",
                    "content": "claimed before stop",
                    "executor": "file_read",
                    "payload": {"path": "AGENTS.md"},
                }
            ],
            "config": {"max_runtime_hours": None},
        },
    )
    cfg = sl.SleepLoopConfig.from_payload(started["config"])
    assert sl.claim_next_task(started["run_id"], cfg, worker_id="stopped-worker")

    stopped = sl.stop_loop("operator_stop")

    assert stopped["status"] == "stopped"
    task = sl.list_tasks(started["run_id"], limit=1)[0]
    assert task["status"] == "failed"
    assert task["error"] == "operator_stop"
    assert task["lease_owner"] == ""
    assert task["lease_token"] == ""
    assert task["lease_expires_at"] is None
    attempt = sl.list_attempts(task_id=task["id"])[0]
    assert attempt["status"] == "failed"
    assert attempt["error"] == "operator_stop"
    assert attempt["finished_at"]


def test_sleep_loop_paused_run_cannot_claim_new_work():
    from shared import sleep_loop_engine as sl

    sl.stop_loop("test_cleanup")
    started = sl.start_loop(
        "pause claim gate",
        {
            "tasks": [
                {
                    "title": "wait while paused",
                    "content": "wait while paused",
                    "executor": "file_read",
                    "payload": {"path": "AGENTS.md"},
                }
            ],
            "config": {"max_runtime_hours": None},
        },
    )
    cfg = sl.SleepLoopConfig.from_payload(started["config"])

    assert sl.pause_loop("operator_pause")["status"] == "paused"
    assert sl.claim_next_task(started["run_id"], cfg, worker_id="paused-worker") is None
    assert sl.list_tasks(started["run_id"], limit=1)[0]["status"] == "pending"
    assert sl.resume_loop()["status"] == "running"
    assert sl.claim_next_task(started["run_id"], cfg, worker_id="resumed-worker")
    sl.stop_loop("test_done")


def test_sleep_loop_tick_finishes_only_its_lease_and_binds_terminal_trace():
    from shared import sleep_loop_engine as sl

    sl.stop_loop("test_cleanup")
    started = sl.start_loop(
        "trace-bound terminal",
        {
            "tasks": [
                {
                    "title": "read governed file",
                    "content": "read governed file",
                    "executor": "file_read",
                    "payload": {"path": "AGENTS.md"},
                }
            ],
            "config": {"max_runtime_hours": None},
        },
    )

    tick = sl.tick_once(worker_id="terminal-worker")

    assert tick["success"] is True
    task = sl.list_tasks(started["run_id"], limit=1)[0]
    assert task["attempt_no"] == 1
    assert task["terminal_trace_id"] == task["result"]["trace_id"]
    assert task["lease_owner"] == ""
    assert task["lease_token"] == ""
    assert task["lease_expires_at"] is None
    sl.stop_loop("test_done")


def test_sleep_loop_persists_trace_bound_attempt_receipt():
    from shared import sleep_loop_engine as sl

    sl.stop_loop("test_cleanup")
    started = sl.start_loop(
        "attempt receipt",
        {
            "tasks": [
                {
                    "title": "receipt read",
                    "content": "receipt read",
                    "executor": "file_read",
                    "payload": {"path": "AGENTS.md"},
                }
            ],
            "config": {"max_runtime_hours": None},
        },
    )

    tick = sl.tick_once(worker_id="receipt-worker")

    task = sl.list_tasks(started["run_id"], limit=1)[0]
    attempts = sl.list_attempts(task_id=task["id"])
    assert tick["success"] is True
    assert len(attempts) == 1
    assert attempts[0]["attempt_no"] == 1
    assert attempts[0]["status"] == "done"
    assert attempts[0]["trace_id"] == task["terminal_trace_id"]
    assert attempts[0]["lease_owner"] == "receipt-worker"
    assert attempts[0]["finished_at"]
    sl.stop_loop("test_done")


def test_sleep_loop_write_timeout_is_not_blindly_retried(monkeypatch):
    from shared import sleep_loop_engine as sl

    sl.stop_loop("test_cleanup")
    started = sl.start_loop(
        "uncertain write timeout",
        {
            "tasks": [
                {
                    "title": "write once",
                    "content": "write once",
                    "executor": "safe_write",
                    "payload": {
                        "filename": "sleep-timeout.txt",
                        "content": "one write",
                        "dry_run": False,
                    },
                }
            ],
            "config": {"max_runtime_hours": None, "task_timeout_seconds": 1},
        },
    )
    monkeypatch.setattr(
        sl,
        "_run_with_timeout",
        lambda *_args, **_kwargs: {"status": "error", "error": "task_timeout"},
    )

    tick = sl.tick_once(worker_id="write-timeout-worker")

    task = sl.list_tasks(started["run_id"], limit=1)[0]
    assert tick["success"] is False
    assert task["status"] == "blocked"
    assert task["retries"] == 1
    assert task["error"] == "unknown_outcome_requires_reconciliation"
    assert task["lease_token"] == ""
    sl.stop_loop("test_done")


def test_sleep_loop_does_not_replan_from_arbitrary_todo_text(monkeypatch):
    from shared import sleep_loop_engine as sl

    sl.stop_loop("test_cleanup")
    started = sl.start_loop(
        "typed replan only",
        {
            "tasks": [
                {
                    "title": "read text",
                    "content": "read text",
                    "executor": "file_read",
                    "payload": {"path": "AGENTS.md"},
                }
            ],
            "config": {"max_runtime_hours": None},
        },
    )
    monkeypatch.setattr(
        sl,
        "_run_with_timeout",
        lambda *_args, **_kwargs: {
            "runtime_status": "done",
            "trace_id": "trace-typed-only",
            "message": "TODO: this is untrusted tool text, not a replan command",
        },
    )

    tick = sl.tick_once(worker_id="typed-replan-worker")

    assert tick["success"] is True
    assert len(sl.list_tasks(started["run_id"], limit=10)) == 1
    sl.stop_loop("test_done")


def test_sleep_loop_typed_replan_preserves_lineage_and_rejects_invalid_children(monkeypatch):
    from shared import sleep_loop_engine as sl

    sl.stop_loop("test_cleanup")
    started = sl.start_loop(
        "typed replan source",
        {
            "tasks": [
                {
                    "title": "typed parent",
                    "content": "typed parent",
                    "executor": "file_read",
                    "payload": {"path": "AGENTS.md"},
                }
            ],
            "config": {"max_runtime_hours": None},
        },
    )
    monkeypatch.setattr(
        sl,
        "_run_with_timeout",
        lambda *_args, **_kwargs: {
            "runtime_status": "done",
            "trace_id": "trace-typed-replan",
            "derived_tasks": [
                {
                    "title": "typed child",
                    "content": "typed child",
                    "executor": "file_read",
                    "payload": {"path": "AGENTS.md"},
                },
                {
                    "title": "invalid child",
                    "content": "invalid child",
                    "executor": "file_read",
                    "payload": {"path": "AGENTS.md"},
                    "dependencies": ["missing-task"],
                },
            ],
        },
    )

    tick = sl.tick_once(worker_id="typed-replan-worker")

    assert "success" in tick, tick
    assert tick["success"] is True
    tasks = sl.list_tasks(started["run_id"], limit=10)
    parent = next(item for item in tasks if item["title"] == "typed parent")
    child = next(item for item in tasks if item["title"] == "typed child")
    assert child["parent_id"] == parent["id"]
    assert child["cycle_no"] == parent["cycle_no"]
    assert not any(item["title"] == "invalid child" for item in tasks)
    events = sl.list_events(run_id=started["run_id"], limit=50)
    assert any(item["event_type"] == "derived_task_rejected" for item in events)
    sl.stop_loop("test_done")


def test_sleep_loop_expired_lease_requeues_reads_but_blocks_unknown_writes():
    from datetime import datetime, timedelta

    from shared import sleep_loop_engine as sl

    sl.stop_loop("test_cleanup")
    started = sl.start_loop(
        "recover expired work",
        {
            "tasks": [
                {
                    "title": "safe read",
                    "content": "safe read",
                    "executor": "file_read",
                    "payload": {"path": "AGENTS.md"},
                },
                {
                    "title": "uncertain write",
                    "content": "uncertain write",
                    "executor": "safe_write",
                    "payload": {
                        "filename": "sleep-recovery.txt",
                        "content": "uncertain",
                        "dry_run": False,
                    },
                },
            ],
            "config": {"max_runtime_hours": None, "task_timeout_seconds": 1},
        },
    )
    cfg = sl.SleepLoopConfig.from_payload(started["config"])
    assert sl.claim_next_task(started["run_id"], cfg, worker_id="crashed-read")
    assert sl.claim_next_task(started["run_id"], cfg, worker_id="crashed-write")

    recovered = sl.recover_expired_leases(
        started["run_id"], now=datetime.now() + timedelta(seconds=2)
    )

    assert recovered["requeued"] == 1
    assert recovered["requires_reconciliation"] == 1
    tasks = {task["title"]: task for task in sl.list_tasks(started["run_id"], limit=10)}
    assert tasks["safe read"]["status"] == "pending"
    assert tasks["safe read"]["retries"] == 1
    assert tasks["safe read"]["lease_token"] == ""
    assert tasks["safe read"]["next_attempt_at"]
    assert tasks["uncertain write"]["status"] == "blocked"
    assert "unknown_outcome" in tasks["uncertain write"]["error"]
    assert tasks["uncertain write"]["lease_token"] == ""
    read_attempt = sl.list_attempts(task_id=tasks["safe read"]["id"])[0]
    write_attempt = sl.list_attempts(task_id=tasks["uncertain write"]["id"])[0]
    assert read_attempt["status"] == "lease_expired_requeued"
    assert write_attempt["status"] == "reconciliation_required"
    assert read_attempt["finished_at"]
    assert write_attempt["finished_at"]
    sl.stop_loop("test_done")


def test_sleep_loop_tick_recovers_expired_claim_before_scheduling():
    from shared import sleep_loop_engine as sl

    sl.stop_loop("test_cleanup")
    started = sl.start_loop(
        "automatic recovery",
        {
            "tasks": [
                {
                    "title": "recover me",
                    "content": "recover me",
                    "executor": "file_read",
                    "payload": {"path": "AGENTS.md"},
                }
            ],
            "config": {"max_runtime_hours": None, "task_timeout_seconds": 1},
        },
    )
    cfg = sl.SleepLoopConfig.from_payload(started["config"])
    claimed = sl.claim_next_task(started["run_id"], cfg, worker_id="dead-worker")
    assert claimed is not None
    connection = sl._conn()
    connection.execute(
        "UPDATE sleep_loop_tasks SET lease_expires_at='2000-01-01T00:00:00.000000' WHERE id=?",
        (claimed["id"],),
    )
    connection.commit()
    connection.close()

    tick = sl.tick_once(worker_id="replacement-worker")

    task = sl.list_tasks(started["run_id"], limit=1)[0]
    assert tick["message"] == "waiting_for_dependencies"
    assert task["status"] == "pending"
    assert task["retries"] == 1
    sl.stop_loop("test_done")


def test_sleep_loop_start_tick_stop_cycle():
    from shared import sleep_loop_engine as sl

    sl.stop_loop("test_cleanup")
    started = sl.start_loop(
        "夜间任务一；夜间任务二",
        {"config": {"max_split_tasks": 2, "cycle_sleep_seconds": 1, "max_runtime_hours": None}},
    )
    assert started["ok"] is True
    assert started["queued"] == 2

    first = sl.tick_once()
    second = sl.tick_once()
    assert first["ok"] is True
    assert second["ok"] is True

    state = sl.status()
    assert state["active"] is True
    assert state["queue"]["done"] >= 2

    completed = sl.tick_once()
    assert completed["status"] == "stopped"
    assert completed["reason"] == "queue_completed"
    assert sl.status()["active"] is False
    assert len(sl.list_tasks(limit=10)) >= 2


def test_sleep_loop_repeats_only_when_explicitly_enabled():
    from shared import sleep_loop_engine as sl

    sl.stop_loop("test_cleanup")
    started = sl.start_loop(
        "重复任务一；重复任务二",
        {
            "config": {
                "max_split_tasks": 2,
                "cycle_sleep_seconds": 1,
                "max_runtime_hours": None,
                "repeat_seed_tasks": True,
            }
        },
    )
    assert started["ok"] is True

    sl.tick_once()
    sl.tick_once()
    sleep_tick = sl.tick_once()
    assert sleep_tick["status"] == "sleeping"
    assert sleep_tick["next_cycle_at"]

    stopped = sl.stop_loop("test_done")
    assert stopped["ok"] is True


def test_sleep_loop_repeat_seed_scopes_explicit_idempotency_key_by_cycle():
    from shared import sleep_loop_engine as sl

    sl.stop_loop("test_cleanup")
    started = sl.start_loop(
        "repeat keyed seed",
        {
            "tasks": [
                {
                    "title": "repeat keyed read",
                    "content": "repeat keyed read",
                    "executor": "file_read",
                    "payload": {"path": "AGENTS.md"},
                    "idempotency_key": "repeat-key",
                }
            ],
            "config": {
                "cycle_sleep_seconds": 1,
                "max_runtime_hours": None,
                "repeat_seed_tasks": True,
            },
        },
    )
    assert sl.tick_once()["success"] is True
    assert sl.tick_once()["status"] == "sleeping"
    conn = sl._conn()
    conn.execute(
        "UPDATE sleep_loop_runs SET next_cycle_at=? WHERE id=?",
        ("2000-01-01T00:00:00", started["run_id"]),
    )
    conn.commit()
    conn.close()

    next_cycle = sl.tick_once()

    assert next_cycle["cycle_no"] == 2
    tasks = sl.list_tasks(started["run_id"], limit=10)
    assert {item["idempotency_key"] for item in tasks} == {
        "repeat-key",
        "repeat-key:cycle:2",
    }
    cfg = sl.SleepLoopConfig.from_payload(started["config"])
    long_key_task = sl.add_task(
        started["run_id"],
        {
            "title": "long cycle key",
            "content": "long cycle key",
            "executor": "file_read",
            "payload": {"path": "AGENTS.md"},
            "idempotency_key": "x" * 200,
        },
        cfg,
        cycle_no=2,
    )
    stored = next(item for item in sl.list_tasks(started["run_id"], limit=10) if item["id"] == long_key_task["id"])
    assert stored["idempotency_key"].startswith("cycle:2:")
    assert len(stored["idempotency_key"]) <= 200
    sl.stop_loop("test_done")


def test_sleep_loop_hard_boundary_halts():
    from shared import sleep_loop_engine as sl

    sl.stop_loop("test_cleanup")
    started = sl.start_loop(
        "高危测试",
        {
            "tasks": ["批量删除全库数据"],
            "config": {"max_runtime_hours": None},
        },
    )
    assert started["ok"] is True

    state = sl.status()
    assert state["queue"]["blocked"] == 1
    assert state["queue"]["pending"] == 0
    sl.stop_loop("test_done")


def test_sleep_loop_default_split_creates_real_search_tasks():
    from shared import sleep_loop_engine as sl

    sl.stop_loop("test_cleanup")
    started = sl.start_loop(
        "真实任务搜索一；真实任务搜索二",
        {"config": {"max_split_tasks": 2, "max_runtime_hours": None}},
    )

    assert started["ok"] is True
    tasks = sl.list_tasks(run_id=started["run_id"], limit=10)
    assert tasks
    assert {task["executor"] for task in tasks} == {"kb_search"}
    assert all(task["status"] == "pending" for task in tasks)
    sl.stop_loop("test_done")


def test_sleep_loop_blocks_preview_and_placeholder_executors():
    from shared import sleep_loop_engine as sl

    sl.stop_loop("test_cleanup")
    started = sl.start_loop(
        "禁止空壳任务",
        {
            "tasks": [
                {"title": "空壳 echo", "content": "echo is fake", "executor": "echo", "payload": {}},
                {
                    "title": "预览任务包",
                    "content": "dry-run taskpack is preview only",
                    "executor": "taskpack_generate",
                    "payload": {"goal": "preview"},
                },
                {
                    "title": "dry run 写入",
                    "content": "safe_write dry_run is not real",
                    "executor": "safe_write",
                    "payload": {"filename": "fake.txt", "content": "x", "dry_run": True},
                },
            ],
            "config": {"max_runtime_hours": None},
        },
    )

    assert started["ok"] is True
    tasks = sl.list_tasks(run_id=started["run_id"], limit=10)
    assert len(tasks) == 3
    assert {task["status"] for task in tasks} == {"blocked"}
    assert all(
        any(marker in task["error"] for marker in ["non_real_executor", "dry_run_task"])
        for task in tasks
    )
    sl.stop_loop("test_done")


def test_sleep_loop_real_file_read_requires_evidence_before_done():
    from shared import sleep_loop_engine as sl

    sl.stop_loop("test_cleanup")
    started = sl.start_loop(
        "读取真实文件",
        {
            "tasks": [
                {
                    "title": "读取引擎文档",
                    "content": "读取已提交的工程说明，必须返回 path + content evidence",
                    "executor": "file_read",
                    "payload": {"path": "docs/HERMES_SLEEP_LOOP_ENGINE.md"},
                }
            ],
            "config": {"max_runtime_hours": None},
        },
    )

    assert started["ok"] is True
    tick = sl.tick_once()
    assert tick["success"] is True
    task = next(
        item
        for item in sl.list_tasks(run_id=started["run_id"], limit=20)
        if item["executor"] == "file_read"
    )
    result = task["result"]
    assert task["status"] == "done"
    assert result["tool"] == "file_read"
    assert result["path"].endswith("docs\\HERMES_SLEEP_LOOP_ENGINE.md") or result[
        "path"
    ].endswith("docs/HERMES_SLEEP_LOOP_ENGINE.md")
    assert "content" in result
    assert result["real_evidence"] == "file_read_content_evidence"
    sl.stop_loop("test_done")


def test_sleep_loop_executes_only_through_runtime_composite_port(monkeypatch):
    from app.agent import executor as runtime_executor
    from app.tools import registry
    from shared import sleep_loop_engine as sl

    assert callable(runtime_executor.run_tool)

    def reject_direct_registry_call(*args, **kwargs):
        raise AssertionError("sleep loop bypassed the Runtime execution port")

    monkeypatch.setattr(registry, "run_tool", reject_direct_registry_call)
    sl.stop_loop("test_cleanup")
    started = sl.start_loop(
        "通过统一 Runtime 读取真实文件",
        {
            "tasks": [
                {
                    "title": "统一 Runtime 文件读取",
                    "content": "通过统一 Runtime 读取 AGENTS.md",
                    "executor": "file_read",
                    "payload": {"path": "AGENTS.md"},
                }
            ],
            "config": {"max_runtime_hours": None},
        },
    )

    tick = sl.tick_once()
    task = sl.list_tasks(run_id=started["run_id"], limit=10)[0]
    result = task["result"]

    assert tick["success"] is True
    assert task["status"] == "done"
    assert result["runtime_status"] == "done"
    assert result["evaluation"]["success"] is True
    assert result["lesson"]["evidence_trace_id"] == result["trace_id"]
    sl.stop_loop("test_done")


def test_sleep_loop_kb_search_runs_with_real_evidence_in_worker_context():
    from shared import sleep_loop_engine as sl

    sl.stop_loop("test_cleanup")
    started = sl.start_loop(
        "真实 KB 搜索",
        {
            "tasks": [
                {
                    "title": "真实 KB 搜索",
                    "content": "直接在 sleep-loop worker 环境调用 kb_search，必须返回 count+items evidence",
                    "executor": "kb_search",
                    "payload": {"query": "sleep loop real evidence", "top_k": 3},
                }
            ],
            "config": {"max_runtime_hours": None},
        },
    )

    assert started["ok"] is True
    tick = sl.tick_once()
    assert tick["success"] is True
    task = next(
        item
        for item in sl.list_tasks(run_id=started["run_id"], limit=20)
        if item["executor"] == "kb_search" and not item.get("parent_id")
    )
    result = task["result"]
    assert task["status"] == "done"
    assert result["tool"] == "kb_search"
    assert isinstance(result["items"], list)
    assert isinstance(result["count"], int)
    assert result["real_evidence"] == "kb_search_count_evidence"
    sl.stop_loop("test_done")


def test_sleep_loop_api_composite_endpoint():
    import app.main as main
    from shared import sleep_loop_engine as sl

    sl.stop_loop("test_cleanup")
    client = TestClient(main.app)
    headers = {"X-API-Key": "dev-key-change-me"}

    resp = client.post(
        "/sleep-loop?action=start",
        headers=headers,
        json={
            "goal": "API任务一；API任务二",
            "config": {"max_split_tasks": 2, "max_runtime_hours": None},
        },
    )
    assert resp.status_code == 200
    assert resp.json()["ok"] is True

    tick = client.post("/sleep-loop?action=tick", headers=headers, json={})
    assert tick.status_code == 200

    attempts = client.get(
        "/sleep-loop",
        params={"action": "attempts", "run_id": resp.json()["run_id"]},
        headers=headers,
    )
    assert attempts.status_code == 200
    assert "items" in attempts.json(), attempts.json()
    assert len(attempts.json()["items"]) == 1
    assert attempts.json()["items"][0]["status"] == "done"

    status = client.get("/sleep-loop?action=status", headers=headers)
    assert status.status_code == 200
    assert status.json()["active"] is True

    stop = client.post("/sleep-loop?action=stop", headers=headers, json={"reason": "test_done"})
    assert stop.status_code == 200
    assert stop.json()["ok"] is True


def test_sleep_loop_survives_worker_process_restarts_with_durable_readback():
    import json
    import subprocess
    import sys

    from shared import sleep_loop_engine as sl

    sl.stop_loop("test_cleanup")
    started = sl.start_loop(
        "process restart durability",
        {
            "tasks": [
                {
                    "title": "restart read one",
                    "content": "restart read one",
                    "executor": "file_read",
                    "payload": {"path": "AGENTS.md"},
                },
                {
                    "title": "restart read two",
                    "content": "restart read two",
                    "executor": "file_read",
                    "payload": {"path": "README.md"},
                },
            ],
            "config": {"max_runtime_hours": None},
        },
    )
    command = [
        sys.executable,
        "-c",
        (
            "import json; "
            "from app.sleep_runtime import tick_once; "
            "print(json.dumps(tick_once(worker_id='restart-worker')))"
        ),
    ]

    results = [
        json.loads(
            subprocess.run(
                command,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
        )
        for _ in range(3)
    ]

    assert results[0]["success"] is True
    assert results[1]["success"] is True
    assert results[2]["status"] == "stopped"
    assert results[2]["reason"] == "queue_completed"
    assert sl.status()["active"] is False
    tasks = sl.list_tasks(started["run_id"], limit=10)
    assert {item["status"] for item in tasks} == {"done"}
    attempts = sl.list_attempts(run_id=started["run_id"], limit=10)
    assert len(attempts) == 2
    assert {item["status"] for item in attempts} == {"done"}
    assert all(item["trace_id"] for item in attempts)


def test_sleep_loop_requires_review_survives_ledger_roundtrip_and_fingerprint():
    import pytest

    from app.adapters.sleep_taskpack import (
        ContractMappingError,
        project_sleep_ledger_task_for_execution,
    )
    from shared import sleep_loop_engine as sl

    sl.stop_loop("test_cleanup")
    request = {
        "title": "reviewed write",
        "content": "reviewed write",
        "executor": "safe_write",
        "payload": {"filename": "reviewed.txt", "content": "x", "dry_run": False},
        "requires_review": True,
        "idempotency_key": "reviewed-write-1",
    }
    started = sl.start_loop(
        "review gate persistence",
        {"tasks": [request], "config": {"max_runtime_hours": None}},
    )
    cfg = sl.SleepLoopConfig.from_payload(started["config"])
    persisted = sl.list_tasks(started["run_id"], limit=1)[0]

    assert bool(persisted["requires_review"]) is True
    with pytest.raises(ContractMappingError, match="requires_review"):
        project_sleep_ledger_task_for_execution(
            persisted,
            declared_allowed_tools=["safe_write"],
        )
    with pytest.raises(ValueError, match="idempotency key was reused"):
        sl.add_task(
            started["run_id"],
            {**request, "requires_review": False},
            cfg,
            cycle_no=1,
        )
    sl.stop_loop("test_done")
