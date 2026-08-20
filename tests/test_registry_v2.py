"""Tests for Registry V2 contract: migration, validation, schema integrity."""

from __future__ import annotations

import json
from pathlib import Path

from shared.registry_v2 import (
    AbsorptionMode,
    EvidenceState,
    LicenseInfo,
    ProjectStatus,
    ProvenanceEvidence,
    RegistryEntryV2,
    RiskAssessment,
    RiskPolicy,
    validate_registry,
    validate_registry_ledger_pair,
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
    source = (Path(__file__).resolve().parents[1] / "shared" / "registry_v2.py").read_text(
        encoding="utf-8"
    )
    assert "class RegistryEntryV2" in source
    assert "class AbsorptionMode" in source
    assert "class ProjectStatus" in source
    assert "def from_v1" in source
    assert "def validate_registry" in source


def test_registry_v2_keeps_unprovenanced_v1_entries_explicitly_unknown():
    entry = RegistryEntryV2.from_v1({"project_id": "osp_0001", "name": "candidate"})

    assert entry.provenance == ProvenanceEvidence(state=EvidenceState.UNKNOWN)
    assert entry.status == ProjectStatus.CANDIDATE


def test_registry_v2_reads_explicit_provenance_without_upgrading_status():
    entry = RegistryEntryV2.from_v1(
        {
            "project_id": "osp_0001",
            "name": "candidate",
            "status": "candidate",
            "provenance": {
                "canonical_source": "https://example.invalid/project",
                "source_revision": "deadbeef",
                "license_snapshot": "sha256:license",
                "implementation_paths": ["app/example.py"],
                "test_evidence": ["tests/test_example.py::test_contract"],
                "runtime_evidence": ["runtime:local-smoke"],
                "rollback_handle": "commit:abc123",
                "state": "recorded",
            },
        }
    )

    assert entry.status == ProjectStatus.CANDIDATE
    assert entry.provenance.state == EvidenceState.RECORDED
    assert entry.provenance.implementation_paths == ("app/example.py",)
    assert entry.provenance.test_evidence == ("tests/test_example.py::test_contract",)
    assert entry.provenance.runtime_evidence == ("runtime:local-smoke",)


def test_registry_v2_recorded_requires_at_least_one_evidence_field():
    empty = RegistryEntryV2.from_v1(
        {
            "project_id": "osp_0001",
            "name": "candidate",
            "provenance": {"state": "recorded"},
        }
    )
    recorded = RegistryEntryV2.from_v1(
        {
            "project_id": "osp_0001",
            "name": "candidate",
            "provenance": {
                "state": "recorded",
                "canonical_source": "https://example.invalid",
            },
        }
    )

    assert empty.provenance.state == EvidenceState.UNKNOWN
    assert recorded.provenance.state == EvidenceState.RECORDED

    malformed = RegistryEntryV2.from_v1(
        {
            "project_id": "osp_0001",
            "name": "candidate",
            "provenance": {"state": "recorded", "canonical_source": 1},
        }
    )
    assert malformed.provenance.state == EvidenceState.UNKNOWN


def test_registry_v2_preserves_v1_positional_constructor_prefix():
    entry = RegistryEntryV2(
        "osp_0001",
        "candidate",
        None,
        None,
        "category",
        "target",
        AbsorptionMode.REFERENCE_CANDIDATE,
        ProjectStatus.CANDIDATE,
        RiskPolicy.STANDARD_REVIEW,
        LicenseInfo(),
        RiskAssessment(),
        "note",
        ["alias"],
        False,
    )

    assert entry.note == "note"
    assert entry.aliases == ["alias"]
    assert entry.requires_human_review is False
    assert entry.provenance.state == EvidenceState.UNKNOWN


def test_provenance_evidence_preserves_legacy_positional_prefix():
    evidence = ProvenanceEvidence(
        "https://example.invalid/project",
        "deadbeef",
        "sha256:license",
        ("app/example.py",),
        "commit:abc123",
        EvidenceState.RECORDED,
    )

    assert evidence.rollback_handle == "commit:abc123"
    assert evidence.state is EvidenceState.RECORDED
    assert evidence.test_evidence == ()
    assert evidence.runtime_evidence == ()


def test_registry_v2_malformed_provenance_fails_closed_to_unknown():
    for raw in (
        {"state": None, "implementation_paths": [1]},
        {"state": {"verified": True}},
        {"state": "not-a-state", "implementation_paths": {"path": "bad"}},
    ):
        entry = RegistryEntryV2.from_v1(
            {"project_id": "osp_0001", "name": "candidate", "provenance": raw}
        )
        assert entry.status == ProjectStatus.CANDIDATE
        assert entry.provenance.state == EvidenceState.UNKNOWN


def test_registry_v2_verified_requires_complete_provenance():
    incomplete = RegistryEntryV2.from_v1(
        {
            "project_id": "osp_0001",
            "name": "candidate",
            "provenance": {"state": "verified"},
        }
    )
    complete = RegistryEntryV2.from_v1(
        {
            "project_id": "osp_0001",
            "name": "candidate",
            "provenance": {
                "state": "verified",
                "canonical_source": "https://example.invalid/project",
                "source_revision": "deadbeef",
                "license_snapshot": "sha256:license",
                "implementation_paths": [1, "app/example.py"],
                "test_evidence": ["tests/test_example.py::test_contract"],
                "runtime_evidence": ["runtime:local-smoke"],
                "rollback_handle": "commit:abc123",
            },
        }
    )

    assert incomplete.provenance.state == EvidenceState.UNKNOWN
    assert complete.provenance.state == EvidenceState.UNKNOWN

    complete = RegistryEntryV2.from_v1(
        {
            "project_id": "osp_0001",
            "name": "candidate",
            "provenance": {
                "state": "verified",
                "canonical_source": "https://example.invalid/project",
                "source_revision": "deadbeef",
                "license_snapshot": "sha256:license",
                "implementation_paths": ["app/example.py"],
                "test_evidence": ["tests/test_example.py::test_contract"],
                "runtime_evidence": ["runtime:local-smoke"],
                "rollback_handle": "commit:abc123",
            },
        }
    )

    assert complete.provenance.state == EvidenceState.VERIFIED
    assert complete.status == ProjectStatus.CANDIDATE


def test_registry_v2_verified_rejects_whitespace_evidence():
    entry = RegistryEntryV2.from_v1(
        {
            "project_id": "osp_0001",
            "name": "candidate",
            "provenance": {
                "state": "verified",
                "canonical_source": " ",
                "source_revision": "rev",
                "license_snapshot": "license",
                "implementation_paths": ["  "],
                "test_evidence": ["tests/test_example.py::test_contract"],
                "runtime_evidence": ["runtime:local-smoke"],
                "rollback_handle": "rollback",
            },
        }
    )

    assert entry.provenance.state == EvidenceState.UNKNOWN


def test_registry_v2_verified_requires_test_and_runtime_evidence():
    entry = RegistryEntryV2.from_v1(
        {
            "project_id": "osp_0001",
            "name": "candidate",
            "provenance": {
                "state": "verified",
                "canonical_source": "https://example.invalid/project",
                "source_revision": "deadbeef",
                "license_snapshot": "sha256:license",
                "implementation_paths": ["app/example.py"],
                "rollback_handle": "commit:abc123",
            },
        }
    )

    assert entry.provenance.state == EvidenceState.UNKNOWN


def test_registry_v2_validates_registry_ledger_identity_and_implemented_evidence():
    registry = [{
        "project_id": "osp_0001",
        "name": "candidate",
        "category": "",
        "recommended_target": "",
        "absorption_mode": "",
        "risk_policy": "standard_review",
        "note": "",
        "status": "candidate",
    }]
    ledger = [{
        "project_id": "osp_0001",
        "name": "candidate",
        "category": "",
        "recommended_target": "",
        "absorption_mode": "",
        "risk_policy": "standard_review",
        "note": "",
        "source_status": "candidate",
        "execution_state": "implemented",
    }]

    errors = validate_registry_ledger_pair(registry, ledger)

    assert errors == ["osp_0001: implemented entry lacks implementation_evidence"]


def test_registry_v2_identity_gate_rejects_duplicate_and_missing_ids():
    assert validate_registry_ledger_pair(
        [{"project_id": "osp_0001"}, {"project_id": "osp_0001"}],
        [{"project_id": "osp_0001"}],
    ) == ["registry entry [1]: duplicate project_id osp_0001"]
    assert validate_registry_ledger_pair(
        [{"name": "missing"}],
        [{"name": "missing"}],
    ) == [
        "registry entry [0]: project_id must be non-empty string",
        "ledger entry [0]: project_id must be non-empty string",
    ]


def test_registry_v2_identity_gate_rejects_status_mismatch():
    registry = [{"project_id": "osp_0001", "status": "candidate"}]
    ledger = [
        {
            "project_id": "osp_0001",
            "source_status": "verified",
            "execution_state": "reference_only",
        }
    ]

    assert validate_registry_ledger_pair(registry, ledger) == [
        "osp_0001: missing identity field: name",
        "osp_0001: missing identity field: category",
        "osp_0001: missing identity field: recommended_target",
        "osp_0001: missing identity field: absorption_mode",
        "osp_0001: missing identity field: risk_policy",
        "osp_0001: missing identity field: note",
        "osp_0001: shared field differs: status",
    ]


def test_registry_v2_identity_gate_rejects_malformed_execution_state():
    registry = [{"project_id": "osp_0001", "status": "candidate"}]
    ledger = [{
        "project_id": "osp_0001",
        "source_status": "candidate",
        "execution_state": ["implemented"],
    }]

    errors = validate_registry_ledger_pair(registry, ledger)

    assert "osp_0001: invalid execution_state ['implemented']" in errors
