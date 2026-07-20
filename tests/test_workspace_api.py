from __future__ import annotations

from fastapi.testclient import TestClient


def test_workspace_page_and_safe_diagnostics_are_available() -> None:
    from app.main import app

    client = TestClient(app)

    page = client.get("/workspace")
    assert page.status_code == 200
    assert "Cognitive Workspace" in page.text

    diagnostics = client.get("/workspace/api/diagnostics")
    assert diagnostics.status_code == 200
    payload = diagnostics.json()
    assert payload["schema_version"] == "v1"
    assert "database_path" not in diagnostics.text
    assert "backup_path" not in diagnostics.text


def test_workspace_mutations_fail_closed_without_server_owned_identity() -> None:
    from app.main import app

    response = TestClient(app).post(
        "/workspace/api/commands/promote-research",
        json={
            "command_id": "cmd-1",
            "package_id": "package-1",
            "rationale": "not trusted",
        },
    )

    assert response.status_code == 401


def test_workspace_http_flow_promotes_persisted_research_and_derives_mastery(
    monkeypatch, tmp_path,
) -> None:

    from app.facades.research import research_github_repository
    from app.main import app
    from app.workspace import router
    from shared.auth import create_token
    from shared.config import config
    from tests.test_phase4_research_github import _transport
    from tests.test_phase5_mcs_closed_loop import _database

    database = _database(tmp_path)
    monkeypatch.setattr(router, "DB_PATH", database)
    graph = research_github_repository(
        "https://github.com/octo/loop-os", fetcher=_transport(), db_path=database
    )
    monkeypatch.setitem(config._data["auth"], "enabled", True)
    headers = {"Authorization": f"Bearer {create_token('reviewer-1')}"}
    client = TestClient(app)

    promoted = client.post(
        "/workspace/api/commands/promote-research",
        headers=headers,
        json={"command_id": "promote-1", "package_id": graph.package.package_id, "rationale": "grounded"},
    )
    assert promoted.status_code == 200
    claim_id = next(item for item in promoted.json()["unit_ids"] if "claim" in item)
    learning = client.post(
        "/workspace/api/commands/start-learning", headers=headers,
        json={"command_id": "learning-1", "unit_id": claim_id, "rationale": "practice"},
    )
    assert learning.status_code == 200
    artifact_id = learning.json()["artifact_id"]
    approved = client.post(
        "/workspace/api/commands/approve-learning", headers=headers,
        json={"command_id": "approve-1", "artifact_id": artifact_id},
    )
    assert approved.status_code == 200
    for index in range(3):
        practice = client.post(
            "/workspace/api/commands/record-practice", headers=headers,
            json={"command_id": f"practice-{index}", "artifact_id": artifact_id, "quality": 5},
        )
    assert practice.status_code == 200
    assert practice.json()["mastered"] is True
    assert practice.json()["machine_candidate_id"]
    case = client.get(f"/workspace/api/cases/{artifact_id}", headers=headers)
    assert case.status_code == 200
    assert any(event["event_type"] == "machine_knowledge_candidate_created" for event in case.json()["events"])
