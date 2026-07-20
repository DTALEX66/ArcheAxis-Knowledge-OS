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
