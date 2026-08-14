"""AXW-RUN-204 — Backend Supervisor state machine + API tests.

Proves legal state transitions, illegal transitions fail closed, the log
ring buffer is bounded, concurrent status calls are thread-safe, and the
system API (status/restart) behaves honestly over TestClient.
"""

from __future__ import annotations

import threading
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.workspace.supervisor import BackendSupervisor, BackendSupervisorState


def test_start_reaches_ready_with_recorded_events() -> None:
    supervisor = BackendSupervisor()
    assert supervisor.state is BackendSupervisorState.STOPPED
    supervisor.start()
    assert supervisor.state is BackendSupervisorState.READY
    events = supervisor.events()
    assert [event["from"] for event in events] == ["stopped", "starting", "migrating"]
    assert [event["to"] for event in events] == ["starting", "migrating", "ready"]
    assert all({"ts", "from", "to", "reason"} <= set(event) for event in events)


def test_restart_roundtrip_ready_reconnecting_ready() -> None:
    supervisor = BackendSupervisor()
    supervisor.start()
    supervisor.restart()
    assert supervisor.state is BackendSupervisorState.READY
    tail = supervisor.events()[-2:]
    assert tail[0]["from"] == "ready" and tail[0]["to"] == "reconnecting"
    assert tail[1]["from"] == "reconnecting" and tail[1]["to"] == "ready"


def test_restart_requires_running() -> None:
    supervisor = BackendSupervisor()
    with pytest.raises(ValueError, match="not running"):
        supervisor.restart()


def test_illegal_transition_fails_closed() -> None:
    supervisor = BackendSupervisor()
    supervisor.start()
    with pytest.raises(ValueError, match="cannot start from state ready"):
        supervisor.start()  # READY -> STARTING is not allowed
    # the state machine's own guard also rejects illegal transitions
    with pytest.raises(ValueError, match="illegal state transition"):
        supervisor._transition_locked(BackendSupervisorState.STARTING, "direct attempt")


def test_fail_then_recover_via_restart() -> None:
    supervisor = BackendSupervisor()
    supervisor.start()
    supervisor.fail("schema migration failed")
    assert supervisor.state is BackendSupervisorState.FAILED
    supervisor.restart()
    assert supervisor.state is BackendSupervisorState.READY


def test_fail_requires_running() -> None:
    supervisor = BackendSupervisor()
    with pytest.raises(ValueError, match="stopped"):
        supervisor.fail("boom")


def test_stop_halts_uptime_and_pid() -> None:
    supervisor = BackendSupervisor()
    supervisor.start()
    running = supervisor.status()
    assert running["state"] == "ready"
    assert running["pid"] is not None
    assert running["uptime"] >= 0.0
    supervisor.stop()
    stopped = supervisor.status()
    assert stopped["state"] == "stopped"
    assert stopped["uptime"] == 0.0
    assert stopped["pid"] is None
    # stop is idempotent
    assert supervisor.stop() is BackendSupervisorState.STOPPED


def test_log_ring_buffer_is_bounded() -> None:
    supervisor = BackendSupervisor()
    supervisor.start()  # 3 lifecycle log lines
    for index in range(250):
        supervisor._log(f"line {index}")
    logs = supervisor.logs(tail_n=1000)
    assert len(logs) == 200  # maxlen=200
    assert logs[0].endswith("line 50")  # oldest kept: 253 total - 200 capacity
    assert logs[-1].endswith("line 249")
    assert len(supervisor.logs(tail_n=5)) == 5


def test_concurrent_status_calls_are_thread_safe() -> None:
    supervisor = BackendSupervisor()
    supervisor.start()
    errors: list[Exception] = []
    ok_count = 0
    lock = threading.Lock()

    def worker() -> None:
        nonlocal ok_count
        try:
            for _ in range(50):
                status = supervisor.status()
                assert status["state"] == "ready"
                assert isinstance(status["logs_tail"], list)
            with lock:
                ok_count += 1
        except Exception as exc:  # pragma: no cover - failure path
            errors.append(exc)

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert not errors
    assert ok_count == 8
    assert supervisor.state is BackendSupervisorState.READY


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("ARCHEAXIS_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.delenv("ARCHEAXIS_RUNTIME_PROFILE", raising=False)
    from app.workspace.supervisor import BackendSupervisor

    import app.workspace.system as system_module

    monkeypatch.setattr(system_module, "supervisor", BackendSupervisor())
    from app.main import app

    return TestClient(app)


def test_status_endpoint_reports_stopped_supervisor(client: TestClient) -> None:
    response = client.get("/api/v1/system/status")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["state"] == "stopped"
    assert body["uptime"] == 0.0
    assert body["pid"] is None
    assert isinstance(body["logs_tail"], list)


def test_status_endpoint_rejects_out_of_range_tail_n(client: TestClient) -> None:
    response = client.get("/api/v1/system/status", params={"tail_n": 0})
    assert response.status_code == 422, response.text
    response = client.get("/api/v1/system/status", params={"tail_n": 201})
    assert response.status_code == 422, response.text


def test_restart_endpoint_409_when_not_running(client: TestClient) -> None:
    response = client.post("/api/v1/system/restart")
    assert response.status_code == 409, response.text
    assert "not running" in response.json()["detail"]


def test_restart_endpoint_202_when_running(client: TestClient) -> None:
    import app.workspace.system as system_module

    system_module.supervisor.start()
    response = client.post("/api/v1/system/restart")
    assert response.status_code == 202, response.text
    body = response.json()
    assert body["accepted"] is True
    assert body["state"] == "ready"
    assert [event["to"] for event in body["events"][-2:]] == ["reconnecting", "ready"]
    assert system_module.supervisor.state is BackendSupervisorState.READY
