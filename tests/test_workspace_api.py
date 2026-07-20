from __future__ import annotations

from fastapi.testclient import TestClient


def test_local_workspace_page_and_safe_diagnostics_are_available() -> None:
    from app.main import app

    client = TestClient(app)

    page = client.get("/workspace")
    assert page.status_code == 200
    assert "元枢系统" in page.text
    assert "ArcheAxis OS" in page.text
    assert "元枢·观心" in page.text
    assert "Cognitive-Loop-OS" not in page.text
    assert "API key" not in page.text
    assert 'id="intake-url-form"' in page.text
    assert 'id="intake-file-form"' in page.text
    assert "command_id" not in page.text

    stylesheet = client.get("/workspace/assets/styles.css")
    assert stylesheet.status_code == 200
    assert "--accent:#C8A972" in stylesheet.text
    application = client.get("/workspace/assets/app.js")
    assert application.status_code == 200
    assert "Command Palette" not in application.text

    diagnostics = client.get("/workspace/api/diagnostics")
    assert diagnostics.status_code == 200
    payload = diagnostics.json()
    assert payload["schema_version"] == "v1"
    assert "database_path" not in diagnostics.text
    assert "backup_path" not in diagnostics.text


def test_workspace_mutations_use_local_principal_without_api_credentials() -> None:
    from app.main import app

    response = TestClient(app).post("/workspace/api/commands/promote-research", json={})

    assert response.status_code == 422


def test_workspace_intake_accepts_web_sources_and_uploaded_text(monkeypatch, tmp_path) -> None:
    from app.main import app
    from app.workspace import router
    from tests.test_phase5_mcs_closed_loop import _database

    database = _database(tmp_path)
    monkeypatch.setattr(router, "DB_PATH", database)
    monkeypatch.setattr(
        router.service,
        "intake_url",
        lambda *, url, db_path: {
            "source_type": "web",
            "source": url,
            "content": "# extracted",
            "engine": "test",
        },
    )
    client = TestClient(app)

    webpage = client.post("/workspace/api/intake/url", json={"url": "https://example.com/article"})
    assert webpage.status_code == 200
    assert webpage.json()["source_type"] == "web"

    uploaded = client.post(
        "/workspace/api/intake/upload",
        files={"file": ("notes.txt", b"local intake content", "text/plain")},
    )
    assert uploaded.status_code == 200
    assert uploaded.json()["source_type"] == "file"
    assert uploaded.json()["file_name"] == "notes.txt"
    assert "local intake content" in uploaded.json()["content"]
    assert uploaded.json()["status"] == "candidate"
    assert uploaded.json()["requires_human_review"] is True

    from app.facades.research import get_research_package

    package = get_research_package(uploaded.json()["package_id"], db_path=database)
    assert package.package.status == "candidate"
    assert package.sources[0].content == "local intake content"


def test_workspace_github_intake_persists_a_candidate_research_package(tmp_path) -> None:
    from app.facades.research import get_research_package
    from app.workspace import service
    from tests.test_phase4_research_github import _transport
    from tests.test_phase5_mcs_closed_loop import _database

    database = _database(tmp_path)

    result = service.intake_url(
        url="https://github.com/octo/loop-os",
        db_path=database,
        fetcher=_transport(),
    )

    assert result["source_type"] == "github_repository"
    assert result["status"] == "candidate"
    assert result["requires_human_review"] is True
    package = get_research_package(result["package_id"], db_path=database)
    assert package.package.package_id == result["package_id"]
    assert package.package.status == "candidate"


def test_workspace_http_flow_promotes_persisted_research_and_derives_mastery(
    monkeypatch, tmp_path,
) -> None:
    from app.facades.research import research_github_repository
    from app.main import app
    from app.workspace import router
    from shared.config import config
    from tests.test_phase4_research_github import _transport
    from tests.test_phase5_mcs_closed_loop import _database

    database = _database(tmp_path)
    monkeypatch.setattr(router, "DB_PATH", database)
    graph = research_github_repository(
        "https://github.com/octo/loop-os", fetcher=_transport(), db_path=database
    )
    monkeypatch.setitem(config._data["auth"], "enabled", False)
    client = TestClient(app)

    promoted = client.post(
        "/workspace/api/commands/promote-research",
        json={"command_id": "promote-1", "package_id": graph.package.package_id, "rationale": "grounded"},
    )
    assert promoted.status_code == 200
    conflicting_promotion = client.post(
        "/workspace/api/commands/promote-research",
        json={
            "command_id": "promote-1",
            "package_id": graph.package.package_id,
            "rationale": "changed rationale",
        },
    )
    assert conflicting_promotion.status_code == 409

    claim_id = next(item for item in promoted.json()["unit_ids"] if "claim" in item)
    learning = client.post(
        "/workspace/api/commands/start-learning",
        json={"command_id": "learning-1", "unit_id": claim_id, "rationale": "practice"},
    )
    assert learning.status_code == 200
    assert learning.json()["status"] == "approved"
    assert learning.json()["card_ids"]
    artifact_id = learning.json()["artifact_id"]
    conflicting_learning = client.post(
        "/workspace/api/commands/start-learning",
        json={"command_id": "learning-1", "unit_id": claim_id, "rationale": "changed rationale"},
    )
    assert conflicting_learning.status_code == 409

    for index in range(3):
        practice = client.post(
            "/workspace/api/commands/record-practice",
            json={"command_id": f"practice-{index}", "artifact_id": artifact_id, "quality": 5},
        )
    assert practice.status_code == 200
    assert practice.json()["mastered"] is True
    assert practice.json()["machine_candidate_id"]
    conflicting_practice = client.post(
        "/workspace/api/commands/record-practice",
        json={"command_id": "practice-0", "artifact_id": artifact_id, "quality": 0},
    )
    assert conflicting_practice.status_code == 409
    case = client.get(f"/workspace/api/cases/{artifact_id}")
    assert case.status_code == 200
    assert any(event["event_type"] == "machine_knowledge_candidate_created" for event in case.json()["events"])
