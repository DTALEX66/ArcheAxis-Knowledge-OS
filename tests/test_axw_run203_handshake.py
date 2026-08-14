"""AXW-RUN-203 — Backend Handshake endpoint tests.

Proves GET /api/v1/system/handshake returns honest product identity,
a pyproject-backed backend_version, a git-backed source_commit, and a
runtime_mode driven by ARCHEAXIS_RUNTIME_PROFILE.
"""

from __future__ import annotations

import re
import subprocess
import tomllib
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

_PROJECT_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    # Isolate the runtime data dir; keep the supervisor fresh per test so
    # migration_state assertions are deterministic.
    monkeypatch.setenv("ARCHEAXIS_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.delenv("ARCHEAXIS_RUNTIME_PROFILE", raising=False)
    import app.workspace.system as system_module
    from app.workspace.supervisor import BackendSupervisor

    monkeypatch.setattr(system_module, "supervisor", BackendSupervisor())
    from app.main import app

    return TestClient(app)


def test_handshake_returns_product_identity(client: TestClient) -> None:
    response = client.get("/api/v1/system/handshake")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["product_id"] == "archeaxis-workspace"
    assert body["product_name"] == "ArcheAxis Knowledge"
    assert re.match(r"^1\.", body["api_contract"])


def test_handshake_backend_version_matches_pyproject(client: TestClient) -> None:
    with open(_PROJECT_ROOT / "pyproject.toml", "rb") as f:
        expected = tomllib.load(f)["project"]["version"]
    body = client.get("/api/v1/system/handshake").json()
    assert body["backend_version"] == expected


def test_handshake_source_commit_matches_git_head(client: TestClient) -> None:
    result = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        cwd=str(_PROJECT_ROOT),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    body = client.get("/api/v1/system/handshake").json()
    assert body["source_commit"] == result.stdout.strip()
    assert re.match(r"^[0-9a-f]{7,}$", body["source_commit"])


def test_handshake_runtime_facts(client: TestClient) -> None:
    body = client.get("/api/v1/system/handshake").json()
    assert isinstance(body["schema_version"], int) and body["schema_version"] >= 1
    assert isinstance(body["workspace_id"], str) and len(body["workspace_id"]) == 16
    assert body["capabilities"] == []
    assert body["migration_state"] in {"ready", "migrating", "failed"}


def test_handshake_runtime_mode_defaults_to_installed_stable(client: TestClient) -> None:
    body = client.get("/api/v1/system/handshake").json()
    assert body["runtime_mode"] == "installed-stable"


def test_handshake_runtime_mode_env_driven(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ARCHEAXIS_RUNTIME_PROFILE", "external-dev")
    body = client.get("/api/v1/system/handshake").json()
    assert body["runtime_mode"] == "external-dev"


def test_handshake_migration_state_reflects_failed_supervisor(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    import app.workspace.system as system_module

    system_module.supervisor.start()
    system_module.supervisor.fail("schema migration failed")
    body = client.get("/api/v1/system/handshake").json()
    assert body["migration_state"] == "failed"
