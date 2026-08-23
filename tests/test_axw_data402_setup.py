"""AXW-DATA-402 — First-run setup wizard (backend) tests.

Proves GET /api/v1/setup/status reports per-step readiness
(id/state/message/action_hint) and POST /api/v1/setup/initialize creates
the workspace idempotently, across four scenarios: fresh environment,
existing workspace, legacy database present, and an unwritable data path
(fail-closed, no crash).
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.setup.setup_status import legacy_db_path, workspace_root, workspaces_base
from shared.workspace_manifest import create_workspace, load


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    # Isolate the runtime data dir under a green-stable deployment so
    # path_policy resolves it deterministically from the environment.
    monkeypatch.setenv("ARCHEAXIS_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("ARCHEAXIS_RUNTIME_PROFILE", "green-stable")
    monkeypatch.delenv("ARCHEAXIS_CAPABILITY_ROOT", raising=False)
    monkeypatch.delenv("COGNITIVE_DATA_DIR", raising=False)
    import app.main  # noqa: F401 — import after env isolation (DB_PATH parity)
    from app.main import app

    return TestClient(app)


def _status(client: TestClient) -> dict:
    response = client.get("/api/v1/setup/status")
    assert response.status_code == 200, response.text
    return response.json()


def _step(steps: list[dict], step_id: str) -> dict:
    matches = [step for step in steps if step["id"] == step_id]
    assert matches, f"step {step_id!r} missing from {[s['id'] for s in steps]}"
    return matches[0]


def _assert_step_shape(step: dict) -> None:
    assert step["id"]
    assert step["state"] in {"pending", "ready", "blocked", "completed"}
    assert isinstance(step["message"], str)
    assert isinstance(step["action_hint"], str)


def test_fresh_environment_initialize_then_completed(client: TestClient) -> None:
    status = _status(client)
    assert status["ready"] is False
    assert status["legacy_db_present"] is False
    for step in status["steps"]:
        _assert_step_shape(step)
    assert _step(status["steps"], "workspace_exists")["state"] == "pending"
    assert _step(status["steps"], "manifest_valid")["state"] == "pending"
    assert _step(status["steps"], "paths_writable")["state"] == "ready"

    response = client.post("/api/v1/setup/initialize")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["initialized"] is True
    assert body["already_existed"] is False
    assert body["workspace_id"].startswith("ws-")

    after = _status(client)
    assert after["ready"] is True
    assert _step(after["steps"], "workspace_exists")["state"] == "completed"
    assert _step(after["steps"], "manifest_valid")["state"] == "completed"
    assert after["workspace_id"] == body["workspace_id"]
    assert workspace_root().is_dir()
    assert load(workspace_root() / "manifest.json").workspace_id == body["workspace_id"]


def test_existing_workspace_initialize_is_idempotent(
    client: TestClient, tmp_path: Path
) -> None:
    first = create_workspace(workspaces_base(), "workspace")
    assert first.workspace_id.startswith("ws-")

    status = _status(client)
    assert _step(status["steps"], "workspace_exists")["state"] == "completed"
    assert _step(status["steps"], "manifest_valid")["state"] == "completed"

    response = client.post("/api/v1/setup/initialize")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["initialized"] is True
    assert body["already_existed"] is True
    assert body["workspace_id"] == first.workspace_id

    # Idempotent: a second call returns the exact same现状.
    again = client.post("/api/v1/setup/initialize").json()
    assert again["workspace_id"] == first.workspace_id
    assert again["already_existed"] is True


def test_legacy_database_surfaces_migration_step(client: TestClient) -> None:
    database = legacy_db_path()
    database.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE legacy_notes (id TEXT PRIMARY KEY, body TEXT)")
        connection.execute("INSERT INTO legacy_notes VALUES ('n1', 'keep me')")

    status = _status(client)
    assert status["legacy_db_present"] is True
    assert status["ready"] is False
    step = _step(status["steps"], "legacy_db_migration")
    _assert_step_shape(step)
    assert step["state"] in {"blocked", "pending"}
    assert "legacy" in step["message"].casefold()
    assert step["action_hint"], "migration step must carry an action_hint"

    # The wizard cannot be ready while a legacy database awaits migration.
    assert _step(status["steps"], "workspace_exists")["state"] != "completed"


def test_unwritable_data_path_is_fail_closed(client: TestClient, tmp_path: Path) -> None:
    # A file squatting on the workspaces directory makes mkdir/write
    # probes fail — the status endpoint must report blocked, not crash.
    data_root = tmp_path / "data"
    data_root.mkdir(parents=True, exist_ok=True)
    (data_root / "workspaces").write_text("not a directory", encoding="utf-8")

    status = _status(client)
    step = _step(status["steps"], "paths_writable")
    _assert_step_shape(step)
    assert step["state"] == "blocked"
    assert step["message"]
    assert step["action_hint"]

    # Fail-closed: every other step still reports a valid state and the
    # workspace is not reported as ready.
    for other in status["steps"]:
        _assert_step_shape(other)
    assert status["ready"] is False
    assert _step(status["steps"], "workspace_exists")["state"] in {"pending", "blocked"}


def test_quick_mode_places_all_four_libraries_under_user_root(
    client: TestClient, tmp_path: Path
) -> None:
    root = tmp_path / "my-archeaxis-data"
    response = client.post("/api/v1/setup/initialize", json={"mode": "quick", "root": str(root)})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["mode"] == "quick"
    assert set(body["domains"]) == {
        "source_archive", "evidence_ledger", "human_learning_vault", "ai_asset_vault"
    }
    for domain, location in body["domains"].items():
        assert Path(location) == root / domain
        assert Path(location).is_dir()
        assert body["library_health"][domain]["free_bytes"] > 0


def test_preflight_reports_quick_mode_health_without_creating_directories(
    client: TestClient, tmp_path: Path
) -> None:
    root = tmp_path / "preflight-only"

    response = client.post(
        "/api/v1/setup/preflight", json={"mode": "quick", "root": str(root)}
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["ready"] is True
    assert body["mode"] == "quick"
    assert set(body["domains"]) == {
        "source_archive", "evidence_ledger", "human_learning_vault", "ai_asset_vault"
    }
    assert all(item["free_bytes"] > 0 for item in body["library_health"].values())
    assert not root.exists(), "preflight must not create the selected library root"


def test_advanced_mode_requires_four_distinct_non_nested_library_paths(
    client: TestClient, tmp_path: Path
) -> None:
    paths = {
        "source_archive": str(tmp_path / "source"),
        "evidence_ledger": str(tmp_path / "evidence"),
        "human_learning_vault": str(tmp_path / "learning"),
        "ai_asset_vault": str(tmp_path / "assets"),
    }
    response = client.post("/api/v1/setup/initialize", json={"mode": "advanced", "domains": paths})
    assert response.status_code == 200, response.text
    assert response.json()["mode"] == "advanced"

    nested = dict(paths)
    nested["ai_asset_vault"] = str(tmp_path / "source" / "assets")
    rejected = client.post("/api/v1/setup/initialize", json={"mode": "advanced", "domains": nested})
    assert rejected.status_code == 422
    assert rejected.json()["detail"]["code"] == "nested_path"
