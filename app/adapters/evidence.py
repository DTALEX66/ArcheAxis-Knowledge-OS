"""Adapters for text-grounded evidence and the legacy conservative verifier."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pydantic import ValidationError

from app.adapters.taskpack import ContractMappingError
from app.contracts.v1 import CONTRACT_VERSION, EvidenceV1

_RESULT_FIELDS = {"status", "terms_checked", "candidates_checked", "match", "match_count"}
_MATCH_FIELDS = {"term", "source", "location", "asset", "kind", "context", "status"}


@dataclass(frozen=True)
class EvidenceMatchProjection:
    evidence: EvidenceV1
    match_summary: dict[str, int]


def from_match_result(
    result: dict[str, Any], *, evidence_id: str, claim_id: str
) -> EvidenceMatchProjection:
    """Convert one real ``match_evidence`` result without inventing a match."""

    if result.get("status") != "matched":
        raise ContractMappingError("evidence requires a real semantic match")
    unknown_result = set(result) - _RESULT_FIELDS
    if unknown_result:
        raise ContractMappingError(f"unmapped result fields: {sorted(unknown_result)}")
    match = result.get("match")
    if not isinstance(match, dict):
        raise ContractMappingError("matched result requires a match dictionary")
    unknown_match = set(match) - _MATCH_FIELDS
    if unknown_match:
        raise ContractMappingError(f"unmapped match fields: {sorted(unknown_match)}")
    missing_match = _MATCH_FIELDS - set(match)
    if missing_match:
        raise ContractMappingError(f"missing match fields: {sorted(missing_match)}")
    if match["status"] != "matched":
        raise ContractMappingError("nested evidence status must be matched")

    try:
        evidence = EvidenceV1(
            schema_version=CONTRACT_VERSION,
            evidence_id=evidence_id,
            claim_id=claim_id,
            matched_term=match["term"],
            source_locator=match["source"],
            location=match["location"],
            asset_locator=match["asset"],
            kind=match["kind"],
            context=match["context"],
            status="matched",
            provenance_status="caller_supplied",
            requires_human_review=True,
        )
    except ValidationError as error:
        raise ContractMappingError(f"invalid matched evidence: {error}") from error

    summary_fields = ("terms_checked", "candidates_checked", "match_count")
    try:
        summary = {field: int(result[field]) for field in summary_fields}
    except (KeyError, TypeError, ValueError) as error:
        raise ContractMappingError("invalid match summary") from error
    return EvidenceMatchProjection(evidence=evidence, match_summary=summary)


def to_legacy_verification_evidence(evidence: EvidenceV1) -> dict[str, Any]:
    """Project caller-supplied evidence into the current candidate-only verifier."""

    if evidence.provenance_status != "caller_supplied":
        raise ContractMappingError(
            "server-owned evidence cannot enter the caller-supplied verification path"
        )
    return {
        "evidence_id": evidence.evidence_id,
        "claim_id": evidence.claim_id,
        "term": evidence.matched_term,
        "source": evidence.source_locator,
        "location": evidence.location,
        "asset": evidence.asset_locator,
        "kind": evidence.kind,
        "context": evidence.context,
        "status": evidence.status,
    }
