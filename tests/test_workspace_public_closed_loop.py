from __future__ import annotations

from fastapi.testclient import TestClient


def test_workspace_public_closed_loop_is_source_bound_without_internal_ids(monkeypatch, tmp_path) -> None:
    import sqlite3

    from app.facades.research import research_github_repository
    from app.main import app
    from app.workspace import router
    from shared.config import config
    from tests.test_phase4_research_github import _transport
    from tests.test_phase5_mcs_closed_loop import _database

    database = _database(tmp_path)
    monkeypatch.setattr(router, "DB_PATH", database)
    monkeypatch.setitem(config._data["auth"], "enabled", False)
    monkeypatch.setitem(config._data["rate_limit"], "enabled", False)
    graph = research_github_repository(
        "https://github.com/octo/loop-os", fetcher=_transport(), db_path=database
    )
    source = graph.canonical_url
    client = TestClient(app)
    forbidden = {"package_id", "unit_id", "artifact_id", "command_id", "machine_candidate_id"}

    approved = client.post(
        "/workspace/api/research/approve",
        json={"command_id": "ui-research-1", "source": source},
    )
    assert approved.status_code == 200
    assert not forbidden.intersection(approved.json())

    knowledge = client.get("/workspace/api/knowledge")
    assert knowledge.status_code == 200
    assert knowledge.json()["items"][0]["source"] == source
    assert not forbidden.intersection(knowledge.text)

    started = client.post(
        "/workspace/api/knowledge/start-learning",
        json={"command_id": "ui-learning-1", "source": source},
    )
    assert started.status_code == 200
    assert started.json()["status"] == "started"
    assert not forbidden.intersection(started.json())

    learning = client.get("/workspace/api/learning")
    assert learning.status_code == 200
    assert learning.json()["items"][0]["source"] == source
    assert learning.json()["items"][0]["card_count"] > 0
    assert not forbidden.intersection(learning.text)

    for index in range(3):
        practice = client.post(
            "/workspace/api/learning/practice",
            json={"command_id": f"ui-practice-{index}", "source": source, "quality": 5},
        )
        assert practice.status_code == 200
        assert not forbidden.intersection(practice.json())

    evolution = client.get("/workspace/api/evolution")
    assert evolution.status_code == 200
    assert evolution.json()["mastery"]["mastered"] == 1
    assert evolution.json()["machine_knowledge"]["candidate"] == 1

    candidates = client.get("/workspace/api/runtime/candidates")
    assert candidates.status_code == 200
    candidate = candidates.json()["items"][0]
    assert candidate["lifecycle"] == "candidate"
    assert not forbidden.intersection(candidates.text)

    runtime_approval = client.post(
        "/workspace/api/runtime/approve",
        json={"command_id": "ui-runtime-1", "title": candidate["title"]},
    )
    assert runtime_approval.status_code == 200
    assert not forbidden.intersection(runtime_approval.json())

    runtime = client.get("/workspace/api/runtime/knowledge")
    assert runtime.status_code == 200
    assert runtime.json()["items"][0]["lifecycle"] == "approved"
    assert not forbidden.intersection(runtime.text)

    assert client.post(
        "/workspace/api/knowledge/start-learning",
        json={"command_id": "ui-learning-invalid", "source": "https://invalid.test/no-case"},
    ).status_code == 422
    with sqlite3.connect(database) as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM machine_knowledge_candidates_v1 WHERE lifecycle_status='approved'"
        ).fetchone()[0] == 1
