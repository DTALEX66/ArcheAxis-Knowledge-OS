from __future__ import annotations

import json
import sqlite3


def test_reviewed_artifact_projects_cards_only_after_explicit_approval(tmp_path):
    from app.knowledge.learning_artifact import approve_artifact_cards
    from shared.migration_runner import MigrationOperator
    from tests.test_phase4_research_github import _prepare_research_schema

    database = tmp_path / "cards.sqlite"
    _prepare_research_schema(database)
    operator = MigrationOperator(db_path=database, backup_dir=tmp_path / "backups")
    operator.apply("core.sqlite")
    operator.apply("knowledge-governance.sqlite")
    artifact = {
        "schema_version": "1.0.0", "artifact_id": "artifact-1", "artifact_type": "enhancement_bundle",
        "source_record_ids": ["source-1"], "summary": {},
        "cards": [{"front": "Claim", "back": "Evidence", "source_unit_id": "unit-1"}], "quality": {},
        "status": "candidate", "provenance_status": "server_verified", "requires_human_review": True, "created_at": "2026-07-20T00:00:00Z",
    }
    with sqlite3.connect(database) as connection:
        connection.execute("INSERT INTO knowledge_candidate_learning_artifacts_v1 VALUES (?, ?, ?, ?, ?, ?, 'candidate', ?)", ("artifact-1", "unit-1", "approval-1", "reviewer-1", "candidate", json.dumps(artifact), "2026-07-20T00:00:00Z"))
        connection.commit()
    cards = approve_artifact_cards("artifact-1", reviewer_id="reviewer-2", reviewed_at="2026-07-20T00:01:00Z", db_path=database)
    assert cards[0]["review_status"] == "draft"
    with sqlite3.connect(database) as connection:
        assert connection.execute("SELECT title, content FROM kb_cards").fetchone() == ("Claim", "Evidence")
