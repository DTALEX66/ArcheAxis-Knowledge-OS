from __future__ import annotations

import sqlite3
from contextlib import closing


def test_reviewed_candidate_claim_creates_candidate_learning_artifact_only(tmp_path):
    from app.facades.research import research_github_repository
    from app.knowledge.learning_artifact import (
        KnowledgeLearningArtifactApproval,
        create_candidate_learning_artifact,
    )
    from app.knowledge.promotion import (
        ResearchKnowledgeApproval,
        promote_research_package_to_candidates,
    )
    from shared.migration_runner import MigrationOperator
    from tests.test_phase4_research_github import _prepare_research_schema, _transport

    database = tmp_path / "knowledge-artifact.sqlite"
    _prepare_research_schema(database)
    MigrationOperator(db_path=database, backup_dir=tmp_path / "backups").apply(
        "knowledge-governance.sqlite"
    )
    graph = research_github_repository(
        "https://github.com/octo/loop-os", fetcher=_transport(), db_path=database
    )
    promotion = promote_research_package_to_candidates(
        ResearchKnowledgeApproval(
            approval_id="approve-artifact-source",
            package_id=graph.package.package_id,
            reviewer_id="reviewer-1",
            decision="approved",
            rationale="reviewed research candidate",
            reviewed_at="2026-07-20T16:00:00Z",
        ),
        db_path=database,
    )
    claim = next(unit for unit in promotion.units if unit.unit_type == "research_claim")

    artifact = create_candidate_learning_artifact(
        KnowledgeLearningArtifactApproval(
            approval_id="approve-learning-artifact",
            unit_id=claim.unit_id,
            reviewer_id="reviewer-2",
            rationale="approved for learning candidate generation",
            reviewed_at="2026-07-20T16:01:00Z",
        ),
        db_path=database,
    )

    assert artifact.status == "candidate"
    assert artifact.provenance_status == "server_verified"
    assert artifact.requires_human_review is True
    assert artifact.source_record_ids
    assert artifact.cards
    with closing(sqlite3.connect(database)) as connection:
        persisted = connection.execute(
            "SELECT status, source_unit_id FROM knowledge_candidate_learning_artifacts_v1"
        ).fetchone()
        legacy_cards = connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name IN ('cards', 'reviews')"
        ).fetchall()
    assert persisted == ("candidate", claim.unit_id)
    assert legacy_cards == []
