from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path


def test_knowledge_governance_owner_is_independent_and_rollback_safe(tmp_path: Path) -> None:
    from shared.migration_runner import MigrationOperator

    database = tmp_path / "phase5.sqlite"
    with closing(sqlite3.connect(database)) as connection:
        connection.execute("CREATE TABLE sentinel(id TEXT PRIMARY KEY)")
        connection.execute("INSERT INTO sentinel VALUES ('preserve')")
        connection.commit()

    operator = MigrationOperator(db_path=database, backup_dir=tmp_path / "backups")
    applied = operator.apply("knowledge-governance.sqlite")

    assert applied["state"] == "applied"
    assert applied["provenance"]["backup_sha256"]
    with closing(sqlite3.connect(database)) as connection:
        tables = {
            row[0]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        assert "knowledge_candidate_promotions_v1" in tables
        assert "knowledge_candidate_units_v1" in tables
        assert "knowledge_candidate_relations_v1" in tables
        assert "graph_entities" not in tables
        assert "graph_relations" not in tables
        assert connection.execute("SELECT id FROM sentinel").fetchone()[0] == "preserve"

    rolled_back = operator.rollback("knowledge-governance.sqlite")
    assert rolled_back["state"] == "rolled_back"
    with closing(sqlite3.connect(database)) as connection:
        tables = {
            row[0]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        assert "knowledge_candidate_promotions_v1" not in tables
        assert "knowledge_candidate_units_v1" not in tables
        assert "knowledge_candidate_relations_v1" not in tables
        assert connection.execute("SELECT id FROM sentinel").fetchone()[0] == "preserve"
