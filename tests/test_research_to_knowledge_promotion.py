from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path

from tests.test_phase4_research_github import _prepare_research_schema, _transport


def _approval(package_id: str, *, decision: str = "approved"):
    from app.knowledge.promotion import ResearchKnowledgeApproval

    return ResearchKnowledgeApproval(
        approval_id=f"approval-{decision}-{package_id}",
        package_id=package_id,
        reviewer_id="human-reviewer-001",
        decision=decision,
        rationale="Explicit human review for Phase 5 candidate-only promotion.",
        reviewed_at="2026-07-20T10:00:00+00:00",
    )


def _prepare_database(database: Path) -> None:
    from shared.migration_runner import MigrationOperator

    _prepare_research_schema(database)
    MigrationOperator(
        db_path=database,
        backup_dir=database.parent / "migration-backups",
    ).apply("knowledge-governance.sqlite")


def test_approved_research_package_promotes_only_candidate_knowledge_with_provenance(
    tmp_path: Path,
) -> None:
    from app.facades.research import research_github_repository
    from app.knowledge.promotion import promote_research_package_to_candidates

    database = tmp_path / "phase5.sqlite"
    _prepare_database(database)
    graph = research_github_repository(
        "https://github.com/octo/loop-os", fetcher=_transport(), db_path=database
    )
    approval = _approval(graph.package.package_id)

    first = promote_research_package_to_candidates(approval, db_path=database)
    second = promote_research_package_to_candidates(approval, db_path=database)

    assert first == second
    assert first.lifecycle_status == "candidate"
    assert first.package_id == graph.package.package_id
    assert first.units and first.relations
    assert {unit.unit_type for unit in first.units} == {"research_source", "research_claim"}
    assert all(unit.properties["lifecycle_status"] == "candidate" for unit in first.units)
    assert all(unit.properties["research_package_id"] == graph.package.package_id for unit in first.units)
    assert all("source_ids" in unit.properties or "source_id" in unit.properties for unit in first.units)
    assert all(relation.graph_name == "knowledge_candidate" for relation in first.relations)

    with closing(sqlite3.connect(database)) as connection:
        assert connection.execute("SELECT COUNT(*) FROM knowledge_candidate_promotions_v1").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM knowledge_candidate_units_v1").fetchone()[0] == len(first.units)
        assert (
            connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='graph_entities'"
            ).fetchone()
            is None
        )
        assert (
            connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='graph_relations'"
            ).fetchone()
            is None
        )


def test_rejected_research_package_is_audited_without_candidate_knowledge(tmp_path: Path) -> None:
    from app.facades.research import research_github_repository
    from app.knowledge.promotion import promote_research_package_to_candidates

    database = tmp_path / "rejected.sqlite"
    _prepare_database(database)
    graph = research_github_repository(
        "https://github.com/octo/loop-os", fetcher=_transport(), db_path=database
    )

    result = promote_research_package_to_candidates(
        _approval(graph.package.package_id, decision="rejected"), db_path=database
    )

    assert result.lifecycle_status == "rejected"
    assert result.units == []
    assert result.relations == []
    with closing(sqlite3.connect(database)) as connection:
        assert (
            connection.execute(
                "SELECT decision FROM knowledge_candidate_governance_events_v1"
            ).fetchone()[0]
            == "rejected"
        )
        assert connection.execute("SELECT COUNT(*) FROM knowledge_candidate_promotions_v1").fetchone()[0] == 0
        assert connection.execute("SELECT COUNT(*) FROM knowledge_candidate_units_v1").fetchone()[0] == 0


def test_approval_reads_live_wal_database(tmp_path: Path) -> None:
    from app.facades.research import research_github_repository
    from app.knowledge.promotion import promote_research_package_to_candidates

    database = tmp_path / "live-wal.sqlite"
    _prepare_database(database)
    graph = research_github_repository(
        "https://github.com/octo/loop-os", fetcher=_transport(), db_path=database
    )
    with closing(sqlite3.connect(database)) as connection:
        connection.execute("PRAGMA journal_mode=WAL")
        connection.commit()

    receipt = promote_research_package_to_candidates(
        _approval(graph.package.package_id), db_path=database
    )

    assert receipt.lifecycle_status == "candidate"
    assert receipt.package_id == graph.package.package_id
