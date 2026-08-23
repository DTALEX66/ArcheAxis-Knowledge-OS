from __future__ import annotations

import sqlite3
from contextlib import closing
from hashlib import sha256

import pytest


def _store_bundle(database, bundle_id: str, *, decision: str | None) -> str:
    from app.evidence.ledger import (
        BundleReview,
        EvidenceBundleDraft,
        EvidenceBundleEntry,
        review_bundle,
        store_bundle,
    )

    entries = [
        EvidenceBundleEntry(
            entry_id=f"{bundle_id}-a",
            relation_kind="supports",
            raw_sha256=sha256(f"{bundle_id}-a".encode()).hexdigest(),
            source_revision="2026-07-20T15:00:00Z",
            anchor={"page": 1, "quote": "first independent source"},
            source_lineage="publisher-a",
            source_kind="document",
            scope="research",
            rights="cc-by-4.0",
        ),
        EvidenceBundleEntry(
            entry_id=f"{bundle_id}-b",
            relation_kind="supports",
            raw_sha256=sha256(f"{bundle_id}-b".encode()).hexdigest(),
            source_revision="2026-07-20T15:00:00Z",
            anchor={"page": 2, "quote": "second independent source"},
            source_lineage="publisher-b",
            source_kind="document",
            scope="research",
            rights="cc-by-4.0",
        ),
    ]
    store_bundle(
        EvidenceBundleDraft(bundle_id=bundle_id, claim_id="claim-version", entries=entries),
        db_path=database,
    )
    if decision is not None:
        review_bundle(
            BundleReview(
                review_id=f"{bundle_id}-review",
                bundle_id=bundle_id,
                decision=decision,
                reviewer_id="reviewer-1",
                rationale="two independent source lineages reviewed",
                reviewed_at="2026-07-20T15:00:00Z",
            ),
            db_path=database,
        )
    return bundle_id


def test_candidate_versions_preserve_parent_and_open_conflict_review(tmp_path):
    from app.knowledge.promotion import (
        ResearchKnowledgeApproval,
        promote_research_package_to_candidates,
    )
    from app.knowledge.versioning import (
        KnowledgeVersionProposal,
        register_candidate_knowledge_version,
    )
    from shared.migration_runner import MigrationOperator
    from tests.test_phase4_research_github import _prepare_research_schema, _transport

    database = tmp_path / "versioning.sqlite"
    _prepare_research_schema(database)
    with closing(sqlite3.connect(database)) as connection:
        connection.commit()
    MigrationOperator(db_path=database, backup_dir=tmp_path / "backups").apply(
        "knowledge-governance.sqlite"
    )

    from app.facades.research import research_github_repository

    graph = research_github_repository(
        "https://github.com/octo/loop-os", fetcher=_transport(), db_path=database
    )
    receipt = promote_research_package_to_candidates(
        ResearchKnowledgeApproval(
            approval_id="approve-versioning",
            package_id=graph.package.package_id,
            reviewer_id="reviewer-1",
            decision="approved",
            rationale="candidate is reviewable",
            reviewed_at="2026-07-20T15:00:00Z",
        ),
        db_path=database,
    )
    claim_unit = next(unit for unit in receipt.units if unit.unit_type == "research_claim")
    evidence_bundle_id = _store_bundle(database, "bundle-versioning", decision="verified")

    with pytest.raises(ValueError, match="human review"):
        register_candidate_knowledge_version(
            KnowledgeVersionProposal(
                proposal_id="version-unreviewed",
                unit_id=claim_unit.unit_id,
                canonical_key="github:acme/alpha:claim:unreviewed",
                content={"statement": "unreviewed evidence cannot register"},
                evidence_bundle_id=_store_bundle(database, "bundle-unreviewed", decision=None),
                reviewer_id="reviewer-1",
                reviewed_at="2026-07-20T15:00:30Z",
            ),
            db_path=database,
        )

    first = register_candidate_knowledge_version(
        KnowledgeVersionProposal(
            proposal_id="version-1",
            unit_id=claim_unit.unit_id,
            canonical_key="github:acme/alpha:claim:overview",
            parent_version_id=None,
            content={"statement": "alpha provides initial behavior"},
            evidence_bundle_id=evidence_bundle_id,
            reviewer_id="reviewer-1",
            reviewed_at="2026-07-20T15:01:00Z",
        ),
        db_path=database,
    )
    conflict = register_candidate_knowledge_version(
        KnowledgeVersionProposal(
            proposal_id="version-2",
            unit_id=claim_unit.unit_id,
            canonical_key="github:acme/alpha:claim:overview",
            parent_version_id=first.version_id,
            content={"statement": "alpha provides changed behavior"},
            evidence_bundle_id=evidence_bundle_id,
            reviewer_id="reviewer-2",
            reviewed_at="2026-07-20T15:02:00Z",
        ),
        db_path=database,
    )

    assert first.lifecycle_status == "candidate"
    assert conflict.lifecycle_status == "conflict"
    assert conflict.parent_version_id == first.version_id
    assert conflict.conflict_review_id

    with closing(sqlite3.connect(database)) as connection:
        old = connection.execute(
            "SELECT lifecycle_status, content_json, provenance_json FROM knowledge_candidate_versions_v1 WHERE id=?",
            (first.version_id,),
        ).fetchone()
        review = connection.execute(
            "SELECT status, prior_version_id, proposed_version_id FROM knowledge_candidate_conflict_reviews_v1 WHERE id=?",
            (conflict.conflict_review_id,),
        ).fetchone()

    assert old[:2] == ("candidate", '{"statement":"alpha provides initial behavior"}')
    assert '"evidence_bundle_id":"bundle-versioning"' in old[2]
    assert '"evidence_bundle_fingerprint":"' in old[2]
    assert '"evidence_review_decision":"verified"' in old[2]
    assert review == ("open", first.version_id, conflict.version_id)


def test_deprecating_candidate_version_preserves_history_and_writes_one_event(tmp_path):
    from app.facades.research import research_github_repository
    from app.knowledge.promotion import (
        ResearchKnowledgeApproval,
        promote_research_package_to_candidates,
    )
    from app.knowledge.versioning import (
        KnowledgeVersionDeprecation,
        KnowledgeVersionProposal,
        deprecate_candidate_knowledge_version,
        register_candidate_knowledge_version,
    )
    from shared.migration_runner import MigrationOperator
    from tests.test_phase4_research_github import _prepare_research_schema, _transport

    database = tmp_path / "deprecate-version.sqlite"
    _prepare_research_schema(database)
    MigrationOperator(db_path=database, backup_dir=tmp_path / "backups").apply("knowledge-governance.sqlite")
    graph = research_github_repository("https://github.com/octo/loop-os", fetcher=_transport(), db_path=database)
    promotion = promote_research_package_to_candidates(ResearchKnowledgeApproval(approval_id="approve-deprecate", package_id=graph.package.package_id, reviewer_id="reviewer-1", decision="approved", rationale="reviewed", reviewed_at="2026-07-20T15:00:00Z"), db_path=database)
    unit = next(item for item in promotion.units if item.unit_type == "research_claim")
    evidence_bundle_id = _store_bundle(
        database, "bundle-deprecate", decision="not_verifiable"
    )
    version = register_candidate_knowledge_version(KnowledgeVersionProposal(proposal_id="deprecate-v1", unit_id=unit.unit_id, canonical_key="github:octo/loop-os:claim:overview", content={"statement": "keep history"}, evidence_bundle_id=evidence_bundle_id, reviewer_id="reviewer-1", reviewed_at="2026-07-20T15:01:00Z"), db_path=database)
    request = KnowledgeVersionDeprecation(approval_id="deprecate-v1-approval", version_id=version.version_id, reviewer_id="reviewer-2", rationale="superseded evidence", reviewed_at="2026-07-20T15:02:00Z")
    deprecate_candidate_knowledge_version(request, db_path=database)
    deprecate_candidate_knowledge_version(request, db_path=database)

    with closing(sqlite3.connect(database)) as connection:
        row = connection.execute("SELECT lifecycle_status, parent_version_id, content_json FROM knowledge_candidate_versions_v1 WHERE id=?", (version.version_id,)).fetchone()
        events = connection.execute("SELECT COUNT(*) FROM knowledge_candidate_governance_events_v1 WHERE approval_id=? AND decision='deprecated'", (request.approval_id,)).fetchone()[0]
    assert row == ("deprecated", None, '{"statement":"keep history"}')
    assert events == 1
