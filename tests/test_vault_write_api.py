from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient


def _write_vault(root: Path, store: Path, relative_path: str, content: str) -> dict:
    from app.main import app

    client = TestClient(app)
    response = client.post(
        "/workspace/api/vault/write",
        json={
            "root": str(root),
            "relative_path": relative_path,
            "content": content,
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_vault_write_updates_file_and_backs_up(tmp_path: Path, monkeypatch) -> None:
    import app.workspace.router as router

    root = tmp_path / "vault"
    root.mkdir()
    note = root / "notes.md"
    note.write_text("original text\n", encoding="utf-8", newline="\n")
    store = tmp_path / "workspace.sqlite"
    monkeypatch.setattr(router, "DB_PATH", store)

    payload = _write_vault(root, store, "notes.md", "updated text\n")
    assert payload["schema_version"] == "v1"
    assert payload["relative_path"] == "notes.md"
    assert payload["expected_hash_checked"] is False
    assert note.read_text(encoding="utf-8") == "updated text\n"
    assert "vault-backups" in payload["backup_path"]
    backup = Path(payload["backup_path"])
    assert backup.is_file()
    assert backup.read_bytes() == b"original text\n"


def test_vault_write_with_expected_hash_conflicts_on_change(
    tmp_path: Path, monkeypatch
) -> None:
    import hashlib

    import app.workspace.router as router
    from app.main import app

    root = tmp_path / "vault"
    root.mkdir()
    note = root / "notes.md"
    note.write_text("base\n", encoding="utf-8", newline="\n")
    store = tmp_path / "workspace.sqlite"
    monkeypatch.setattr(router, "DB_PATH", store)

    stale_hash = hashlib.sha256(b"stale\n").hexdigest()  # does not match on-disk
    client = TestClient(app)
    response = client.post(
        "/workspace/api/vault/write",
        json={
            "root": str(root),
            "relative_path": "notes.md",
            "content": "clobber\n",
            "expected_hash": stale_hash,
        },
    )
    assert response.status_code == 409
    detail = response.json()["detail"]
    assert "expected-hash mismatch" in detail["message"]
    assert detail["current_hash"] == hashlib.sha256(b"base\r\n" if b"\r\n" in note.read_bytes() else b"base\n").hexdigest()
    # Fail-closed: the file was NOT modified.
    assert note.read_text(encoding="utf-8") == "base\n"


def test_vault_write_roundtrip_with_expected_hash(tmp_path: Path, monkeypatch) -> None:
    import hashlib

    import app.workspace.router as router

    root = tmp_path / "vault"
    root.mkdir()
    note = root / "notes.md"
    note.write_text("read me\n", encoding="utf-8", newline="\n")
    store = tmp_path / "workspace.sqlite"
    monkeypatch.setattr(router, "DB_PATH", store)

    current_hash = hashlib.sha256(b"read me\n").hexdigest()
    payload = _write_vault(root, store, "notes.md", "round trip\n")
    assert payload["source_hash"] != current_hash
    assert note.read_text(encoding="utf-8") == "round trip\n"


def test_vault_write_rejects_escape_and_binary(tmp_path: Path, monkeypatch) -> None:
    import app.workspace.router as router
    from app.main import app

    root = tmp_path / "vault"
    root.mkdir()
    (root / "image.png").write_bytes(b"PK\x03\x04binary-like")
    store = tmp_path / "workspace.sqlite"
    monkeypatch.setattr(router, "DB_PATH", store)
    client = TestClient(app)

    escaped = client.post(
        "/workspace/api/vault/write",
        json={
            "root": str(root),
            "relative_path": "../outside.md",
            "content": "x\n",
        },
    )
    assert escaped.status_code == 422

    binary = client.post(
        "/workspace/api/vault/write",
        json={
            "root": str(root),
            "relative_path": "image.png",
            "content": "x\n",
        },
    )
    assert binary.status_code == 422


def test_vault_write_missing_file_is_rejected(tmp_path: Path, monkeypatch) -> None:
    import app.workspace.router as router
    from app.main import app

    root = tmp_path / "vault"
    root.mkdir()
    store = tmp_path / "workspace.sqlite"
    monkeypatch.setattr(router, "DB_PATH", store)
    client = TestClient(app)

    response = client.post(
        "/workspace/api/vault/write",
        json={
            "root": str(root),
            "relative_path": "missing.md",
            "content": "x\n",
        },
    )
    assert response.status_code == 422
