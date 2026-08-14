"""AXW-DATA-401 Workspace Manifest tests.

Proves create → load → validate round-trip, fail-closed rejection of
missing/invalid fields, the four-asset-domain directory layout, and that
the hand-written validator (jsonschema unavailable) enforces the same
contract as the JSON Schema path.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from shared.workspace_manifest import (
    ASSET_DOMAINS,
    SCHEMA_VERSION,
    create_workspace,
    load,
    validate,
)

VALID_MANIFEST = {
    "schema_version": SCHEMA_VERSION,
    "workspace_id": "ws-abc123",
    "created_at": "2026-08-14T00:00:00+00:00",
    "name": "test-workspace",
    "domains": {
        "source_archive": {"path": "/tmp/ws/source_archive", "type": "source_archive", "readonly": False},
        "evidence_ledger": {"path": "/tmp/ws/evidence_ledger", "type": "evidence_ledger", "readonly": False},
        "human_learning_vault": {"path": "/tmp/ws/human_learning_vault", "type": "human_learning_vault", "readonly": False},
        "ai_asset_vault": {"path": "/tmp/ws/ai_asset_vault", "type": "ai_asset_vault", "readonly": False},
    },
}


def test_create_load_validate_roundtrip(tmp_path: Path) -> None:
    created = create_workspace(tmp_path, "alpha")
    assert created.name == "alpha"
    assert created.schema_version == SCHEMA_VERSION
    assert created.workspace_id.startswith("ws-")

    manifest_path = tmp_path / "alpha" / "manifest.json"
    assert manifest_path.exists()

    loaded = load(manifest_path)
    assert loaded == created
    assert loaded.domains.keys() == set(ASSET_DOMAINS)
    for domain_key in ASSET_DOMAINS:
        assert loaded.domains[domain_key].type == domain_key
        assert loaded.domains[domain_key].readonly is False
        assert Path(loaded.domains[domain_key].path).is_dir()

    # validate() accepts the round-tripped mapping
    validate(loaded.to_dict())


def test_create_workspace_directory_structure(tmp_path: Path) -> None:
    created = create_workspace(tmp_path, "bravo")
    workspace_dir = tmp_path / "bravo"
    for domain_key in ASSET_DOMAINS:
        assert (workspace_dir / domain_key).is_dir()
    assert (workspace_dir / "backups").is_dir()
    assert (workspace_dir / "derived").is_dir()
    assert (workspace_dir / "logs").is_dir()
    # manifest lists every domain path as an existing directory
    for domain in created.domains.values():
        assert Path(domain.path).is_dir()


def test_create_workspace_reuses_existing_valid_manifest(tmp_path: Path) -> None:
    first = create_workspace(tmp_path, "charlie")
    second = create_workspace(tmp_path, "charlie")
    assert second == first
    assert second.workspace_id == first.workspace_id


def test_create_workspace_rejects_empty_name(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        create_workspace(tmp_path, "   ")


def test_validate_rejects_missing_required_field() -> None:
    missing_domains = {key: value for key, value in VALID_MANIFEST.items() if key != "domains"}
    with pytest.raises(ValueError, match="domains"):
        validate(missing_domains)

    missing_name = {key: value for key, value in VALID_MANIFEST.items() if key != "name"}
    with pytest.raises(ValueError, match="name"):
        validate(missing_name)


def test_validate_rejects_missing_asset_domain() -> None:
    manifest = json.loads(json.dumps(VALID_MANIFEST))
    del manifest["domains"]["ai_asset_vault"]
    with pytest.raises(ValueError, match="ai_asset_vault"):
        validate(manifest)


def test_validate_rejects_unknown_top_level_field() -> None:
    manifest = json.loads(json.dumps(VALID_MANIFEST))
    manifest["surprise"] = True
    with pytest.raises(ValueError, match="surprise"):
        validate(manifest)


def test_validate_rejects_malformed_domain_entry() -> None:
    manifest = json.loads(json.dumps(VALID_MANIFEST))
    manifest["domains"]["source_archive"] = {"path": "/tmp/x", "type": "source_archive"}
    with pytest.raises(ValueError, match="readonly"):
        validate(manifest)

    manifest = json.loads(json.dumps(VALID_MANIFEST))
    manifest["domains"]["evidence_ledger"] = {"path": "/tmp/x", "type": "nonsense", "readonly": False}
    with pytest.raises(ValueError, match="evidence_ledger"):
        validate(manifest)


def test_validate_rejects_unsupported_schema_version() -> None:
    manifest = json.loads(json.dumps(VALID_MANIFEST))
    manifest["schema_version"] = "9.9"
    # jsonschema reports const violations as "'1.0' was expected"; the
    # handwritten path names the field — accept either message shape.
    with pytest.raises(ValueError, match=r"was expected|schema_version"):
        validate(manifest)


def test_validate_rejects_non_mapping_root() -> None:
    with pytest.raises(ValueError):
        validate(["not", "a", "manifest"])


def test_load_rejects_broken_json(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    with pytest.raises(ValueError, match="invalid JSON"):
        load(bad)


def test_handwritten_validator_matches_schema_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    """With jsonschema unavailable the hand-written validator must enforce
    the same required-field contract (fail-closed)."""
    monkeypatch.setitem(sys.modules, "jsonschema", None)

    validate(json.loads(json.dumps(VALID_MANIFEST)))  # valid passes

    missing = {key: value for key, value in VALID_MANIFEST.items() if key != "workspace_id"}
    with pytest.raises(ValueError, match="workspace_id"):
        validate(missing)

    extra = json.loads(json.dumps(VALID_MANIFEST))
    extra["mystery"] = 1
    with pytest.raises(ValueError, match="mystery"):
        validate(extra)

    # capability_lock shape is enforced by the handwritten path too
    locked = json.loads(json.dumps(VALID_MANIFEST))
    locked["capability_lock"] = [{"capability_id": "search"}]
    with pytest.raises(ValueError, match="version_range"):
        validate(locked)
