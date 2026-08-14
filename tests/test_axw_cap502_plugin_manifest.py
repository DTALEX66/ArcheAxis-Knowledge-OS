"""AXW-CAP-502 Plugin Manifest v1 tests.

Proves: valid manifests pass load/validate; missing permissions, unknown
permissions, bad platform, bad version and unknown fields are rejected
fail-closed; `is_compatible` rejects contract mismatches and platform
mismatches; the hand-written validator enforces the same contract when
jsonschema is unavailable.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from shared.plugin_manifest import (
    MANIFEST_VERSION,
    PluginManifest,
    is_compatible,
    load,
    load_manifest_from_mapping,
    validate,
)

VALID_MANIFEST = {
    "manifest_version": MANIFEST_VERSION,
    "plugin_id": "ax.vector_search",
    "name": "Vector Search",
    "version": "1.2.3",
    "api_contract": "1.x",
    "permissions": ["files.read", "model.load"],
    "platform": {"os": "windows", "arch": "x86_64"},
    "resources": {"cpu": "1", "memory_mb": 256},
    "license": "MIT",
    "data_ownership": {"declared": True, "note": "embeddings stored in workspace vault"},
    "healthcheck": "ping",
    "size_bytes": 4096,
    "entry": "entry.py",
    "dependencies": ["ax.core>=0.5"],
}


def _write(tmp_path: Path, name: str, data: dict) -> Path:
    path = tmp_path / name
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_valid_manifest_loads_and_roundtrips(tmp_path: Path) -> None:
    path = _write(tmp_path, "plugin-manifest.json", VALID_MANIFEST)
    manifest = load(path)
    assert isinstance(manifest, PluginManifest)
    assert manifest.plugin_id == "ax.vector_search"
    assert manifest.version == "1.2.3"
    assert manifest.permissions == ("files.read", "model.load")
    assert manifest.platform.os == "windows"
    assert manifest.platform.arch == "x86_64"
    assert manifest.entry == "entry.py"
    assert manifest.dependencies == ("ax.core>=0.5",)
    # round-trip survives validation
    validate(manifest.to_dict())
    assert load_manifest_from_mapping(json.loads(json.dumps(VALID_MANIFEST))) == manifest


def test_rejects_missing_permissions() -> None:
    manifest = json.loads(json.dumps(VALID_MANIFEST))
    del manifest["permissions"]
    with pytest.raises(ValueError, match="permissions"):
        validate(manifest)


def test_rejects_unknown_permission() -> None:
    manifest = json.loads(json.dumps(VALID_MANIFEST))
    manifest["permissions"] = ["files.read", "rm -rf"]
    with pytest.raises(ValueError, match="rm -rf"):
        validate(manifest)


def test_rejects_duplicate_permissions() -> None:
    manifest = json.loads(json.dumps(VALID_MANIFEST))
    manifest["permissions"] = ["files.read", "files.read"]
    with pytest.raises(ValueError):
        validate(manifest)


def test_rejects_missing_platform_and_bad_arch() -> None:
    manifest = json.loads(json.dumps(VALID_MANIFEST))
    del manifest["platform"]
    with pytest.raises(ValueError, match="platform"):
        validate(manifest)

    manifest = json.loads(json.dumps(VALID_MANIFEST))
    manifest["platform"] = {"os": "windows", "arch": "mips"}
    with pytest.raises(ValueError, match="mips"):
        validate(manifest)


def test_rejects_bad_version_and_bad_plugin_id() -> None:
    manifest = json.loads(json.dumps(VALID_MANIFEST))
    manifest["version"] = "1.2"
    with pytest.raises(ValueError):
        validate(manifest)

    manifest = json.loads(json.dumps(VALID_MANIFEST))
    manifest["plugin_id"] = "UPPER CASE"
    # jsonschema reports pattern violations as "'UPPER CASE' does not match ..."
    with pytest.raises(ValueError, match=r"UPPER CASE|plugin_id"):
        validate(manifest)


def test_rejects_unknown_field() -> None:
    manifest = json.loads(json.dumps(VALID_MANIFEST))
    manifest["backdoor"] = "payload"
    with pytest.raises(ValueError, match="backdoor"):
        validate(manifest)


def test_rejects_broken_json(tmp_path: Path) -> None:
    path = tmp_path / "broken.json"
    path.write_text("nope{", encoding="utf-8")
    with pytest.raises(ValueError, match="invalid JSON"):
        load(path)


def test_is_compatible_contract_match() -> None:
    manifest = load_manifest_from_mapping(json.loads(json.dumps(VALID_MANIFEST)))
    # plugin "1.x" vs host "1.x"
    assert is_compatible(manifest, "1.x", {"os": "windows", "arch": "x86_64"})
    # plugin "1.x" vs host ">=1.0,<2.0"
    assert is_compatible(manifest, ">=1.0,<2.0", {"os": "windows", "arch": "x86_64"})
    # plugin "1.x" vs host "2.x" — no overlap
    assert not is_compatible(manifest, "2.x", {"os": "windows", "arch": "x86_64"})
    # plugin "1.x" vs host "<1.0" — no overlap
    assert not is_compatible(manifest, "<1.0", {"os": "windows", "arch": "x86_64"})


def test_is_compatible_contract_intersection() -> None:
    manifest = load_manifest_from_mapping(json.loads(json.dumps(VALID_MANIFEST)))
    # plugin "1.x" intersects host ">=1.5,<2.5"
    assert is_compatible(manifest, ">=1.5,<2.5", {"os": "windows", "arch": "x86_64"})
    # plugin "1.x" does NOT intersect host ">=2.0"
    assert not is_compatible(manifest, ">=2.0", {"os": "windows", "arch": "x86_64"})


def test_is_compatible_platform_mismatch_rejected() -> None:
    manifest = load_manifest_from_mapping(json.loads(json.dumps(VALID_MANIFEST)))
    assert not is_compatible(manifest, "1.x", {"os": "linux", "arch": "x86_64"})
    assert not is_compatible(manifest, "1.x", {"os": "windows", "arch": "aarch64"})
    assert not is_compatible(manifest, "1.x", {"os": "windows"})  # arch missing


def test_is_compatible_any_platform_wildcard() -> None:
    manifest_data = json.loads(json.dumps(VALID_MANIFEST))
    manifest_data["platform"] = {"os": "any", "arch": "any"}
    manifest = load_manifest_from_mapping(manifest_data)
    assert is_compatible(manifest, "1.x", {"os": "macos", "arch": "arm64"})


def test_is_compatible_unparseable_range_fails_closed() -> None:
    manifest = load_manifest_from_mapping(json.loads(json.dumps(VALID_MANIFEST)))
    # unparseable host contract → incompatible, never permissive
    assert not is_compatible(manifest, "banana", {"os": "windows", "arch": "x86_64"})
    # unparseable plugin contract → incompatible
    bad_plugin = json.loads(json.dumps(VALID_MANIFEST))
    bad_plugin["api_contract"] = "not-a-range"
    assert not is_compatible(
        load_manifest_from_mapping(bad_plugin), "1.x", {"os": "windows", "arch": "x86_64"}
    )


def test_handwritten_validator_matches_schema_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(sys.modules, "jsonschema", None)

    validate(json.loads(json.dumps(VALID_MANIFEST)))  # valid passes

    missing = json.loads(json.dumps(VALID_MANIFEST))
    del missing["entry"]
    with pytest.raises(ValueError, match="entry"):
        validate(missing)

    extra = json.loads(json.dumps(VALID_MANIFEST))
    extra["sneaky"] = 1
    with pytest.raises(ValueError, match="sneaky"):
        validate(extra)

    no_perm = json.loads(json.dumps(VALID_MANIFEST))
    no_perm["permissions"] = ["process", "process"]
    with pytest.raises(ValueError, match="unique"):
        validate(no_perm)
