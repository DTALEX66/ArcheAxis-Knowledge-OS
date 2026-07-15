"""Adapters between canonical claims and the current caller-supplied verifier."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from app.adapters.taskpack import ContractMappingError
from app.contracts.v1 import ClaimV1
from shared.evidence_verification import verification_status


def bind_legacy_evidence(
    claim: ClaimV1, evidence: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Bind legacy evidence dictionaries to one claim without mutating either side."""

    bound: list[dict[str, Any]] = []
    for item in evidence:
        if not isinstance(item, dict):
            raise ContractMappingError("legacy evidence item must be a dictionary")
        existing_claim_id = item.get("claim_id")
        if existing_claim_id and str(existing_claim_id) != claim.claim_id:
            raise ContractMappingError("evidence claim_id conflicts with canonical claim")
        copied = deepcopy(item)
        copied["claim_id"] = claim.claim_id
        bound.append(copied)
    return bound


def verify_with_legacy_evidence(
    claim: ClaimV1, evidence: list[dict[str, Any]]
) -> dict[str, Any]:
    """Use the legacy verifier only for caller-supplied, human-reviewed claims."""

    if claim.provenance_status != "caller_supplied" or claim.status == "verified":
        raise ContractMappingError(
            "server-owned claim cannot enter the caller-supplied verification path"
        )
    return verification_status(bind_legacy_evidence(claim, evidence))
