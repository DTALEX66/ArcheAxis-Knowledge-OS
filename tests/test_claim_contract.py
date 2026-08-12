from __future__ import annotations

import pytest
from pydantic import ValidationError

CLAIM_SCHEMA_ID = "https://archeaxis.local/contracts/v1/claim.schema.json"


def _claim(**overrides):
    from app.contracts.v1 import ClaimV1

    payload = {
        "schema_version": "1.0.0",
        "claim_id": "claim-001",
        "statement": "Vector search retrieves semantically similar records.",
        "source_record_ids": ["source-001"],
        "status": "candidate",
        "provenance_status": "caller_supplied",
        "requires_human_review": True,
        "created_at": "2026-07-15 23:30:00",
    }
    payload.update(overrides)
    return ClaimV1(**payload)


def test_claim_v1_schema_is_stable_strict_and_explicit():
    from app.contracts.v1 import ClaimV1

    schema = ClaimV1.model_json_schema()
    payload = _claim().model_dump()

    assert schema["$id"] == CLAIM_SCHEMA_ID
    assert "schema_version" in schema["required"]
    with pytest.raises(ValidationError):
        ClaimV1(**{key: value for key, value in payload.items() if key != "schema_version"})
    with pytest.raises(ValidationError):
        ClaimV1(**{**payload, "schema_version": "2.0.0"})
    with pytest.raises(ValidationError):
        ClaimV1(**{**payload, "invented": "forbidden"})
    with pytest.raises(ValidationError):
        ClaimV1(**{**payload, "source_record_ids": []})


def test_caller_supplied_claim_cannot_be_auto_verified_or_skip_review():
    with pytest.raises(ValidationError, match="verified claim requires server_verified"):
        _claim(status="verified")
    with pytest.raises(ValidationError, match="caller_supplied claim requires human review"):
        _claim(requires_human_review=False)


def test_verified_claim_requires_server_owned_provenance():
    verified = _claim(
        status="verified",
        provenance_status="server_verified",
        requires_human_review=False,
    )
    assert verified.status == "verified"

    with pytest.raises(ValidationError, match="verified claim requires server_verified"):
        _claim(status="verified", provenance_status="caller_supplied")


def test_legacy_evidence_binding_is_lossless_and_deeply_isolated():
    from app.adapters.claim import bind_legacy_evidence

    claim = _claim()
    evidence = [
        {
            "kind": "pdf",
            "source": "course.pdf",
            "status": "matched",
            "location": "page:3",
            "metadata": {"pages": [3]},
        }
    ]

    bound = bind_legacy_evidence(claim, evidence)

    assert bound[0] == {**evidence[0], "claim_id": claim.claim_id}
    evidence[0]["metadata"]["pages"].append(4)
    assert bound[0]["metadata"] == {"pages": [3]}
    bound[0]["metadata"]["pages"].append(5)
    assert evidence[0]["metadata"] == {"pages": [3, 4]}


def test_legacy_evidence_binding_rejects_a_different_claim_id():
    from app.adapters.claim import bind_legacy_evidence
    from app.adapters.taskpack import ContractMappingError

    with pytest.raises(ContractMappingError, match="evidence claim_id conflicts"):
        bind_legacy_evidence(
            _claim(),
            [{"claim_id": "claim-other", "source": "other.pdf", "status": "matched"}],
        )


def test_claim_verification_projection_remains_caller_supplied_candidate():
    from app.adapters.claim import verify_with_legacy_evidence

    result = verify_with_legacy_evidence(
        _claim(),
        [
            {
                "kind": "pdf",
                "source": "course.pdf",
                "status": "verified",
                "location": "page:3",
            },
            {
                "kind": "oer",
                "source": "https://example.edu/course",
                "status": "matched",
                "location": "section:2",
            },
        ],
    )

    assert result["status"] == "caller_supplied_candidate"
    assert result["claim_bound_by_caller"] is True
    assert result["server_verified"] is False
    assert result["requires_human_review"] is True


def test_server_verified_claim_cannot_be_downgraded_through_legacy_verifier():
    from app.adapters.claim import verify_with_legacy_evidence
    from app.adapters.taskpack import ContractMappingError

    verified = _claim(
        status="verified",
        provenance_status="server_verified",
        requires_human_review=False,
    )
    with pytest.raises(ContractMappingError, match="caller-supplied verification path"):
        verify_with_legacy_evidence(verified, [])


def test_contracts_facade_exports_claim_v1_and_adapters():
    from app.adapters.claim import bind_legacy_evidence, verify_with_legacy_evidence
    from app.contracts.v1 import ClaimV1
    from app.facades import contracts

    assert contracts.ClaimV1 is ClaimV1
    assert contracts.bind_legacy_evidence is bind_legacy_evidence
    assert contracts.verify_with_legacy_evidence is verify_with_legacy_evidence
