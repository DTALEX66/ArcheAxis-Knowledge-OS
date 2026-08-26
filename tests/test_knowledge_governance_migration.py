from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from pathlib import Path


def test_knowledge_governance_owner_is_independent_and_rollback_safe(tmp_path: Path) -> None:
    from shared.migration_runner import MigrationOperator

    database = tmp_path / "phase5.sqlite"
    with closing(sqlite3.connect(database)) as connection:
        connection.execute("CREATE TABLE sentinel(id TEXT PRIMARY KEY)")
        connection.execute("INSERT INTO sentinel VALUES ('preserve')")
        connection.execute("CREATE TABLE machine_knowledge(id TEXT PRIMARY KEY)")
        connection.execute("INSERT INTO machine_knowledge VALUES ('legacy-k1')")
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
        assert {
            "evidence_bundles_v1",
            "evidence_bundle_entries_v1",
            "evidence_bundle_reviews_v1",
            "learning_events_v2",
            "distillation_candidates_v2",
            "machine_competence_receipts_v2",
        } <= tables
        assert "graph_entities" not in tables
        assert "graph_relations" not in tables
        assert connection.execute("SELECT id FROM sentinel").fetchone()[0] == "preserve"
        assert connection.execute(
            "SELECT migration_status FROM machine_competence_legacy_v2 "
            "WHERE legacy_table='machine_knowledge' AND legacy_id='legacy-k1'"
        ).fetchone()[0] == "UNMIGRATED"

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
        assert not {
            "evidence_bundles_v1",
            "evidence_bundle_entries_v1",
            "evidence_bundle_reviews_v1",
            "learning_events_v2",
            "distillation_candidates_v2",
            "machine_competence_receipts_v2",
        } & tables
        assert connection.execute("SELECT id FROM sentinel").fetchone()[0] == "preserve"


def test_existing_knowledge_owner_applies_all_pending_incremental_migrations(
    tmp_path: Path,
) -> None:
    from shared.migration_runner import MigrationOperator

    database = tmp_path / "phase5-upgrade.sqlite"
    with closing(sqlite3.connect(database)):
        pass
    operator = MigrationOperator(db_path=database, backup_dir=tmp_path / "backups")
    operator.apply("knowledge-governance.sqlite")
    with closing(sqlite3.connect(database)) as connection:
        provenance = json.loads(
            connection.execute(
                "SELECT provenance_json FROM migration_operator_runs "
                "WHERE owner='knowledge-governance.sqlite' AND state='applied' "
                "ORDER BY recorded_at DESC, rowid DESC LIMIT 1"
            ).fetchone()[0]
        )
        provenance["applied_migrations"] = [
            "phase5_knowledge_candidate_governance_v1",
            "phase5_knowledge_candidate_governance_events_v1",
            "phase5_knowledge_candidate_versioning_v1",
            "phase5_knowledge_candidate_learning_artifacts_v1",
        ]
        connection.executescript(
            """
            DROP TABLE machine_competence_legacy_v2;
            DROP TABLE machine_competence_receipts_v2;
            DROP TABLE distillation_candidates_v2;
            DROP TABLE learning_events_v2;
            DROP TABLE evidence_bundle_reviews_v1;
            DROP TABLE evidence_bundle_entries_v1;
            DROP TABLE evidence_bundles_v1;
            DROP TABLE machine_knowledge_approval_events_v1;
            DROP TABLE learning_approval_events_v1;
            DELETE FROM schema_migrations WHERE version IN (9, 10, 15, 16);
            """
        )
        connection.execute(
            "UPDATE migration_operator_runs SET provenance_json=? "
            "WHERE owner='knowledge-governance.sqlite' AND state='applied'",
            (json.dumps(provenance, sort_keys=True),),
        )
        connection.commit()

    before = next(
        item for item in operator.status() if item["owner"] == "knowledge-governance.sqlite"
    )
    assert before["state"] == "pending"
    upgraded = operator.apply("knowledge-governance.sqlite")

    assert upgraded["state"] == "applied"
    assert upgraded["provenance"]["applied_migrations"] == [
        "phase5_learning_approval_events_v1",
        "phase5_machine_knowledge_approval_events_v1",
        "phase5_evidence_bundle_ledger_v1",
        "axr_learning_truth_v2",
    ]
    status = next(
        item for item in operator.status() if item["owner"] == "knowledge-governance.sqlite"
    )
    assert status["state"] == "applied"
    with closing(sqlite3.connect(database)) as connection:
        tables = {
            row[0]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
    assert "learning_approval_events_v1" in tables
    assert "machine_knowledge_approval_events_v1" in tables
    assert "evidence_bundles_v1" in tables
    assert "evidence_bundle_entries_v1" in tables
    assert "evidence_bundle_reviews_v1" in tables
    assert "learning_events_v2" in tables
    assert "distillation_candidates_v2" in tables
    assert "machine_competence_receipts_v2" in tables
    runs_before_reapply = len(
        [
            row
            for row in operator._snapshot_operator_runs()
            if row["owner"] == "knowledge-governance.sqlite"
        ]
    )
    operator.apply("knowledge-governance.sqlite")
    runs_after_reapply = len(
        [
            row
            for row in operator._snapshot_operator_runs()
            if row["owner"] == "knowledge-governance.sqlite"
        ]
    )
    assert runs_after_reapply == runs_before_reapply
