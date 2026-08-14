"""AXW-CAP-501 Capability Store v1 tests.

Full lifecycle over a tmp_path root: stage a fake pack → activate (hash
verified, atomic move) → list → disable → enable → quarantine, asserting
directory movements and registry index transitions. Also proves fail-closed
behavior: packs without a manifest are refused, tampered staged packs are
refused at activation, and the HTTP API surfaces the same lifecycle.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.capability.router import router as capability_router
from app.capability.store import CapabilityStore, CapabilityStoreError
from shared.plugin_manifest import MANIFEST_VERSION

VALID_MANIFEST = {
    "manifest_version": MANIFEST_VERSION,
    "plugin_id": "ax.vector_search",
    "name": "Vector Search",
    "version": "1.2.3",
    "api_contract": "1.x",
    "permissions": ["files.read", "model.load"],
    "platform": {"os": "windows", "arch": "x86_64"},
    "entry": "entry.py",
}


def make_pack(tmp_path: Path, name: str = "pack1", plugin_id: str = "ax.vector_search") -> Path:
    pack = tmp_path / name
    pack.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(json.dumps(VALID_MANIFEST))
    manifest["plugin_id"] = plugin_id
    (pack / "plugin-manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    (pack / "entry.py").write_text("def run():\n    return 42\n", encoding="utf-8")
    (pack / "assets").mkdir()
    (pack / "assets" / "model.bin").write_bytes(b"\x00\x01\x02model")
    return pack


def test_partitions_created(tmp_path: Path) -> None:
    CapabilityStore(tmp_path / "capstore")
    for partition in ("registry", "installed", "disabled", "staging", "quarantine", "packages"):
        assert (tmp_path / "capstore" / partition).is_dir()


def test_stage_activate_list_disable_enable_quarantine(tmp_path: Path) -> None:
    store = CapabilityStore(tmp_path / "capstore")
    pack = make_pack(tmp_path)

    staged = store.stage(pack)
    assert staged.status == "staged"
    assert staged.plugin_id == "ax.vector_search"
    assert staged.content_hash
    staged_dirs = list((tmp_path / "capstore" / "staging").iterdir())
    assert len(staged_dirs) == 1
    staged_id = staged_dirs[0].name

    activated = store.activate(staged_id)
    assert activated.status == "installed"
    assert activated.activated_at is not None
    # staging emptied, installed populated
    assert not list((tmp_path / "capstore" / "staging").iterdir())
    installed_dir = tmp_path / "capstore" / "installed" / "ax.vector_search@1.2.3"
    assert installed_dir.is_dir()
    assert (installed_dir / "entry.py").is_file()
    assert (installed_dir / "assets" / "model.bin").is_file()
    assert (installed_dir / ".capability.json").is_file()

    listed = store.list_installed()
    assert [record.plugin_id for record in listed] == ["ax.vector_search"]
    assert listed[0].status == "installed"

    disabled = store.disable("ax.vector_search")
    assert disabled.status == "disabled"
    assert not installed_dir.exists()
    assert (tmp_path / "capstore" / "disabled" / "ax.vector_search@1.2.3").is_dir()
    assert store.list_installed() == []

    enabled = store.enable("ax.vector_search")
    assert enabled.status == "installed"
    assert installed_dir.is_dir()
    assert not (tmp_path / "capstore" / "disabled" / "ax.vector_search@1.2.3").exists()

    quarantined = store.quarantine("ax.vector_search", "suspicious network call")
    assert quarantined.status == "quarantined"
    assert quarantined.quarantine_reason == "suspicious network call"
    assert not installed_dir.exists()
    quarantine_dir = tmp_path / "capstore" / "quarantine" / "ax.vector_search@1.2.3"
    assert quarantine_dir.is_dir()
    journal = json.loads((quarantine_dir / ".quarantine.json").read_text(encoding="utf-8"))
    assert journal["reason"] == "suspicious network call"
    assert store.list_installed() == []


def test_stage_refuses_pack_without_manifest(tmp_path: Path) -> None:
    store = CapabilityStore(tmp_path / "capstore")
    bare = tmp_path / "bare"
    bare.mkdir()
    (bare / "entry.py").write_text("x = 1", encoding="utf-8")
    with pytest.raises(CapabilityStoreError, match="plugin-manifest.json"):
        store.stage(bare)


def test_stage_refuses_invalid_manifest(tmp_path: Path) -> None:
    store = CapabilityStore(tmp_path / "capstore")
    bad = tmp_path / "bad"
    bad.mkdir()
    (bad / "plugin-manifest.json").write_text(
        json.dumps({"manifest_version": MANIFEST_VERSION, "plugin_id": "x"}), encoding="utf-8"
    )
    with pytest.raises(ValueError, match=r"required|permissions"):
        store.stage(bad)


def test_activate_refuses_tampered_staged_pack(tmp_path: Path) -> None:
    store = CapabilityStore(tmp_path / "capstore")
    staged = store.stage(make_pack(tmp_path))
    staged_id = list((tmp_path / "capstore" / "staging").iterdir())[0].name
    assert staged.status == "staged"

    # tamper with a payload file AFTER staging — hash must catch it
    staged_dir = tmp_path / "capstore" / "staging" / staged_id
    (staged_dir / "entry.py").write_text("def run():\n    return 999\n", encoding="utf-8")

    with pytest.raises(CapabilityStoreError, match="hash mismatch"):
        store.activate(staged_id)
    # nothing moved, pack stays in staging, nothing installed
    assert (tmp_path / "capstore" / "staging" / staged_id).is_dir()
    assert not (tmp_path / "capstore" / "installed" / "ax.vector_search@1.2.3").exists()
    assert store.list_installed() == []


def test_activate_refuses_unknown_staged_id(tmp_path: Path) -> None:
    store = CapabilityStore(tmp_path / "capstore")
    with pytest.raises(CapabilityStoreError, match="unknown staged"):
        store.activate("deadbeef00000000")


def test_quarantine_requires_reason(tmp_path: Path) -> None:
    store = CapabilityStore(tmp_path / "capstore")
    store.stage(make_pack(tmp_path))
    staged_id = list((tmp_path / "capstore" / "staging").iterdir())[0].name
    store.activate(staged_id)
    with pytest.raises(CapabilityStoreError, match="reason"):
        store.quarantine("ax.vector_search", "   ")


def test_api_full_lifecycle(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ARCHEAXIS_CAPABILITY_ROOT", str(tmp_path / "api-capstore"))
    app = FastAPI()
    app.include_router(capability_router)
    client = TestClient(app)
    pack = make_pack(tmp_path, name="apipack")

    staged = client.post("/api/v1/capabilities/stage", json={"path": str(pack)})
    assert staged.status_code == 200, staged.text
    staged_id = staged.json()["staged"]["plugin_id"]  # plugin_id, not staged id
    assert staged_id == "ax.vector_search"

    # locate the real staged id on disk
    staging_dir = tmp_path / "api-capstore" / "staging"
    real_staged_id = list(staging_dir.iterdir())[0].name

    activated = client.post(f"/api/v1/capabilities/activate/{real_staged_id}")
    assert activated.status_code == 200, activated.text
    assert activated.json()["activated"]["status"] == "installed"

    listing = client.get("/api/v1/capabilities/")
    assert listing.status_code == 200
    body = listing.json()
    assert body["count"] == 1
    assert body["capabilities"][0]["plugin_id"] == "ax.vector_search"

    disabled = client.post("/api/v1/capabilities/disable/ax.vector_search")
    assert disabled.status_code == 200, disabled.text
    assert disabled.json()["disabled"]["status"] == "disabled"

    quarantined = client.post(
        "/api/v1/capabilities/quarantine/ax.vector_search", json={"reason": "API test"}
    )
    assert quarantined.status_code == 200, quarantined.text
    assert quarantined.json()["quarantined"]["status"] == "quarantined"
    assert client.get("/api/v1/capabilities/").json()["count"] == 0


def test_api_fails_closed_on_bad_pack(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ARCHEAXIS_CAPABILITY_ROOT", str(tmp_path / "api-capstore2"))
    app = FastAPI()
    app.include_router(capability_router)
    client = TestClient(app)

    # staging a pack without a manifest → 400
    bare = tmp_path / "bare"
    bare.mkdir()
    (bare / "x.txt").write_text("hi", encoding="utf-8")
    response = client.post("/api/v1/capabilities/stage", json={"path": str(bare)})
    assert response.status_code == 400
    assert "plugin-manifest.json" in response.json()["detail"]

    # activating an unknown staged id → 400
    response = client.post("/api/v1/capabilities/activate/nope000000000000")
    assert response.status_code == 400


def test_capability_router_mounted_in_real_app(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The capability API must be reachable through the real app.main app."""
    monkeypatch.setenv("ARCHEAXIS_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("ARCHEAXIS_CAPABILITY_ROOT", str(tmp_path / "app-capstore"))
    from app.main import app

    client = TestClient(app)
    response = client.get("/api/v1/capabilities/")
    assert response.status_code == 200, response.text
    assert response.json() == {"count": 0, "capabilities": []}
