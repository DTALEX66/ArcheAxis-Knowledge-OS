from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from tests.test_phase4_research_github import _prepare_research_schema, _transport


def _database(tmp_path: Path) -> Path:
    from shared.migration_runner import MigrationOperator

    database = tmp_path / "mcs.sqlite"
    _prepare_research_schema(database)
    operator = MigrationOperator(db_path=database, backup_dir=tmp_path / "backups")
    operator.apply("core.sqlite")
    operator.apply("knowledge-governance.sqlite")
    return database


def test_governed_closed_loop_requires_learning_approval_then_persists_mastery_candidate_and_audit(
    tmp_path: Path, monkeypatch,
) -> None:
    from app.facades.research import research_github_repository
    from app.knowledge.closed_loop import (
        approve_learning_artifact,
        audit_closed_loop,
        record_practice_evidence,
        start_learning_candidate,
    )
    from app.knowledge.promotion import (
        ResearchKnowledgeApproval,
        promote_research_package_to_candidates,
    )

    database = _database(tmp_path)
    graph = research_github_repository(
        "https://github.com/octo/loop-os", fetcher=_transport(), db_path=database
    )
    promotion = promote_research_package_to_candidates(
        ResearchKnowledgeApproval(
            approval_id="research-approval", package_id=graph.package.package_id,
            reviewer_id="reviewer-1", decision="approved", rationale="grounded", reviewed_at="2026-07-20T10:00:00Z",
        ), db_path=database,
    )
    claim = next(unit for unit in promotion.units if unit.unit_type == "research_claim")
    artifact = start_learning_candidate(
        unit_id=claim.unit_id, approval_id="learning-candidate", reviewer_id="reviewer-2",
        rationale="learning candidate", reviewed_at="2026-07-20T10:01:00Z", db_path=database,
    )

    with pytest.raises(ValueError, match="approved learning artifact"):
        record_practice_evidence(
            artifact_id=artifact.artifact_id, command_id="practice-before-approval", quality=5,
            recorded_at="2026-07-20T10:02:00Z", db_path=database,
        )

    approve_learning_artifact(
        artifact_id=artifact.artifact_id, command_id="approve-learning", reviewer_id="reviewer-3",
        reviewed_at="2026-07-20T10:03:00Z", db_path=database,
    )[0]
    for index in range(1, 4):
        result = record_practice_evidence(
            artifact_id=artifact.artifact_id, command_id=f"practice-{index}", quality=5,
            recorded_at=f"2026-07-20T10:0{3 + index}:00Z", db_path=database,
        )
    assert result.mastery_signal.is_mastered is True
    assert result.machine_knowledge.lifecycle_status == "candidate"

    with sqlite3.connect(database) as connection:
        counts_before = tuple(
            connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in ("kb_reviews", "mastery_signals_v1", "machine_knowledge_candidates_v1")
        )
    replay = record_practice_evidence(
        artifact_id=artifact.artifact_id,
        command_id="practice-3",
        quality=5,
        recorded_at="2026-07-20T11:00:00Z",
        db_path=database,
    )
    assert replay == result
    with pytest.raises(RuntimeError, match="practice command id conflicts"):
        record_practice_evidence(
            artifact_id="*",
            command_id="practice-3",
            quality=5,
            recorded_at="2026-07-20T11:00:00Z",
            db_path=database,
        )
    with sqlite3.connect(database) as connection:
        counts_after = tuple(
            connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in ("kb_reviews", "mastery_signals_v1", "machine_knowledge_candidates_v1")
        )
    assert counts_after == counts_before

    from app.knowledge import closed_loop

    def fail_machine_write(*args, **kwargs):
        raise RuntimeError("injected machine candidate failure")

    monkeypatch.setattr(
        closed_loop, "create_machine_knowledge_candidate_on_connection", fail_machine_write
    )
    with pytest.raises(RuntimeError, match="injected machine candidate failure"):
        record_practice_evidence(
            artifact_id=artifact.artifact_id,
            command_id="practice-atomic-rollback",
            quality=5,
            recorded_at="2026-07-20T11:01:00Z",
            db_path=database,
        )
    with sqlite3.connect(database) as connection:
        counts_after_failure = tuple(
            connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in ("kb_reviews", "mastery_signals_v1", "machine_knowledge_candidates_v1")
        )
    assert counts_after_failure == counts_before

    with pytest.raises(RuntimeError, match="practice command id conflicts"):
        record_practice_evidence(
            artifact_id=artifact.artifact_id,
            command_id="practice-3",
            quality=0,
            recorded_at="2026-07-20T11:00:00Z",
            db_path=database,
        )

    audit = audit_closed_loop(artifact.artifact_id, db_path=database)
    assert [event.event_type for event in audit] == [
        "learning_candidate_created", "learning_artifact_approved",
        "practice_recorded", "practice_recorded", "practice_recorded",
        "mastery_calculated", "mastery_calculated", "mastery_calculated",
        "machine_knowledge_candidate_created",
    ]
    with sqlite3.connect(database) as connection:
        assert connection.execute("SELECT COUNT(*) FROM mastery_signals_v1").fetchone()[0] == 3
