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
            requires_human_review=True,
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
