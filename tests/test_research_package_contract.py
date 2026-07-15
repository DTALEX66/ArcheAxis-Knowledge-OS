from __future__ import annotations

import pytest
from pydantic import ValidationError

RESEARCH_PACKAGE_SCHEMA_ID = (
    "https://cognitive-loop-os.local/contracts/v1/research-package.schema.json"
)


def _package(**overrides):
    from app.contracts.v1 import ResearchPackageV1

    payload = {
        "schema_version": "1.0.0",
        "package_id": "research-package-001",
        "source_record_ids": ["source-001", "source-002"],
        "claim_ids": ["claim-001"],
        "evidence_ids": ["evidence-001", "evidence-002"],
        "independent_source_count": 2,
        "conflicts": [],
        "unknowns": ["sample size is not reported"],
        "risks": ["caller supplied provenance"],
        "verification_status": "caller_supplied_candidate",
        "status": "candidate",
        "provenance_status": "caller_supplied",
        "requires_human_review": True,
        "created_at": "2026-07-15 23:55:00",
    }
    payload.update(overrides)
    return ResearchPackageV1(**payload)


def test_research_package_v1_schema_is_stable_strict_and_explicit():
    from app.contracts.v1 import ResearchPackageV1

    schema = ResearchPackageV1.model_json_schema()
    payload = _package().model_dump()

    assert schema["$id"] == RESEARCH_PACKAGE_SCHEMA_ID
    assert "schema_version" in schema["required"]
    with pytest.raises(ValidationError):
        ResearchPackageV1(**{**payload, "schema_version": "2.0.0"})
    with pytest.raises(ValidationError):
        ResearchPackageV1(**{**payload, "invented": "forbidden"})
    with pytest.raises(ValidationError):
        ResearchPackageV1(**{**payload, "claim_ids": []})
    with pytest.raises(ValidationError):
        ResearchPackageV1(**{**payload, "evidence_ids": []})


def test_caller_supplied_package_cannot_be_verified_or_skip_review():
    with pytest.raises(ValidationError, match="verified package requires server_verified"):
        _package(status="verified")
    with pytest.raises(ValidationError, match="caller_supplied package requires human review"):
        _package(requires_human_review=False)


def test_candidate_package_is_built_from_bound_claims_and_real_evidence():
    from app.adapters.research_package import build_candidate_research_package
    from app.contracts.v1 import ClaimV1, EvidenceV1, SourceRecordV1

    sources = [
        SourceRecordV1(
            schema_version="1.0.0",
            source_id=f"source-00{index}",
            title=f"Source {index}",
            content="content",
            source_locator=locator,
            tags=[],
            provenance_status="unverified",
            quarantine_status="candidate",
            created_at="2026-07-15 23:50:00",
        )
        for index, locator in ((1, "course.pdf"), (2, "https://example.edu/course"))
    ]
    claim = ClaimV1(
        schema_version="1.0.0",
        claim_id="claim-001",
        statement="Vector search retrieves semantically similar records.",
        source_record_ids=[source.source_id for source in sources],
        status="candidate",
        provenance_status="caller_supplied",
        requires_human_review=True,
        created_at="2026-07-15 23:51:00",
    )
    evidence = [
        EvidenceV1(
            schema_version="1.0.0",
            evidence_id=f"evidence-00{index}",
            claim_id=claim.claim_id,
            matched_term="vector search",
            source_locator=source.source_locator,
            location=f"locator:{index}",
            asset_locator="",
            kind=kind,
            context="vector search retrieves semantically similar records",
            status="matched",
            provenance_status="caller_supplied",
            requires_human_review=True,
        )
        for index, (source, kind) in enumerate(
            zip(sources, ("pdf", "oer"), strict=True), start=1
        )
    ]

    package = build_candidate_research_package(
        package_id="research-package-001",
        sources=sources,
        claims=[claim],
        evidence=evidence,
        conflicts=[],
        unknowns=["sample size is not reported"],
        risks=["caller supplied provenance"],
        created_at="2026-07-15 23:55:00",
    )

    assert package == _package()


def test_research_package_rejects_evidence_for_an_unknown_claim():
    from app.adapters.research_package import build_candidate_research_package
    from app.adapters.taskpack import ContractMappingError
    from app.contracts.v1 import EvidenceV1

    evidence = EvidenceV1(
        schema_version="1.0.0",
        evidence_id="evidence-001",
        claim_id="claim-missing",
        matched_term="term",
        source_locator="source.pdf",
        location="page:1",
        asset_locator="",
        kind="pdf",
        context="term in context",
        status="matched",
        provenance_status="caller_supplied",
        requires_human_review=True,
    )
    with pytest.raises(ContractMappingError, match="unknown claim"):
        build_candidate_research_package(
            package_id="package",
            sources=[],
            claims=[],
            evidence=[evidence],
            conflicts=[],
            unknowns=[],
            risks=[],
            created_at="now",
        )


def test_research_package_rejects_claim_for_an_unknown_source():
    from app.adapters.research_package import validate_research_bindings
    from app.adapters.taskpack import ContractMappingError
    from app.contracts.v1 import ClaimV1

    claim = ClaimV1(
        schema_version="1.0.0",
        claim_id="claim-001",
        statement="statement",
        source_record_ids=["source-missing"],
        status="candidate",
        provenance_status="caller_supplied",
        requires_human_review=True,
        created_at="now",
    )
    with pytest.raises(ContractMappingError, match="unknown source"):
        validate_research_bindings([], [claim], [])


def test_research_package_rejects_duplicate_ids():
    from app.adapters.research_package import validate_research_bindings
    from app.adapters.taskpack import ContractMappingError
    from app.contracts.v1 import SourceRecordV1

    source = SourceRecordV1(
        schema_version="1.0.0",
        source_id="source-001",
        title="source",
        content="content",
        source_locator="source.pdf",
        tags=[],
        provenance_status="unverified",
        quarantine_status="candidate",
        created_at="now",
    )
    with pytest.raises(ContractMappingError, match="duplicate source IDs"):
        validate_research_bindings([source, source.model_copy(deep=True)], [], [])


def test_contracts_facade_exports_research_package_v1():
    from app.adapters.research_package import build_candidate_research_package
    from app.contracts.v1 import ResearchPackageV1
    from app.facades import contracts

    assert contracts.ResearchPackageV1 is ResearchPackageV1
    assert contracts.build_candidate_research_package is build_candidate_research_package
