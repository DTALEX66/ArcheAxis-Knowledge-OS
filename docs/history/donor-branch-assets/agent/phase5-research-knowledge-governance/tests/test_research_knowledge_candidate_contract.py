from __future__ import annotations


def test_explicit_human_approval_projects_research_only_to_candidate_knowledge():
    from app.adapters.research_knowledge import project_approved_research_package
    from app.contracts.v1 import (
        ClaimV1,
        EvidenceV1,
        ResearchPackageV1,
        SourceRecordV1,
    )
    from shared.research_store import GovernanceFinding, SourceProvenanceRecord

    source = SourceRecordV1(
        schema_version="1.0.0",
        source_id="source-001",
        title="Repository metadata",
        content="A governed research workflow.",
        source_locator="https://api.github.com/repos/octo/loop-os",
        tags=["github"],
        provenance_status="unverified",
        quarantine_status="candidate",
        created_at="2026-07-18T00:00:00Z",
    )
    claim = ClaimV1(
        schema_version="1.0.0",
        claim_id="claim-001",
        statement="The repository describes a governed research workflow.",
        source_record_ids=[source.source_id],
        status="candidate",
        provenance_status="caller_supplied",
        requires_human_review=True,
        created_at="2026-07-18T00:00:00Z",
    )
    evidence = EvidenceV1(
        schema_version="1.0.0",
        evidence_id="evidence-001",
        claim_id=claim.claim_id,
        matched_term="governed research workflow",
        source_locator=source.source_locator,
        location="metadata.description",
        asset_locator="sha256:fixture",
        kind="api",
        context="A governed research workflow.",
        status="matched",
        provenance_status="caller_supplied",
        requires_human_review=True,
    )
    package = ResearchPackageV1(
        schema_version="1.0.0",
        package_id="research_package_001",
        source_record_ids=[source.source_id],
        claim_ids=[claim.claim_id],
        evidence_ids=[evidence.evidence_id],
        independent_source_count=1,
        conflicts=[],
        unknowns=[],
        risks=["single source group"],
        verification_status="caller_supplied_candidate",
        status="candidate",
        provenance_status="caller_supplied",
        requires_human_review=True,
        created_at="2026-07-18T00:00:00Z",
    )
    provenance = SourceProvenanceRecord(
        source_id=source.source_id,
        canonical_url="https://github.com/octo/loop-os",
        source_group_id="github:octo/loop-os",
        source_locator=source.source_locator,
        retrieved_at="2026-07-18T00:00:00Z",
        content_hash="sha256:fixture",
        content_type="application/json",
        media_type="application/json",
        byte_length=len(source.content.encode()),
        collector_identity="github-api-v1",
        extractor_identity="github-metadata-json-v1",
        payload_role="metadata",
    )
    finding = GovernanceFinding(
        finding_id="finding-001",
        package_id=package.package_id,
        finding_type="risk",
        detail="single source group",
        severity="medium",
        created_at="2026-07-18T00:00:00Z",
    )

    projection = project_approved_research_package(
        package=package,
        sources=[source],
        source_provenance=[provenance],
        claims=[claim],
        evidence=[evidence],
        findings=[finding],
        review_id="review-001",
        reviewer_id="human-reviewer",
        decided_at="2026-07-18T01:00:00Z",
        rationale="Approve only as a governed candidate.",
    )

    assert projection.package_id == package.package_id
    assert projection.review_id == "review-001"
    assert {unit.properties["candidate_status"] for unit in projection.units} == {"candidate"}
    assert all(unit.properties["requires_human_review"] is True for unit in projection.units)
    assert all(unit.properties["package_id"] == package.package_id for unit in projection.units)
    assert all(unit.properties["reviewer_id"] == "human-reviewer" for unit in projection.units)
    assert all(unit.properties["source_group_id"] == "github:octo/loop-os" for unit in projection.units)
    assert {relation.relation_type for relation in projection.relations} == {
        "supported_by_candidate",
        "evidenced_by_candidate",
    }
