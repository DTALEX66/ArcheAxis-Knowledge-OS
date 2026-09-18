"""Explicit human-review projection from quarantined research to candidate knowledge."""
from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from dataclasses import dataclass

from app.adapters.taskpack import ContractMappingError
from app.contracts.v1 import (
    CONTRACT_VERSION,
    ClaimV1,
    EvidenceV1,
    KnowledgeUnitV1,
    RelationV1,
    ResearchPackageV1,
    SourceRecordV1,
)
from shared.research_store import GovernanceFinding, SourceProvenanceRecord


@dataclass(frozen=True)
class ResearchKnowledgeCandidateProjection:
    """Candidate-only graph projection attributable to one human review decision."""

    package_id: str
    review_id: str
    reviewer_id: str
    decided_at: str
    rationale: str
    units: list[KnowledgeUnitV1]
    relations: list[RelationV1]


def _stable_id(prefix: str, *parts: str) -> str:
    encoded = json.dumps(parts, ensure_ascii=True, separators=(",", ":")).encode()
    return f"{prefix}_{hashlib.sha256(encoded).hexdigest()[:24]}"


def _candidate_properties(
    *,
    package: ResearchPackageV1,
    provenance: SourceProvenanceRecord,
    review_id: str,
    reviewer_id: str,
    decided_at: str,
    rationale: str,
    payload_type: str,
    payload: dict[str, object],
) -> dict[str, object]:
    return {
        "candidate_status": "candidate",
        "requires_human_review": True,
        "package_id": package.package_id,
        "package_provenance_status": package.provenance_status,
        "package_verification_status": package.verification_status,
        "source_group_id": provenance.source_group_id,
        "canonical_url": provenance.canonical_url,
        "review_id": review_id,
        "reviewer_id": reviewer_id,
        "review_decided_at": decided_at,
        "review_rationale": rationale,
        "payload_type": payload_type,
        "payload": payload,
    }


def _validate_input(
    *,
    package: ResearchPackageV1,
    sources: Sequence[SourceRecordV1],
    source_provenance: Sequence[SourceProvenanceRecord],
    claims: Sequence[ClaimV1],
    evidence: Sequence[EvidenceV1],
    findings: Sequence[GovernanceFinding],
    review_id: str,
    reviewer_id: str,
    decided_at: str,
    rationale: str,
) -> dict[str, SourceProvenanceRecord]:
    if not review_id or not reviewer_id or not decided_at or not rationale:
        raise ContractMappingError("human review identity, timestamp, and rationale are required")
    if (
        package.status != "candidate"
        or package.provenance_status != "caller_supplied"
        or package.verification_status != "caller_supplied_candidate"
        or not package.requires_human_review
    ):
        raise ContractMappingError("only quarantined candidate research can be projected")
    if [source.source_id for source in sources] != package.source_record_ids:
        raise ContractMappingError("package source IDs do not match projection sources")
    if [claim.claim_id for claim in claims] != package.claim_ids:
        raise ContractMappingError("package claim IDs do not match projection claims")
    if [item.evidence_id for item in evidence] != package.evidence_ids:
        raise ContractMappingError("package evidence IDs do not match projection evidence")
    provenance_by_source = {item.source_id: item for item in source_provenance}
    if set(provenance_by_source) != set(package.source_record_ids):
        raise ContractMappingError("source provenance must match every package source")
    if any(item.package_id != package.package_id for item in findings):
        raise ContractMappingError("finding references another research package")
    if any(source.quarantine_status != "candidate" for source in sources):
        raise ContractMappingError("only quarantined sources can be projected")
    if any(claim.requires_human_review is not True for claim in claims):
        raise ContractMappingError("research claims must retain human-review requirement")
    return provenance_by_source


def project_approved_research_package(
    *,
    package: ResearchPackageV1,
    sources: Sequence[SourceRecordV1],
    source_provenance: Sequence[SourceProvenanceRecord],
    claims: Sequence[ClaimV1],
    evidence: Sequence[EvidenceV1],
    findings: Sequence[GovernanceFinding],
    review_id: str,
    reviewer_id: str,
    decided_at: str,
    rationale: str,
) -> ResearchKnowledgeCandidateProjection:
    """Project a human-approved package to candidates, never verified/active knowledge."""

    provenance_by_source = _validate_input(
        package=package,
        sources=sources,
        source_provenance=source_provenance,
        claims=claims,
        evidence=evidence,
        findings=findings,
        review_id=review_id,
        reviewer_id=reviewer_id,
        decided_at=decided_at,
        rationale=rationale,
    )
    source_unit_ids: dict[str, str] = {}
    claim_unit_ids: dict[str, str] = {}
    units: list[KnowledgeUnitV1] = []
    relations: list[RelationV1] = []

    for source in sources:
        provenance = provenance_by_source[source.source_id]
        unit_id = _stable_id("knowledge_source_candidate", package.package_id, source.source_id)
        source_unit_ids[source.source_id] = unit_id
        units.append(
            KnowledgeUnitV1(
                schema_version=CONTRACT_VERSION,
                unit_id=unit_id,
                unit_type="research_source_candidate",
                properties=_candidate_properties(
                    package=package,
                    provenance=provenance,
                    review_id=review_id,
                    reviewer_id=reviewer_id,
                    decided_at=decided_at,
                    rationale=rationale,
                    payload_type="source",
                    payload=source.model_dump(),
                ),
                graph_name="research_knowledge_candidates",
                created_at=decided_at,
            )
        )

    for claim in claims:
        provenance = provenance_by_source[claim.source_record_ids[0]]
        unit_id = _stable_id("knowledge_claim_candidate", package.package_id, claim.claim_id)
        claim_unit_ids[claim.claim_id] = unit_id
        units.append(
            KnowledgeUnitV1(
                schema_version=CONTRACT_VERSION,
                unit_id=unit_id,
                unit_type="research_claim_candidate",
                properties=_candidate_properties(
                    package=package,
                    provenance=provenance,
                    review_id=review_id,
                    reviewer_id=reviewer_id,
                    decided_at=decided_at,
                    rationale=rationale,
                    payload_type="claim",
                    payload=claim.model_dump(),
                ),
                graph_name="research_knowledge_candidates",
                created_at=decided_at,
            )
        )
        for source_id in claim.source_record_ids:
            relations.append(
                RelationV1(
                    schema_version=CONTRACT_VERSION,
                    relation_id=_stable_id(
                        "knowledge_relation_candidate",
                        package.package_id,
                        claim.claim_id,
                        source_id,
                        "supported_by_candidate",
                    ),
                    source_unit_id=unit_id,
                    target_unit_id=source_unit_ids[source_id],
                    relation_type="supported_by_candidate",
                    weight=1.0,
                    graph_name="research_knowledge_candidates",
                    created_at=decided_at,
                )
            )

    for item in evidence:
        claim_unit_id = claim_unit_ids[item.claim_id]
        source = next(source for source in sources if source.source_locator == item.source_locator)
        provenance = provenance_by_source[source.source_id]
        evidence_unit_id = _stable_id("knowledge_evidence_candidate", package.package_id, item.evidence_id)
        units.append(
            KnowledgeUnitV1(
                schema_version=CONTRACT_VERSION,
                unit_id=evidence_unit_id,
                unit_type="research_evidence_candidate",
                properties=_candidate_properties(
                    package=package,
                    provenance=provenance,
                    review_id=review_id,
                    reviewer_id=reviewer_id,
                    decided_at=decided_at,
                    rationale=rationale,
                    payload_type="evidence",
                    payload=item.model_dump(),
                ),
                graph_name="research_knowledge_candidates",
                created_at=decided_at,
            )
        )
        relations.append(
            RelationV1(
                schema_version=CONTRACT_VERSION,
                relation_id=_stable_id(
                    "knowledge_relation_candidate",
                    package.package_id,
                    item.evidence_id,
                    item.claim_id,
                    "evidenced_by_candidate",
                ),
                source_unit_id=claim_unit_id,
                target_unit_id=evidence_unit_id,
                relation_type="evidenced_by_candidate",
                weight=1.0,
                graph_name="research_knowledge_candidates",
                created_at=decided_at,
            )
        )

    return ResearchKnowledgeCandidateProjection(
        package_id=package.package_id,
        review_id=review_id,
        reviewer_id=reviewer_id,
        decided_at=decided_at,
        rationale=rationale,
        units=units,
        relations=relations,
    )
