from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("ARCHEAXIS_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("ARCHEAXIS_RUNTIME_PROFILE", "green-stable")
    monkeypatch.setenv("ARCHEAXIS_DESKTOP_LAUNCH_TOKEN", "test-launch-token")
    monkeypatch.delenv("COGNITIVE_DATA_DIR", raising=False)
    from app.main import app

    return TestClient(app)


def _headers(*scopes: str) -> dict[str, str]:
    return {
        "x-archeaxis-launch-token": "test-launch-token",
        "x-archeaxis-actor": "reviewer-1",
        "x-archeaxis-scopes": " ".join(scopes),
    }


def test_federation_writes_require_token_actor_and_scope(client: TestClient) -> None:
    payload = {
        "idempotency_key": "submission-1",
        "submitter": "reviewer-1",
        "items": [{"item_key": "a", "claim": "claim", "source_ref": "raw:sha256:a"}],
    }
    assert client.post("/api/v1/federation/candidates", json=payload).status_code == 403
    assert client.post(
        "/api/v1/federation/candidates", json=payload, headers=_headers("evidence.review")
    ).status_code == 403
    accepted = client.post(
        "/api/v1/federation/candidates", json=payload, headers=_headers("federation.write")
    )
    assert accepted.status_code == 200, accepted.text

    candidate = client.get("/api/v1/federation/knowledge", params={"kind": "candidate"}).json()["items"][0]
    decision = {
        "decision": "verified",
        "reviewer_id": "reviewer-1",
        "rationale": "human checked anchor",
        "expected_version": 1,
        "idempotency_key": "review-1",
    }
    assert client.post(
        f"/api/v1/federation/candidates/{candidate['id']}/review",
        json=decision,
        headers=_headers("federation.write"),
    ).status_code == 403
    reviewed = client.post(
        f"/api/v1/federation/candidates/{candidate['id']}/review",
        json=decision,
        headers=_headers("evidence.review"),
    )
    assert reviewed.status_code == 200, reviewed.text
