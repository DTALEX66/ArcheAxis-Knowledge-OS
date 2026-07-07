from fastapi.testclient import TestClient


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

    status = client.get("/sleep-loop?action=status", headers=headers)
    assert status.status_code == 200
    assert status.json()["active"] is True

    stop = client.post("/sleep-loop?action=stop", headers=headers, json={"reason": "test_done"})
    assert stop.status_code == 200
    assert stop.json()["ok"] is True
