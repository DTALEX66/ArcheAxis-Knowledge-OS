from __future__ import annotations

import io
import time

import pytest
from fastapi.testclient import TestClient


def test_desktop_readiness_is_hidden_without_launch_token(monkeypatch) -> None:
    from app.main import app

    monkeypatch.delenv("COGNITIVE_DESKTOP_LAUNCH_TOKEN", raising=False)
    response = TestClient(app).get("/workspace/api/_desktop/ready")

    assert response.status_code == 404


def test_desktop_readiness_requires_exact_launch_token(monkeypatch) -> None:
    from app.main import app

    monkeypatch.setenv("COGNITIVE_DESKTOP_LAUNCH_TOKEN", "test-launch-token-1234567890")
    client = TestClient(app)

    rejected = client.get(
        "/workspace/api/_desktop/ready",
        headers={"X-ArcheAxis-Launch-Token": "wrong-token"},
    )
    accepted = client.get(
        "/workspace/api/_desktop/ready",
        headers={"X-ArcheAxis-Launch-Token": "test-launch-token-1234567890"},
    )

    assert rejected.status_code == 403
    assert accepted.status_code == 200
    assert accepted.json() == {
        "schema_version": "v1",
        "product": "ArcheAxis Learning Workspace",
        "workspace": "Human–AI Learning Workspace",
    }
    assert "token" not in accepted.text.casefold()


def test_desktop_core_rejects_non_loopback_host(monkeypatch) -> None:
    from app import runtime_entrypoint

    monkeypatch.setenv("COGNITIVE_DESKTOP_CONTROL", "stdio-v1")
    monkeypatch.setenv("COGNITIVE_DESKTOP_LAUNCH_TOKEN", "test-launch-token-1234567890")
    monkeypatch.setenv("COGNITIVE_HOST", "0.0.0.0")

    with pytest.raises(RuntimeError, match="127.0.0.1"):
        runtime_entrypoint.run_core(object())


def test_desktop_core_uses_same_process_and_honors_stdin_shutdown(monkeypatch) -> None:
    import uvicorn

    from app import runtime_entrypoint

    captured: dict[str, object] = {}

    class FakeServer:
        def __init__(self, config) -> None:
            captured["config"] = config
            self.should_exit = False

        def run(self) -> None:
            deadline = time.monotonic() + 2
            while not self.should_exit and time.monotonic() < deadline:
                time.sleep(0.01)
            captured["exited"] = self.should_exit

    def fake_config(app_path: str, **kwargs):
        captured["app_path"] = app_path
        captured["kwargs"] = kwargs
        return object()

    monkeypatch.setenv("COGNITIVE_DESKTOP_CONTROL", "stdio-v1")
    monkeypatch.setenv("COGNITIVE_DESKTOP_LAUNCH_TOKEN", "test-launch-token-1234567890")
    monkeypatch.setenv("COGNITIVE_HOST", "127.0.0.1")
    monkeypatch.setenv("COGNITIVE_PORT", "8127")
    monkeypatch.setattr(runtime_entrypoint.sys, "stdin", io.StringIO("shutdown\n"))
    monkeypatch.setattr(uvicorn, "Config", fake_config)
    monkeypatch.setattr(uvicorn, "Server", FakeServer)

    with pytest.raises(SystemExit) as exit_info:
        runtime_entrypoint.run_core(object())

    assert exit_info.value.code == 0
    assert captured["app_path"] == "app.main:app"
    assert captured["kwargs"] == {
        "host": "127.0.0.1",
        "port": 8127,
        "workers": 1,
        "proxy_headers": False,
    }
    assert captured["exited"] is True
