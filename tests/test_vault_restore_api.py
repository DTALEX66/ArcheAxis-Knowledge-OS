from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient


def _write(root: Path, rel: str, content: str) -> dict:
    from app.main import app

    client = TestClient(app)
    response = client.post(
        "/workspace/api/vault/write",
        json={"root": str(root), "relative_path": rel, "content": content},
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_frontmatter_preserved_roundtrip(tmp_path: Path, monkeypatch) -> None:
    """C4 round-trip: read → edit body → write keeps YAML frontmatter."""
    import hashlib

    import app.workspace.router as router
    from app.main import app

    root = tmp_path / "vault"
    root.mkdir()
    note = root / "notes.md"
    note.write_text(
        "---\ntitle: My Note\ntags: [one, two]\n---\noriginal body\n",
        encoding="utf-8",
        newline="\n",
    )
    store = tmp_path / "workspace.sqlite"
    monkeypatch.setattr(router, "DB_PATH", store)
    client = TestClient(app)

    opened = client.post(
        "/workspace/api/vault/file",
        json={"root": str(root), "relative_path": "notes.md"},
    ).json()
    raw = opened["raw_text"]
    assert "title: My Note" in raw
    current_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()

    edited = raw.replace("original body", "edited body")
    saved = client.post(
        "/workspace/api/vault/write",
        json={
            "root": str(root),
            "relative_path": "notes.md",
            "content": edited,
            "expected_hash": current_hash,
        },
    )
    assert saved.status_code == 200
    assert note.read_text(encoding="utf-8") == edited
    assert "title: My Note" in note.read_text(encoding="utf-8")


def test_list_backups_newest_first(tmp_path: Path, monkeypatch) -> None:
    import app.workspace.router as router
    from app.main import app

    root = tmp_path / "vault"
    root.mkdir()
    note = root / "notes.md"
    note.write_text("v0\n", encoding="utf-8", newline="\n")
    store = tmp_path / "workspace.sqlite"
    monkeypatch.setattr(router, "DB_PATH", store)

    _write(root, "notes.md", "v1\n")
    _write(root, "notes.md", "v2\n")

    client = TestClient(app)
    payload = client.post(
        "/workspace/api/vault/backups",
        json={"root": str(root), "relative_path": "notes.md"},
    ).json()
    assert payload["schema_version"] == "v1"
    names = [b["backup_name"] for b in payload["backups"]]
    assert len(names) == 2
    assert all(n.startswith("notes.md-") and n.endswith(".bak") for n in names)


def test_restore_backup_roundtrip(tmp_path: Path, monkeypatch) -> None:
    import app.workspace.router as router
    from app.main import app

    root = tmp_path / "vault"
    root.mkdir()
    note = root / "notes.md"
    note.write_text("original\n", encoding="utf-8", newline="\n")
    store = tmp_path / "workspace.sqlite"
    monkeypatch.setattr(router, "DB_PATH", store)

    _write(root, "notes.md", "overwritten\n")
    assert note.read_text(encoding="utf-8") == "overwritten\n"

    client = TestClient(app)
    backups = client.post(
        "/workspace/api/vault/backups",
        json={"root": str(root), "relative_path": "notes.md"},
    ).json()["backups"]
    assert backups, "expected at least one backup"
    backup_name = backups[-1]["backup_name"]  # oldest = the pre-overwrite snapshot

    restored = client.post(
        "/workspace/api/vault/restore",
        json={
            "root": str(root),
            "relative_path": "notes.md",
            "backup_name": backup_name,
        },
    )
    assert restored.status_code == 200, restored.text
    payload = restored.json()
    assert payload["restored_from"] == backup_name
    assert note.read_text(encoding="utf-8") == "original\n"
    assert payload["pre_restore_backup"] != ""


def test_restore_rejects_traversal_backup_name(tmp_path: Path, monkeypatch) -> None:
    import app.workspace.router as router
    from app.main import app

    root = tmp_path / "vault"
    root.mkdir()
    (root / "notes.md").write_text("x\n", encoding="utf-8", newline="\n")
    store = tmp_path / "workspace.sqlite"
    monkeypatch.setattr(router, "DB_PATH", store)
    client = TestClient(app)

    response = client.post(
        "/workspace/api/vault/restore",
        json={
            "root": str(root),
            "relative_path": "notes.md",
            "backup_name": "../evil.bak",
        },
    )
    assert response.status_code == 422

    foreign = client.post(
        "/workspace/api/vault/restore",
        json={
            "root": str(root),
            "relative_path": "notes.md",
            "backup_name": "other.md-123.bak",
        },
    )
    assert foreign.status_code == 422
