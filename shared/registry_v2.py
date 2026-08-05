"""Registry V2 contract: canonical open-source project metadata for intake/governance.

Contract-first design: define the schema, then validate existing data against it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class AbsorptionMode(str, Enum):
    REFERENCE_CANDIDATE = "参考/候选Adapter"
    DIRECT_DEPENDENCY = "direct_dependency"
    ADAPTER = "adapter"
    LICENSED_PORT = "licensed_port"
    INDEPENDENT_REIMPLEMENTATION = "independent_reimplementation"
    ALGORITHM_REFERENCE = "algorithm_reference"
    UX_REFERENCE = "ux_reference"
    RESEARCH_ONLY = "research_only"
    REJECTED = "rejected"


class ProjectStatus(str, Enum):
    CANDIDATE = "candidate"
    DISCOVERED = "discovered"
    VERIFIED = "verified"
    SCREENED = "screened"
    INTAKE_APPROVED = "intake_approved"
    ADAPTER_APPROVED = "adapter_approved"
    INTEGRATED = "integrated"
    OBSERVED = "observed"
    DEPRECATED = "deprecated"
    REJECTED = "rejected"


class RiskPolicy(str, Enum):
    STANDARD_REVIEW = "standard_review"
    MUST_REVIEW_BEFORE_USE = "must_review_before_use"
    ELEVATED_REVIEW = "elevated_review"
    RESTRICTED = "restricted"


class EvidenceState(str, Enum):
    """Provenance state; unknown data must never be treated as verified."""

    UNKNOWN = "unknown"
    RECORDED = "recorded"
    VERIFIED = "verified"


@dataclass(frozen=True)
class LicenseInfo:
    spdx: str | None = None
    verified: bool = False
    files: list[str] = field(default_factory=list)
    notice_required: bool = False


@dataclass(frozen=True)
class RiskAssessment:
    network_access: bool = False
    data_access: bool = False
    hardware_requirements: str | None = None
    dependency_risk: str | None = None
    security_supply_chain_risk: str | None = None
    architecture_fit_score: float | None = None


@dataclass(frozen=True)
class ProvenanceEvidence:
    """Evidence fields that may remain unknown until independently collected."""

    canonical_source: str | None = None
    source_revision: str | None = None
    license_snapshot: str | None = None
    implementation_paths: tuple[str, ...] = ()
    rollback_handle: str | None = None
    state: EvidenceState = EvidenceState.UNKNOWN
    test_evidence: tuple[str, ...] = ()
    runtime_evidence: tuple[str, ...] = ()


@dataclass(frozen=True)
class RegistryEntryV2:
    """Canonical V2 registry entry for one open-source project candidate."""

    asset_id: str
    name: str
    repository_url: str | None = None
    pinned_revision: str | None = None
    category: str = ""
    target_module: str = ""
    absorption_mode: AbsorptionMode = AbsorptionMode.REFERENCE_CANDIDATE
    status: ProjectStatus = ProjectStatus.CANDIDATE
    risk_policy: RiskPolicy = RiskPolicy.STANDARD_REVIEW
    license_info: LicenseInfo = field(default_factory=LicenseInfo)
    risk_assessment: RiskAssessment = field(default_factory=RiskAssessment)
    note: str = ""
    aliases: list[str] = field(default_factory=list)
    requires_human_review: bool = True
    # Appended after all V1 fields to preserve the public positional API.
    provenance: ProvenanceEvidence = field(default_factory=ProvenanceEvidence)

    @classmethod
    def from_v1(cls, entry: dict[str, Any]) -> RegistryEntryV2:
        """Lossless migration from the current flat V1 format."""
        absorption = cls._normalize_absorption_mode(entry.get("absorption_mode", ""))
        status = cls._normalize_status(entry.get("status", "candidate"))
        return cls(
            asset_id=entry.get("project_id", entry.get("asset_id", "")),
            name=entry["name"],
            category=entry.get("category", ""),
            target_module=entry.get("recommended_target", ""),
            absorption_mode=absorption,
            status=status,
            risk_policy=RiskPolicy(
                entry.get("risk_policy", "standard_review")
            ),
            note=entry.get("note", ""),
            provenance=cls._provenance_from_entry(entry),
            requires_human_review=True,
        )

    @staticmethod
    def _provenance_from_entry(entry: dict[str, Any]) -> ProvenanceEvidence:
        raw = entry.get("provenance", {})
        if not isinstance(raw, dict):
            raw = {}
        def evidence_values(key: str, legacy_key: str | None = None) -> tuple[Any, ...]:
            values = raw.get(key, entry.get(legacy_key, ()) if legacy_key else ())
            if isinstance(values, str):
                return (values,)
            if isinstance(values, (list, tuple)):
                # Preserve malformed values so a claimed verified record cannot
                # become valid merely by silently dropping an invalid value.
                return tuple(values)
            return ()

        paths = evidence_values("implementation_paths", "implementation_evidence")
        test_evidence = evidence_values("test_evidence")
        runtime_evidence = evidence_values("runtime_evidence")
        state = raw.get("state", entry.get("evidence_state", "unknown"))
        try:
            evidence_state = EvidenceState(state)
        except ValueError:
            evidence_state = EvidenceState.UNKNOWN
        canonical_source = raw.get("canonical_source", entry.get("canonical_source"))
        source_revision = raw.get("source_revision", entry.get("source_revision"))
        license_snapshot = raw.get("license_snapshot", entry.get("license_snapshot"))
        rollback_handle = raw.get("rollback_handle", entry.get("rollback_handle"))
        def nonempty_text(value: Any) -> bool:
            return isinstance(value, str) and bool(value.strip())

        def nonempty_evidence(values: tuple[Any, ...]) -> bool:
            return bool(values) and all(nonempty_text(value) for value in values)

        complete_evidence = (
            nonempty_text(canonical_source)
            and nonempty_text(source_revision)
            and nonempty_text(license_snapshot)
            and nonempty_evidence(paths)
            and nonempty_evidence(test_evidence)
            and nonempty_evidence(runtime_evidence)
            and nonempty_text(rollback_handle)
        )
        if (
            evidence_state is EvidenceState.VERIFIED
            and not complete_evidence
        ) or (
            evidence_state is EvidenceState.RECORDED
            and not (
                nonempty_text(canonical_source)
                or nonempty_text(source_revision)
                or nonempty_text(license_snapshot)
                or nonempty_evidence(paths)
                or nonempty_evidence(test_evidence)
                or nonempty_evidence(runtime_evidence)
                or nonempty_text(rollback_handle)
            )
        ):
            evidence_state = EvidenceState.UNKNOWN
        return ProvenanceEvidence(
            canonical_source=canonical_source,
            source_revision=source_revision,
            license_snapshot=license_snapshot,
            implementation_paths=paths,
            test_evidence=test_evidence,
            runtime_evidence=runtime_evidence,
            rollback_handle=rollback_handle,
            state=evidence_state,
        )

    @staticmethod
    def _normalize_absorption_mode(raw: str) -> AbsorptionMode:
        mapping: dict[str, AbsorptionMode] = {
            "参考/候选Adapter": AbsorptionMode.REFERENCE_CANDIDATE,
            "参考/候选": AbsorptionMode.REFERENCE_CANDIDATE,
            "adapter": AbsorptionMode.ADAPTER,
            "adapter_candidate": AbsorptionMode.ADAPTER,
            "direct_dependency": AbsorptionMode.DIRECT_DEPENDENCY,
            "licensed_port": AbsorptionMode.LICENSED_PORT,
            "selective_licensed_port": AbsorptionMode.LICENSED_PORT,
            "independent_reimplementation": AbsorptionMode.INDEPENDENT_REIMPLEMENTATION,
            "algorithm_reference": AbsorptionMode.ALGORITHM_REFERENCE,
            "ux_reference": AbsorptionMode.UX_REFERENCE,
            "research_only": AbsorptionMode.RESEARCH_ONLY,
            "rejected": AbsorptionMode.REJECTED,
        }
        return mapping.get(raw, AbsorptionMode.REFERENCE_CANDIDATE)

    @staticmethod
    def _normalize_status(raw: str) -> ProjectStatus:
        mapping: dict[str, ProjectStatus] = {
            "candidate": ProjectStatus.CANDIDATE,
            "integrated_unreviewed": ProjectStatus.INTEGRATED,
        }
        return mapping.get(raw, ProjectStatus.CANDIDATE)


def validate_registry(entries: list[dict[str, Any]]) -> tuple[list[RegistryEntryV2], list[str]]:
    """Validate and migrate a registry payload, returning entries and errors."""
    migrated: list[RegistryEntryV2] = []
    errors: list[str] = []
    seen_ids: set[str] = set()

    for i, entry in enumerate(entries):
        asset_id = entry.get("project_id", entry.get("asset_id", ""))
        if not asset_id:
            errors.append(f"entry [{i}]: missing asset_id/project_id")
            continue
        if asset_id in seen_ids:
            errors.append(f"entry [{i}]: duplicate asset_id {asset_id}")
            continue
        seen_ids.add(asset_id)
        try:
            migrated.append(RegistryEntryV2.from_v1(entry))
        except Exception as exc:
            errors.append(f"entry [{i}] ({asset_id}): {exc}")

    return migrated, errors


def validate_registry_ledger_pair(
    registry_entries: list[dict[str, Any]], ledger_entries: list[dict[str, Any]]
) -> list[str]:
    """Check identity and status boundaries without upgrading any candidate."""
    errors: list[str] = []
    def index_entries(entries: list[dict[str, Any]], label: str) -> dict[str, dict[str, Any]]:
        indexed: dict[str, dict[str, Any]] = {}
        for index, entry in enumerate(entries):
            project_id = entry.get("project_id")
            if not isinstance(project_id, str) or not project_id:
                errors.append(f"{label} entry [{index}]: project_id must be non-empty string")
            elif project_id in indexed:
                errors.append(f"{label} entry [{index}]: duplicate project_id {project_id}")
            else:
                indexed[project_id] = entry
        return indexed

    registry_by_id = index_entries(registry_entries, "registry")
    ledger_by_id = index_entries(ledger_entries, "ledger")
    if errors:
        return errors
    if set(registry_by_id) != set(ledger_by_id):
        errors.append("registry and ledger project_id sets differ")
        return errors
    shared_fields = (
        "name",
        "category",
        "recommended_target",
        "absorption_mode",
        "risk_policy",
        "note",
    )
    for project_id, source in registry_by_id.items():
        ledger = ledger_by_id[project_id]
        for field_name in (*shared_fields, "status"):
            ledger_field = "source_status" if field_name == "status" else field_name
            if field_name not in source or ledger_field not in ledger:
                errors.append(f"{project_id}: missing identity field: {field_name}")
            elif source[field_name] != ledger[ledger_field]:
                errors.append(f"{project_id}: shared field differs: {field_name}")
        execution_state = ledger.get("execution_state")
        if not isinstance(execution_state, str) or execution_state not in {
            "implemented",
            "adapter_contract_pending",
            "deferred_review",
            "reference_only",
        }:
            errors.append(f"{project_id}: invalid execution_state {execution_state!r}")
        if execution_state == "implemented" and not ledger.get("implementation_evidence"):
            errors.append(f"{project_id}: implemented entry lacks implementation_evidence")
    return errors
