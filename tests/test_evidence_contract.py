from __future__ import annotations

import pytest
from pydantic import ValidationError

EVIDENCE_SCHEMA_ID = "https://cognitive-loop-os.local/contracts/v1/evidence.schema.json"


def _evidence(**overrides):
    from app.contracts.v1 import EvidenceV1

    payload = {
        "schema_version": "1.0.0",
        "evidence_id": "evidence-001",
        "claim_id": "claim-001",
        "matched_term": "vector search",
        "source_locator": "course.pdf",
        "location": "page:3",
        "asset_locator": "page-3.png",
        "kind": "pdf",
        "context": "vector search retrieves similar records",
        "status": "matched",
        "provenance_status": "caller_supplied",
        "requires_human_review": True,
    }
    payload.update(overrides)
    return EvidenceV1(**payload)


def test_evidence_v1_schema_is_stable_strict_and_explicit():
    from app.contracts.v1 import EvidenceV1

    schema = EvidenceV1.model_json_schema()
    payload = _evidence().model_dump()

    assert schema["$id"] == EVIDENCE_SCHEMA_ID
    assert "schema_version" in schema["required"]
    with pytest.raises(ValidationError):
        EvidenceV1(**{**payload, "schema_version": "2.0.0"})
    with pytest.raises(ValidationError):
        EvidenceV1(**{**payload, "invented": "forbidden"})
    with pytest.raises(ValidationError):
        EvidenceV1(**{**payload, "status": "verified"})
    with pytest.raises(ValidationError, match="caller_supplied evidence requires human review"):
        EvidenceV1(**{**payload, "requires_human_review": False})


def test_match_result_becomes_caller_supplied_evidence_v1():
    from app.adapters.evidence import from_match_result
    from shared.evidence_verification import match_evidence

    result = match_evidence(
        ["vector search"],
        [
            {
                "source": "course.pdf",
                "location": "page:3",
                "asset": "page-3.png",
                "kind": "pdf",
                "text": "vector search retrieves similar records",
            }
        ],
    )
    projection = from_match_result(result, evidence_id="evidence-001", claim_id="claim-001")

    assert projection.evidence == _evidence()
    assert projection.match_summary == {
        "terms_checked": 1,
        "candidates_checked": 1,
        "match_count": 1,
    }


def test_no_semantic_match_cannot_create_evidence():
    from app.adapters.evidence import from_match_result
    from app.adapters.taskpack import ContractMappingError

    with pytest.raises(ContractMappingError, match="semantic match"):
        from_match_result(
            {"status": "no_semantic_match", "terms_checked": 1, "candidates_checked": 2},
            evidence_id="evidence-001",
            claim_id="claim-001",
        )


def test_match_adapter_rejects_unknown_or_incomplete_fields():
    from app.adapters.evidence import from_match_result
    from app.adapters.taskpack import ContractMappingError

    base = {
        "status": "matched",
        "terms_checked": 1,
        "candidates_checked": 1,
        "match_count": 1,
        "match": {
            "term": "vector search",
            "source": "course.pdf",
            "location": "page:3",
            "asset": "page-3.png",
            "kind": "pdf",
            "context": "vector search retrieves similar records",
            "status": "matched",
        },
    }
    with pytest.raises(ContractMappingError, match="unmapped result fields"):
        from_match_result(
            {**base, "confidence": 1.0}, evidence_id="evidence-001", claim_id="claim-001"
        )
    with pytest.raises(ContractMappingError, match="unmapped match fields"):
        from_match_result(
            {**base, "match": {**base["match"], "confidence": 1.0}},
            evidence_id="evidence-001",
            claim_id="claim-001",
        )


def test_evidence_projects_to_legacy_verifier_without_governance_upgrade():
    from app.adapters.evidence import to_legacy_verification_evidence
    from shared.evidence_verification import verification_status

    legacy = to_legacy_verification_evidence(_evidence())
    assert legacy["claim_id"] == "claim-001"
    assert legacy["status"] == "matched"
    result = verification_status([legacy])
    assert result["status"] == "caller_supplied_candidate"
    assert result["server_verified"] is False
    assert result["requires_human_review"] is True


def test_server_verified_evidence_cannot_enter_legacy_verifier():
    from app.adapters.evidence import to_legacy_verification_evidence
    from app.adapters.taskpack import ContractMappingError

    server_owned = _evidence(provenance_status="server_verified", requires_human_review=False)
    with pytest.raises(ContractMappingError, match="caller-supplied verification path"):
        to_legacy_verification_evidence(server_owned)


def test_contracts_facade_exports_evidence_v1_and_adapters():
    from app.adapters.evidence import from_match_result, to_legacy_verification_evidence
    from app.contracts.v1 import EvidenceV1
    from app.facades import contracts

    assert contracts.EvidenceV1 is EvidenceV1
    assert contracts.from_match_result is from_match_result
    assert contracts.to_legacy_verification_evidence is to_legacy_verification_evidence
