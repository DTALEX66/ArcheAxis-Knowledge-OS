"""Governed assembly of canonical research packages."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

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
    source_id_by_locator = {source.source_locator: source.source_id for source in sources}
    if len(source_id_by_locator) != len(sources):
        raise ContractMappingError("duplicate source locators")
    claims_by_id = {claim.claim_id: claim for claim in claims}
    for claim in claims:
        unknown_sources = set(claim.source_record_ids) - known_sources
        if unknown_sources:
            raise ContractMappingError(
                f"claim {claim.claim_id!r} references unknown source IDs: {sorted(unknown_sources)}"
            )
    for item in evidence:
        if item.claim_id not in known_claims:
            raise ContractMappingError(
                f"evidence {item.evidence_id!r} references unknown claim {item.claim_id!r}"
            )
        source_id = source_id_by_locator.get(item.source_locator)
        if source_id is None:
            raise ContractMappingError(
                f"evidence {item.evidence_id!r} references unknown source locator "
                f"{item.source_locator!r}"
            )
        if source_id not in claims_by_id[item.claim_id].source_record_ids:
            raise ContractMappingError(
                f"evidence {item.evidence_id!r} source is not among its claim sources"
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
    source_group_ids_by_locator: Mapping[str, str] | None = None,
) -> ResearchPackageV1:
    """Build a caller-supplied candidate without promoting it to verified truth."""

    validate_research_bindings(sources, claims, evidence)
    summary = verification_status([to_legacy_verification_evidence(item) for item in evidence])
    independent_source_count = summary["independent_source_count"]
    if source_group_ids_by_locator is not None:
        missing = sorted(
            {
                item.source_locator
                for item in evidence
                if item.status == "matched"
                and item.source_locator not in source_group_ids_by_locator
            }
        )
        if missing:
            raise ContractMappingError(f"source group mapping missing evidence locators: {missing}")
        independent_source_count = len(
            {
                source_group_ids_by_locator[item.source_locator]
                for item in evidence
                if item.status == "matched"
            }
        )
    try:
        return ResearchPackageV1(
            schema_version=CONTRACT_VERSION,
            package_id=package_id,
            source_record_ids=[source.source_id for source in sources],
            claim_ids=[claim.claim_id for claim in claims],
            evidence_ids=[item.evidence_id for item in evidence],
            independent_source_count=independent_source_count,
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
