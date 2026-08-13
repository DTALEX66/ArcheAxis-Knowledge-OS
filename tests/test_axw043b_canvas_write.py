"""AXW-043B: JSON Canvas safe-write tests.

Verifies the C3-compatible canvas write path:
- valid canvas round-trips with unknown fields preserved (no silent loss);
- invalid canvas documents are rejected and the file is left untouched;
- expected-hash conflict fails closed with 409;
- read → edit → write keeps node/edge/layout semantics.
"""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

from fastapi.testclient import TestClient

_CANVAS = {
    "nodes": [
        {"id": "n1", "type": "text", "x": 10, "y": 20, "width": 200, "height": 100, "text": "hello"},
        {"id": "n2", "type": "text", "x": 300, "y": 20, "width": 200, "height": 100, "text": "world"},
    ],
    "edges": [
        {"id": "e1", "fromNode": "n1", "toNode": "n2", "fromSide": "right", "toSide": "left"},
    ],
}


def _client(monkeypatch, tmp_path: Path, store: Path):
    import app.workspace.router as router

    monkeypatch.setattr(router, "DB_PATH", store)
    return TestClient(__import__("app.main", fromlist=["app"]).app)


def _write_canvas(root: Path, relative_path: str, content: str) -> None:
    target = root / relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8", newline="\n")


def test_canvas_roundtrip_preserves_unknown_fields(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path / "vault"
    root.mkdir()
    canvas = copy.deepcopy(_CANVAS)
    canvas["unknownTopLevel"] = {"keep": "me"}
    canvas["nodes"][0]["unknownField"] = "preserved"
    _write_canvas(root, "map.canvas", json.dumps(canvas))
    store = tmp_path / "workspace.sqlite"
    client = _client(monkeypatch, tmp_path, store)

    opened = client.post(
        "/workspace/api/vault/canvas/read",
        json={"root": str(root), "relative_path": "map.canvas"},
    ).json()
    assert opened["schema_version"] == "v1"
    assert opened["canvas"]["unknownTopLevel"] == {"keep": "me"}
    assert opened["canvas"]["nodes"][0]["unknownField"] == "preserved"
    current_hash = opened["source_hash"]

    edited = copy.deepcopy(opened["canvas"])
    edited["nodes"][0]["text"] = "edited"
    saved = client.post(
        "/workspace/api/vault/canvas/write",
        json={
            "root": str(root),
            "relative_path": "map.canvas",
            "canvas": edited,
            "expected_hash": current_hash,
        },
    )
    assert saved.status_code == 200, saved.text
    payload = saved.json()
    assert payload["expected_hash_checked"] is True

    # Unknown fields survived the write (no silent loss).
    on_disk = json.loads((root / "map.canvas").read_text(encoding="utf-8"))
    assert on_disk["unknownTopLevel"] == {"keep": "me"}
    assert on_disk["nodes"][0]["unknownField"] == "preserved"
    assert on_disk["nodes"][0]["text"] == "edited"
    assert on_disk["edges"][0]["fromNode"] == "n1"
    assert "vault-backups" in payload["backup_path"]


def test_canvas_invalid_document_rejected_file_untouched(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path / "vault"
    root.mkdir()
    _write_canvas(root, "map.canvas", json.dumps(_CANVAS))
    original = (root / "map.canvas").read_bytes()
    store = tmp_path / "workspace.sqlite"
    client = _client(monkeypatch, tmp_path, store)

    bad = copy.deepcopy(_CANVAS)
    bad["nodes"][0]["type"] = "video"  # not a valid canvas node type
    response = client.post(
        "/workspace/api/vault/canvas/write",
        json={"root": str(root), "relative_path": "map.canvas", "canvas": bad},
    )
    assert response.status_code == 422
    assert (root / "map.canvas").read_bytes() == original  # untouched


def test_canvas_write_conflict_fails_closed(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path / "vault"
    root.mkdir()
    _write_canvas(root, "map.canvas", json.dumps(_CANVAS))
    store = tmp_path / "workspace.sqlite"
    client = _client(monkeypatch, tmp_path, store)

    stale_hash = hashlib.sha256(b"stale\n").hexdigest()
    response = client.post(
        "/workspace/api/vault/canvas/write",
        json={
            "root": str(root),
            "relative_path": "map.canvas",
            "canvas": copy.deepcopy(_CANVAS),
            "expected_hash": stale_hash,
        },
    )
    if response.status_code != 409:
        raise AssertionError(f"expected 409, got {response.status_code}: {response.text}")
    assert response.status_code == 409
    detail = response.json()["detail"]
    assert "expected-hash mismatch" in detail["message"]
    assert "current_hash" in detail
    # File untouched after the conflict.
    assert json.loads((root / "map.canvas").read_text(encoding="utf-8"))["nodes"][0]["id"] == "n1"


def test_canvas_escape_and_missing_rejected(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path / "vault"
    root.mkdir()
    _write_canvas(root, "map.canvas", json.dumps(_CANVAS))
    store = tmp_path / "workspace.sqlite"
    client = _client(monkeypatch, tmp_path, store)

    escaped = client.post(
        "/workspace/api/vault/canvas/write",
        json={
            "root": str(root),
            "relative_path": "../outside.canvas",
            "canvas": copy.deepcopy(_CANVAS),
        },
    )
    assert escaped.status_code == 422

    missing = client.post(
        "/workspace/api/vault/canvas/write",
        json={
            "root": str(root),
            "relative_path": "nope.canvas",
            "canvas": copy.deepcopy(_CANVAS),
        },
    )
    assert missing.status_code == 422


def test_canvas_read_rejects_malformed_json(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path / "vault"
    root.mkdir()
    _write_canvas(root, "bad.canvas", "{not valid json")
    store = tmp_path / "workspace.sqlite"
    client = _client(monkeypatch, tmp_path, store)

    response = client.post(
        "/workspace/api/vault/canvas/read",
        json={"root": str(root), "relative_path": "bad.canvas"},
    )
    assert response.status_code == 422
    assert "not valid JSON" in response.json()["detail"]
