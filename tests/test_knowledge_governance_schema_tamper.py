from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path

import pytest


def test_knowledge_governance_status_rejects_recorded_event_table_tamper(
    tmp_path: Path,
) -> None:
    from shared import knowledge_governance_migration
    from shared.migration_runner import MigrationOperator

    database = tmp_path / "tampered.sqlite"
    with closing(sqlite3.connect(database)):
        pass
    MigrationOperator(db_path=database, backup_dir=tmp_path / "backups").apply(
        "knowledge-governance.sqlite"
    )
    with closing(sqlite3.connect(database)) as connection:
        connection.execute("DROP TABLE knowledge_candidate_governance_events_v1")
        connection.execute(
            "CREATE TABLE knowledge_candidate_governance_events_v1 (id TEXT PRIMARY KEY)"
        )
        connection.commit()

    with pytest.raises(RuntimeError, match="knowledge governance.*schema"):
        knowledge_governance_migration.status(db_path=database)


def test_knowledge_governance_status_rejects_recorded_versioning_table_tamper(
    tmp_path: Path,
) -> None:
    from shared import knowledge_governance_migration
    from shared.migration_runner import MigrationOperator

    database = tmp_path / "tampered-versioning.sqlite"
    with closing(sqlite3.connect(database)):
        pass
    MigrationOperator(db_path=database, backup_dir=tmp_path / "backups").apply(
        "knowledge-governance.sqlite"
    )
    with closing(sqlite3.connect(database)) as connection:
        connection.execute("DROP TABLE knowledge_candidate_versions_v1")
        connection.execute("CREATE TABLE knowledge_candidate_versions_v1 (id TEXT PRIMARY KEY)")
        connection.commit()

    with pytest.raises(RuntimeError, match="knowledge governance.*schema"):
        knowledge_governance_migration.status(db_path=database)


def test_knowledge_governance_status_rejects_recorded_learning_artifact_table_tamper(
    tmp_path: Path,
) -> None:
    from shared import knowledge_governance_migration
    from shared.migration_runner import MigrationOperator

    database = tmp_path / "tampered-learning-artifact.sqlite"
    with closing(sqlite3.connect(database)):
        pass
    MigrationOperator(db_path=database, backup_dir=tmp_path / "backups").apply(
        "knowledge-governance.sqlite"
    )
    with closing(sqlite3.connect(database)) as connection:
        connection.execute("DROP TABLE knowledge_candidate_learning_artifacts_v1")
        connection.execute(
            "CREATE TABLE knowledge_candidate_learning_artifacts_v1 (id TEXT PRIMARY KEY)"
        )
        connection.commit()

    with pytest.raises(RuntimeError, match="knowledge governance.*schema"):
        knowledge_governance_migration.status(db_path=database)


def test_migration_operator_rejects_live_knowledge_governance_schema_drift(
    tmp_path: Path,
) -> None:
    from shared.migration_runner import MigrationOperator

    database = tmp_path / "operator-tampered-knowledge.sqlite"
    with closing(sqlite3.connect(database)):
        pass
    operator = MigrationOperator(db_path=database, backup_dir=tmp_path / "backups")
    operator.apply("knowledge-governance.sqlite")
    with closing(sqlite3.connect(database)) as connection:
        connection.execute("DROP INDEX idx_learning_approval_events_artifact_v1")
        connection.commit()

    status = next(
        item for item in operator.status() if item["owner"] == "knowledge-governance.sqlite"
    )
    assert status["state"] == "failed"
    assert status["provenance"]["reason"] == "live_schema_drift"
    with pytest.raises(RuntimeError, match="knowledge governance.*schema"):
        operator.apply("knowledge-governance.sqlite")


@pytest.mark.parametrize(
    "extra_sql",
    [
        "CREATE INDEX unexpected_learning_approval_index "
        "ON learning_approval_events_v1(reviewer_id)",
        "CREATE TRIGGER unexpected_learning_approval_trigger "
        "AFTER INSERT ON learning_approval_events_v1 BEGIN SELECT 1; END",
    ],
)
def test_migration_operator_rejects_extra_knowledge_owned_schema_objects(
    tmp_path: Path, extra_sql: str,
) -> None:
    from shared.migration_runner import MigrationOperator

    database = tmp_path / "operator-extra-knowledge.sqlite"
    with closing(sqlite3.connect(database)):
        pass
    operator = MigrationOperator(db_path=database, backup_dir=tmp_path / "backups")
    operator.apply("knowledge-governance.sqlite")
    with closing(sqlite3.connect(database)) as connection:
        connection.execute(extra_sql)
        connection.commit()

    status = next(
        item for item in operator.status() if item["owner"] == "knowledge-governance.sqlite"
    )
    assert status["state"] == "failed"
    assert status["provenance"]["reason"] == "live_schema_drift"
    with pytest.raises(RuntimeError, match="knowledge governance.*schema"):
        operator.apply("knowledge-governance.sqlite")


def test_partial_recorded_knowledge_schema_still_validates_each_applied_migration(
    tmp_path: Path,
) -> None:
    from shared import knowledge_governance_migration
    from shared.migration_runner import MigrationOperator

    database = tmp_path / "partial-recorded-knowledge.sqlite"
    with closing(sqlite3.connect(database)):
        pass
    MigrationOperator(db_path=database, backup_dir=tmp_path / "backups").apply(
        "knowledge-governance.sqlite"
    )
    with closing(sqlite3.connect(database)) as connection:
        connection.executescript(
            """
            DROP TABLE machine_knowledge_approval_events_v1;
            DROP TABLE learning_approval_events_v1;
            DROP TABLE knowledge_candidate_learning_artifacts_v1;
            DROP TABLE knowledge_candidate_conflict_reviews_v1;
            DROP TABLE knowledge_candidate_versions_v1;
            DELETE FROM schema_migrations WHERE version IN (7, 8, 9, 10);
            CREATE INDEX unexpected_governance_event_index
            ON knowledge_candidate_governance_events_v1(reviewer_id);
            """
        )
        connection.commit()

    with pytest.raises(RuntimeError, match="knowledge governance.*schema"):
        knowledge_governance_migration.status(db_path=database)
