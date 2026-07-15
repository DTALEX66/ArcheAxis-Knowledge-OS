"""Governed assembly of canonical research packages."""

from __future__ import annotations

from collections.abc import Sequence

from pydantic import ValidationError

from app.adapters.evidence import to_legacy_verification_evidence
from app.adapters.taskpack import ContractMappingError
from app.contracts.v1 import (
    CONTRACT_VERSION,
    ClaimV1,
    EvidenceV1,
    ResearchPackageV1,
    SourceRecordV1,
)
from shared.evidence_verification import verification_status


def _reject_duplicate_ids(ids: list[str], label: str) -> None:
    if len(ids) != len(set(ids)):
        raise ContractMappingError(f"duplicate {label} IDs")


def validate_research_bindings(
    sources: Sequence[SourceRecordV1],
    claims: Sequence[ClaimV1],
    evidence: Sequence[EvidenceV1],
) -> None:
    """Fail closed when canonical research objects are not fully bound."""

    source_ids = [source.source_id for source in sources]
    claim_ids = [claim.claim_id for claim in claims]
    evidence_ids = [item.evidence_id for item in evidence]
    _reject_duplicate_ids(source_ids, "source")
    _reject_duplicate_ids(claim_ids, "claim")
    _reject_duplicate_ids(evidence_ids, "evidence")

    known_sources = set(source_ids)
    known_claims = set(claim_ids)
    source_locators = {source.source_locator for source in sources}
    for claim in claims:
        unknown_sources = set(claim.source_record_ids) - known_sources
        if unknown_sources:
            raise ContractMappingError(
                f"claim {claim.claim_id!r} references unknown source IDs: "
                f"{sorted(unknown_sources)}"
            )
    for item in evidence:
        if item.claim_id not in known_claims:
            raise ContractMappingError(
                f"evidence {item.evidence_id!r} references unknown claim {item.claim_id!r}"
            )
        if item.source_locator not in source_locators:
            raise ContractMappingError(
                f"evidence {item.evidence_id!r} references unknown source locator "
                f"{item.source_locator!r}"
            )


def build_candidate_research_package(
    *,
    package_id: str,
    sources: Sequence[SourceRecordV1],
    claims: Sequence[ClaimV1],
    evidence: Sequence[EvidenceV1],
    conflicts: Sequence[str],
    unknowns: Sequence[str],
    risks: Sequence[str],
    created_at: str,
) -> ResearchPackageV1:
    """Build a caller-supplied candidate without promoting it to verified truth."""

    validate_research_bindings(sources, claims, evidence)
    summary = verification_status(
        [to_legacy_verification_evidence(item) for item in evidence]
    )
    try:
        return ResearchPackageV1(
            schema_version=CONTRACT_VERSION,
            package_id=package_id,
            source_record_ids=[source.source_id for source in sources],
            claim_ids=[claim.claim_id for claim in claims],
            evidence_ids=[item.evidence_id for item in evidence],
            independent_source_count=summary["independent_source_count"],
            conflicts=list(conflicts),
            unknowns=list(unknowns),
            risks=list(risks),
            verification_status=summary["status"],
            status="candidate",
            provenance_status="caller_supplied",
            requires_human_review=True,
            created_at=created_at,
        )
    except ValidationError as error:
        raise ContractMappingError(f"invalid research package: {error}") from error
