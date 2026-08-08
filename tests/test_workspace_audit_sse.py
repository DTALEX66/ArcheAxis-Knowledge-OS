from __future__ import annotations

from fastapi.testclient import TestClient


def test_workspace_audit_sse_emits_durable_projection_snapshot(monkeypatch) -> None:
    import app.workspace.router as router
    from app.main import app

    monkeypatch.setattr(
        router.service,
        "workspace_delivery",
        lambda *, db_path: {
            "schema_version": "v1",
            "dispatcher": "lease_fenced",
            "summary": {"jobs": 1, "outbox": {"pending": 1}, "receipts": {"missing": 1}},
            "items": [{"activity": "local intake", "job_state": "queued", "outbox_state": "pending", "receipt_state": "missing", "job_attempts": 0, "outbox_attempts": 0}],
        },
    )
    response = TestClient(app).get("/workspace/api/audit/stream?once=true")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert response.headers["cache-control"] == "no-store"
    assert "id: " in response.text
    assert "event: audit\n" in response.text
    assert '"schema_version":"v1"' in response.text
    assert '"activity":"local intake"' in response.text


def test_workspace_audit_sse_resumes_with_heartbeat_for_same_projection(monkeypatch) -> None:
    import app.workspace.router as router
    from app.main import app

    monkeypatch.setattr(
        router.service,
        "workspace_delivery",
        lambda *, db_path: {"schema_version": "v1", "summary": {}, "items": []},
    )
    first = TestClient(app).get("/workspace/api/audit/stream?once=true")
    event_id = next(line.removeprefix("id: ") for line in first.text.splitlines() if line.startswith("id: "))
    resumed = TestClient(app).get(
        "/workspace/api/audit/stream?once=true",
        headers={"Last-Event-ID": event_id},
    )
    assert resumed.status_code == 200
    assert resumed.text == ": heartbeat\n\n"
