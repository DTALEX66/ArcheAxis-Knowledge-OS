"""AXW-CAP-503 builtin conversion plugin extraction tests.

Proves: ``app.capability.builtin.discover()`` returns all six builtin
converter plugins (docx/html/media/ocr/pptx/xlsx) with manifests that
validate against the shared plugin-manifest contract; healthcheck probes
pass for the real adapter modules; CapabilityStore.install_builtin() is
idempotent, registers under installed/ and plugins/, and refuses tampered
builtin packs fail-closed.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from app.capability import builtin as builtin_pkg
from app.capability.builtin import converters_docx, discover, healthcheck_all
from app.capability.store import CapabilityStore, CapabilityStoreError
from shared.plugin_manifest import MANIFEST_VERSION, is_compatible, validate

EXPECTED_PLUGIN_IDS = {
    "ax.builtin.converter.docx",
    "ax.builtin.converter.html",
    "ax.builtin.converter.media",
    "ax.builtin.converter.ocr",
    "ax.builtin.converter.pptx",
    "ax.builtin.converter.xlsx",
}

EXPECTED_ADAPTER_MODULES = {
    "app.ingestion.docx_adapter",
    "app.ingestion.html_adapter",
    "app.ingestion.media_adapter",
    "app.ingestion.ocr_adapter",
    "app.ingestion.pptx_adapter",
    "app.ingestion.xlsx_adapter",
}

ALLOWED_PERMISSIONS = {
    "files.read",
    "files.write",
    "network",
    "process",
    "model.load",
    "ui.contribution",
}


def test_discover_returns_all_six_builtin_plugins() -> None:
    manifests = discover()
    assert len(manifests) == 6
    assert {manifest.plugin_id for manifest in manifests} == EXPECTED_PLUGIN_IDS
    for manifest in manifests:
        validate(manifest.to_dict())
        assert is_compatible(manifest, "1.x", {"os": "windows", "arch": "x86_64"})


def test_manifests_carry_required_builtin_fields() -> None:
    for manifest in discover():
        data = manifest.to_dict()
        assert data["manifest_version"] == MANIFEST_VERSION
        assert data["platform"] == {"os": "windows", "arch": "x86_64"}
        assert set(data["permissions"]) <= ALLOWED_PERMISSIONS
        assert data["permissions"]
        assert data["healthcheck"].startswith("import:")
        assert data["data_ownership"]["declared"] is True
        assert data["entry"].startswith("app.ingestion.")
        # round-trip: the dict survives validation exactly as exported
        assert validate(json.loads(json.dumps(data))) == data


def test_healthcheck_probes_real_adapter_modules() -> None:
    results = {result["plugin_id"]: result for result in healthcheck_all()}
    assert set(results) == EXPECTED_PLUGIN_IDS
    assert len(results) == 6
    for manifest in discover():
        probe = manifest.healthcheck.removeprefix("import:")
        assert probe in EXPECTED_ADAPTER_MODULES
        # the probed module must actually exist on disk/import path
        assert importlib.util.find_spec(probe) is not None
        result = results[manifest.plugin_id]
        assert result["ok"] is True
        assert probe in result["detail"]


def test_discover_fails_closed_on_invalid_builtin_manifest(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bad = dict(converters_docx.MANIFEST)
    bad["permissions"] = ["rm -rf"]
    monkeypatch.setattr(converters_docx, "MANIFEST", bad)
    with pytest.raises(ValueError, match="rm -rf"):
        builtin_pkg.discover()


def test_store_installs_two_builtins_and_is_idempotent(tmp_path: Path) -> None:
    store = CapabilityStore(tmp_path / "capstore")
    manifests = {manifest.plugin_id: manifest for manifest in discover()}
    calls: list[str] = []

    def activator_for(plugin_id: str):
        def activate() -> None:
            calls.append(plugin_id)

        return activate

    docx = store.install_builtin(
        manifests["ax.builtin.converter.docx"], activator_for("ax.builtin.converter.docx")
    )
    pptx = store.install_builtin(
        manifests["ax.builtin.converter.pptx"], activator_for("ax.builtin.converter.pptx")
    )
    assert docx.status == "installed"
    assert pptx.status == "installed"
    assert docx.content_hash and pptx.content_hash

    records = {record.plugin_id: record for record in store.list_all()}
    assert set(records) == {"ax.builtin.converter.docx", "ax.builtin.converter.pptx"}
    assert all(record.status == "installed" for record in records.values())

    # manifest materialized in installed/ + registered under plugins/
    for plugin_id, record in records.items():
        installed_dir = tmp_path / "capstore" / "installed" / f"{plugin_id}@{record.version}"
        assert (installed_dir / "plugin-manifest.json").is_file()
        assert (installed_dir / ".capability.json").is_file()
        registration = json.loads(
            (tmp_path / "capstore" / "plugins" / f"{plugin_id}.json").read_text(encoding="utf-8")
        )
        assert registration["kind"] == "builtin"
        assert registration["content_hash"] == record.content_hash
        assert registration["manifest"]["plugin_id"] == plugin_id

    # idempotent re-activation: same record, activator NOT re-invoked
    again = store.install_builtin(
        manifests["ax.builtin.converter.docx"], activator_for("ax.builtin.converter.docx")
    )
    assert again == records["ax.builtin.converter.docx"]
    assert again.content_hash == records["ax.builtin.converter.docx"].content_hash
    assert calls == ["ax.builtin.converter.docx", "ax.builtin.converter.pptx"]
    assert store.get_activator("ax.builtin.converter.docx") is not None
    assert store.get_activator("ax.builtin.converter.ocr") is None
    assert len(store.list_installed()) == 2


def test_store_refuses_tampered_installed_builtin(tmp_path: Path) -> None:
    store = CapabilityStore(tmp_path / "capstore")
    manifest = next(item for item in discover() if item.plugin_id == "ax.builtin.converter.docx")
    installed = store.install_builtin(manifest)
    pack_dir = (
        tmp_path / "capstore" / "installed" / f"ax.builtin.converter.docx@{installed.version}"
    )

    # the registered manifest is immutable — tampering must be refused
    (pack_dir / "plugin-manifest.json").write_text("{}", encoding="utf-8")
    with pytest.raises(CapabilityStoreError, match="modified|hash mismatch"):
        store.install_builtin(manifest)


def test_store_accepts_builtin_manifest_dict_directly(tmp_path: Path) -> None:
    store = CapabilityStore(tmp_path / "capstore")
    manifest = next(item for item in discover() if item.plugin_id == "ax.builtin.converter.html")
    record = store.install_builtin(manifest.to_dict())
    assert record.plugin_id == "ax.builtin.converter.html"
    assert record.status == "installed"
