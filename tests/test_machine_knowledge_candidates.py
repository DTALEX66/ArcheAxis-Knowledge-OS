from __future__ import annotations

import sqlite3
from contextlib import closing


def test_mastered_signal_creates_candidate_machine_knowledge_with_explicit_lifecycle(tmp_path):
    from app.knowledge.machine_knowledge import (
        MachineKnowledgeApproval,
        create_machine_knowledge_candidate,
        deprecate_machine_knowledge_candidate,
    )
    from shared.migration_runner import MigrationOperator

    database = tmp_path / "machine-candidate.sqlite"
    with closing(sqlite3.connect(database)):
        pass
    MigrationOperator(db_path=database, backup_dir=tmp_path / "backups").apply("core.sqlite")
    with closing(sqlite3.connect(database)) as connection:
        connection.execute(
            "INSERT INTO mastery_signals_v1 VALUES ('signal-1', 'card-1', ?, '2026-07-20T16:00:00Z')",
            ('{"schema_version":"1.0.0","calculation_version":"review-outcome-v1","card_id":"card-1","is_mastered":true,"review_ids":["r1","r2","r3"],"mistake_ids":[],"review_count":3,"unresolved_mistake_ids":[],"latest_ease_factor":2.5,"latest_review_quality":5,"review_status":"mastered"}',),
        )
        connection.commit()

    candidate = create_machine_knowledge_candidate(
        "signal-1", title="Evidence-backed rule", content="Apply the reviewed rule.", db_path=database
    )
    assert candidate.lifecycle_status == "candidate"
    assert candidate.requires_human_review is True
    approved = MachineKnowledgeApproval(
        approval_id="approve-machine-1", candidate_id=candidate.unit_id,
        reviewer_id="reviewer-1", decision="approved", rationale="reviewed", reviewed_at="2026-07-20T16:01:00Z"
    )
    assert deprecate_machine_knowledge_candidate(approved, db_path=database).lifecycle_status == "approved"
    deprecated = MachineKnowledgeApproval(
        approval_id="deprecate-machine-1", candidate_id=candidate.unit_id,
        reviewer_id="reviewer-1", decision="deprecated", rationale="superseded", reviewed_at="2026-07-20T16:02:00Z"
    )
    assert create_machine_knowledge_candidate("signal-1", title="Evidence-backed rule", content="Apply the reviewed rule.", db_path=database).unit_id == candidate.unit_id
    assert deprecate_machine_knowledge_candidate(deprecated, db_path=database).lifecycle_status == "deprecated"
    with closing(sqlite3.connect(database)) as connection:
        assert connection.execute("SELECT COUNT(*) FROM machine_knowledge_units").fetchone()[0] == 0
