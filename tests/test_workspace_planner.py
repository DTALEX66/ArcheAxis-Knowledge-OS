from __future__ import annotations

from fastapi.testclient import TestClient


def test_planner_preview_is_bounded_and_never_executes() -> None:
    from app.main import app

    client = TestClient(app)
    supported = client.post("/workspace/api/planner/preview", json={"goal": "read file: AGENTS.md"})
    assert supported.status_code == 200
    payload = supported.json()
    assert payload["schema_version"] == "v1"
    assert payload["status"] == "supported"
    assert payload["execution"] == "preview_only"
    assert payload["steps"] == [
        {
            "id": 1,
            "name": "read_file",
            "type": "tool",
            "tool": "file_read",
            "path": "AGENTS.md",
            "dry_run": False,
        }
    ]

    unsupported = client.post(
        "/workspace/api/planner/preview", json={"goal": "run shell: delete everything"}
    )
    assert unsupported.status_code == 200
    assert unsupported.json() == {
        "schema_version": "v1",
        "status": "unsupported",
        "execution": "preview_only",
        "steps": [],
    }
