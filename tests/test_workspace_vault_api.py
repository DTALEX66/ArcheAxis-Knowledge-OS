from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient


def test_vault_workbench_inspect_read_search_are_read_only(tmp_path: Path, monkeypatch) -> None:
    import app.workspace.router as router
    from app.main import app

    root = tmp_path / "vault"
    root.mkdir()
    (root / "notes.md").write_text(
        "---\ntitle: Local note\ntags: [one, two]\n---\nfindable text\n",
        encoding="utf-8",
    )
    (root / "image.png").write_bytes(bytes([0, 255, 1]))
    store = tmp_path / "workspace.sqlite"
    monkeypatch.setattr(router, "DB_PATH", store)
    client = TestClient(app)

    inspected = client.post("/workspace/api/vault/inspect", json={"root": str(root)})
    assert inspected.status_code == 200
    payload = inspected.json()
    assert payload["schema_version"] == "v1"
    assert payload["root_name"] == "vault"
    assert {entry["relative_path"] for entry in payload["files"]} == {"image.png", "notes.md"}
    image = next(entry for entry in payload["files"] if entry["relative_path"] == "image.png")
    assert image["kind"] == "attachment"
    assert image["mime_type"] == "image/png"
    assert str(root) not in inspected.text

    opened = client.post(
        "/workspace/api/vault/file",
        json={"root": str(root), "relative_path": "notes.md"},
    )
    assert opened.status_code == 200
    assert opened.json()["raw_text"].endswith("findable text\n")

    search = client.post(
        "/workspace/api/vault/search",
        json={"root": str(root), "query": "findable"},
    )
    assert search.status_code == 200
    assert search.json()["results"][0]["relative_path"] == "notes.md"

    escaped = client.post(
        "/workspace/api/vault/file",
        json={"root": str(root), "relative_path": "../outside.md"},
    )
    assert escaped.status_code == 422

    binary = client.post(
        "/workspace/api/vault/file",
        json={"root": str(root), "relative_path": "image.png"},
    )
    assert binary.status_code == 422
