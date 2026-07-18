"""Tests for Registry V2 contract: migration, validation, schema integrity."""

from __future__ import annotations

import json
from pathlib import Path

from shared.registry_v2 import (
    AbsorptionMode,
    ProjectStatus,
    RegistryEntryV2,
    validate_registry,
)

_REGISTRY_PATH = (
    Path(__file__).resolve().parents[1]
    / "inspiration_research"
    / "resources"
    / "open_source_project_registry.json"
)


def test_registry_v2_migrates_all_101_entries_without_loss():
    assert _REGISTRY_PATH.is_file()
    raw = json.loads(_REGISTRY_PATH.read_text(encoding="utf-8"))
    entries = raw["projects"]
    assert len(entries) == 101

    migrated, errors = validate_registry(entries)
    assert errors == []
    assert len(migrated) == 101

    asset_ids = {e.asset_id for e in migrated}
    assert len(asset_ids) == 101
    assert "osp_0001" in asset_ids
    assert "osp_0103" in asset_ids


def test_registry_v2_preserves_known_first_entry():
    raw = json.loads(_REGISTRY_PATH.read_text(encoding="utf-8"))
    first = RegistryEntryV2.from_v1(raw["projects"][0])
    assert first.asset_id == "osp_0001"
    assert first.name == "sst/opencode"
    assert first.absorption_mode == AbsorptionMode.REFERENCE_CANDIDATE
    assert first.status == ProjectStatus.CANDIDATE
    assert first.requires_human_review is True


def test_registry_v2_normalizes_absorption_mode_variants():
    assert RegistryEntryV2._normalize_absorption_mode("adapter_candidate") == AbsorptionMode.ADAPTER
    assert RegistryEntryV2._normalize_absorption_mode("selective_licensed_port") == AbsorptionMode.LICENSED_PORT
    assert RegistryEntryV2._normalize_absorption_mode("参考/候选Adapter") == AbsorptionMode.REFERENCE_CANDIDATE
    assert RegistryEntryV2._normalize_absorption_mode("unknown") == AbsorptionMode.REFERENCE_CANDIDATE


def test_registry_v2_rejects_duplicate_ids():
    _, errors = validate_registry([
        {"project_id": "osp_0001", "name": "a"},
        {"project_id": "osp_0001", "name": "b"},
    ])
    assert len(errors) == 1
    assert "duplicate" in errors[0].lower()


def test_registry_v2_rejects_missing_id():
    _, errors = validate_registry([{"name": "no-id"}])
    assert len(errors) == 1
    assert "missing" in errors[0].lower()


def test_registry_v2_contract_is_frozen_for_package_discovery():
    source = (Path(__file__).resolve().parents[1] / "shared" / "registry_v2.py").read_text()
    assert "class RegistryEntryV2" in source
    assert "class AbsorptionMode" in source
    assert "class ProjectStatus" in source
    assert "def from_v1" in source
    assert "def validate_registry" in source
