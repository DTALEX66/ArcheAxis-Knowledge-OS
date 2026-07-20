from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path

import pytest

from tests.test_phase4_research_github import _prepare_research_schema, _transport


def _prepare_database(database: Path) -> None:
    from shared.migration_runner import MigrationOperator

    _prepare_research_schema(database)
    MigrationOperator(
        db_path=database,
        backup_dir=database.parent / "migration-backups",
    ).apply("knowledge-governance.sqlite")


def _approval(package_id: str, decision: str) -> object:
    from app.knowledge.promotion import ResearchKnowledgeApproval

    return ResearchKnowledgeApproval(
        approval_id=f"approval-{decision}-{package_id}",
        package_id=package_id,
        reviewer_id="human-reviewer-001",
        decision=decision,
        rationale=f"Explicit {decision} decision.",
        reviewed_at="2026-07-20T10:00:00+00:00",
    )


def test_deprecation_appends_auditable_event_and_deprecates_candidate_projection(
    tmp_path: Path,
) -> None:
    from app.facades.research import research_github_repository
    from app.knowledge.promotion import promote_research_package_to_candidates

    database = tmp_path / "deprecated.sqlite"
    _prepare_database(database)
    graph = research_github_repository(
        "https://github.com/octo/loop-os", fetcher=_transport(), db_path=database
    )
    approved = promote_research_package_to_candidates(
        _approval(graph.package.package_id, "approved"), db_path=database
    )
    deprecated = promote_research_package_to_candidates(
        _approval(graph.package.package_id, "deprecated"), db_path=database
    )

    assert deprecated.promotion_id == approved.promotion_id
    assert deprecated.lifecycle_status == "deprecated"
    assert deprecated.units and deprecated.relations
    with closing(sqlite3.connect(database)) as connection:
        events = connection.execute(
            "SELECT decision FROM knowledge_candidate_governance_events_v1 "
            "ORDER BY created_at, id"
        ).fetchall()
        assert [row[0] for row in events] == ["approved", "deprecated"]
        assert connection.execute(
            "SELECT COUNT(*) FROM knowledge_candidate_promotions_v1"
        ).fetchone()[0] == 1
        assert connection.execute(
            "SELECT COUNT(*) FROM knowledge_candidate_units_v1 "
            "WHERE lifecycle_status='deprecated'"
        ).fetchone()[0] == len(approved.units)
        assert connection.execute(
            "SELECT COUNT(*) FROM knowledge_candidate_relations_v1 "
            "WHERE lifecycle_status='deprecated'"
        ).fetchone()[0] == len(approved.relations)


def test_mid_projection_failure_leaves_no_event_or_candidate_rows(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from app.facades.research import research_github_repository
    from app.knowledge import promotion

    database = tmp_path / "rollback.sqlite"
    _prepare_database(database)
    graph = research_github_repository(
        "https://github.com/octo/loop-os", fetcher=_transport(), db_path=database
    )

    def fail_relation_write() -> None:
        raise RuntimeError("injected candidate relation failure")

    monkeypatch.setattr(promotion, "_before_candidate_relation_write", fail_relation_write)
    with pytest.raises(RuntimeError, match="injected candidate relation failure"):
        promotion.promote_research_package_to_candidates(
            _approval(graph.package.package_id, "approved"), db_path=database
        )

    with closing(sqlite3.connect(database)) as connection:
        for table in (
            "knowledge_candidate_governance_events_v1",
            "knowledge_candidate_promotions_v1",
            "knowledge_candidate_units_v1",
            "knowledge_candidate_relations_v1",
        ):
            assert connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0
