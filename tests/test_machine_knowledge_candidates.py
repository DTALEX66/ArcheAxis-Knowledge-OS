from __future__ import annotations

import sqlite3
from contextlib import closing

import pytest


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
    MigrationOperator(db_path=database, backup_dir=tmp_path / "backups").apply("knowledge-governance.sqlite")
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
    from app.knowledge.vault_projection import project_approved_machine_knowledge_asset

    with pytest.raises(ValueError, match="approved machine knowledge unit"):
        project_approved_machine_knowledge_asset(
            candidate.unit_id,
            db_path=database,
            asset_root=tmp_path,
            dry_run=False,
        )
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
        events = connection.execute(
            "SELECT approval_id, decision, reviewer_id FROM machine_knowledge_approval_events_v1 "
            "ORDER BY reviewed_at, id"
        ).fetchall()
        assert events == [
            ("approve-machine-1", "approved", "reviewer-1"),
            ("deprecate-machine-1", "deprecated", "reviewer-1"),
        ]

    assert deprecate_machine_knowledge_candidate(deprecated, db_path=database).lifecycle_status == "deprecated"
    with closing(sqlite3.connect(database)) as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM machine_knowledge_approval_events_v1"
        ).fetchone()[0] == 2

    conflicting_replay = deprecated.model_copy(update={"rationale": "changed rationale"})
    with pytest.raises(RuntimeError, match="approval id conflicts"):
        deprecate_machine_knowledge_candidate(conflicting_replay, db_path=database)
    resurrection = approved.model_copy(
        update={
            "approval_id": "resurrect-machine-1",
            "reviewed_at": "2026-07-20T16:03:00Z",
        }
    )
    with pytest.raises(RuntimeError, match="deprecated.*terminal"):
        deprecate_machine_knowledge_candidate(resurrection, db_path=database)
    with closing(sqlite3.connect(database)) as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM machine_knowledge_approval_events_v1"
        ).fetchone()[0] == 2


def test_runtime_reads_only_approved_machine_knowledge(tmp_path):
    from app.knowledge.machine_knowledge import (
        MachineKnowledgeApproval,
        create_machine_knowledge_candidate,
        deprecate_machine_knowledge_candidate,
        list_runtime_machine_knowledge,
    )
    from shared.migration_runner import MigrationOperator

    database = tmp_path / "runtime-machine-knowledge.sqlite"
    with closing(sqlite3.connect(database)):
        pass
    MigrationOperator(db_path=database, backup_dir=tmp_path / "backups").apply("core.sqlite")
    MigrationOperator(db_path=database, backup_dir=tmp_path / "backups").apply("knowledge-governance.sqlite")

    def add_mastered_signal(signal_id: str, card_id: str) -> None:
        with closing(sqlite3.connect(database)) as connection:
            payload = (
                '{"schema_version":"1.0.0","calculation_version":"review-outcome-v1",'
                f'"card_id":"{card_id}","is_mastered":true,"review_ids":["r1","r2","r3"],'
                '"mistake_ids":[],"review_count":3,"unresolved_mistake_ids":[],'
                '"latest_ease_factor":2.5,"latest_review_quality":5,"review_status":"mastered"}'
            )
            connection.execute(
                "INSERT INTO mastery_signals_v1 VALUES (?, ?, ?, '2026-07-20T16:00:00Z')",
                (signal_id, card_id, payload),
            )
            connection.commit()

    for suffix in ("approved", "candidate", "deprecated"):
        add_mastered_signal(f"signal-{suffix}", f"card-{suffix}")
    approved = create_machine_knowledge_candidate(
        "signal-approved", title="Approved", content="usable", db_path=database
    )
    create_machine_knowledge_candidate(
        "signal-candidate", title="Candidate", content="not usable", db_path=database
    )
    deprecated = create_machine_knowledge_candidate(
        "signal-deprecated", title="Deprecated", content="not usable", db_path=database
    )
    for approval in (
        MachineKnowledgeApproval(
            approval_id="approve-runtime", candidate_id=approved.unit_id,
            reviewer_id="reviewer-1", decision="approved", rationale="reviewed",
            reviewed_at="2026-07-20T16:01:00Z",
        ),
        MachineKnowledgeApproval(
            approval_id="deprecate-runtime", candidate_id=deprecated.unit_id,
            reviewer_id="reviewer-1", decision="deprecated", rationale="superseded",
            reviewed_at="2026-07-20T16:02:00Z",
        ),
    ):
        deprecate_machine_knowledge_candidate(approval, db_path=database)

    units = list_runtime_machine_knowledge(db_path=database)

    assert [unit.unit_id for unit in units] == [approved.unit_id]
    assert units[0].lifecycle_status == "approved"
    assert units[0].requires_human_review is False


def test_runtime_machine_knowledge_fails_closed_on_tampered_approved_payload(tmp_path):
    from app.knowledge.machine_knowledge import list_runtime_machine_knowledge
    from shared.migration_runner import MigrationOperator

    database = tmp_path / "tampered-machine-knowledge.sqlite"
    with closing(sqlite3.connect(database)):
        pass
    MigrationOperator(db_path=database, backup_dir=tmp_path / "backups").apply("core.sqlite")
    MigrationOperator(db_path=database, backup_dir=tmp_path / "backups").apply("knowledge-governance.sqlite")
    payload = (
        '{"schema_version":"1.0.0","unit_id":"tampered","title":"Tampered",'
        '"content":"unsafe","unit_type":"rule","tags":[],"confidence":0.8,'
        '"source_type":"mastery_signal","source_id":"signal-tampered","legacy_active":0,'
        '"lifecycle_status":"candidate","provenance_status":"server_verified",'
        '"requires_human_review":true,"created_at":"now","updated_at":"now"}'
    )
    with closing(sqlite3.connect(database)) as connection:
        connection.execute(
            "INSERT INTO machine_knowledge_candidates_v1 VALUES (?, ?, ?, 'approved', ?, ?, ?, ?)",
            ("tampered", "signal-tampered", payload, "approval-tampered", "reviewer-1", "reviewed", "now"),
        )
        connection.commit()

    with pytest.raises(RuntimeError, match="approved machine knowledge payload conflicts"):
        list_runtime_machine_knowledge(db_path=database)


def test_runtime_machine_knowledge_filters_by_scope(tmp_path):
    """GOV-001: AI retrieval must only use approved units whose scope matches
    the requesting scope. A unit with a specific scope must NOT leak to a
    different-scope retrieval; a scope-less (generic) approved unit remains
    visible to any retrieval.
    """
    from app.knowledge.machine_knowledge import (
        MachineKnowledgeApproval,
        create_machine_knowledge_candidate,
        deprecate_machine_knowledge_candidate,
        list_runtime_machine_knowledge,
    )
    from shared.migration_runner import MigrationOperator

    database = tmp_path / "scoped-machine-knowledge.sqlite"
    with closing(sqlite3.connect(database)):
        pass
    MigrationOperator(db_path=database, backup_dir=tmp_path / "backups").apply("core.sqlite")
    MigrationOperator(db_path=database, backup_dir=tmp_path / "backups").apply("knowledge-governance.sqlite")

    def add_mastered(signal_id, card_id):
        payload = (
            '{"schema_version":"1.0.0","calculation_version":"review-outcome-v1",'
            f'"card_id":"{card_id}","is_mastered":true,"review_ids":["r1","r2","r3"],'
            '"mistake_ids":[],"review_count":3,"unresolved_mistake_ids":[],'
            '"latest_ease_factor":2.5,"latest_review_quality":5,"review_status":"mastered"}'
        )
        with closing(sqlite3.connect(database)) as conn:
            conn.execute(
                "INSERT INTO mastery_signals_v1 VALUES (?, ?, ?, '2026-07-20T16:00:00Z')",
                (signal_id, card_id, payload),
            )
            conn.commit()

    # Two mastered signals -> two candidates; approve one scoped and one generic.
    add_mastered("sig-scoped", "card-scoped")
    add_mastered("sig-generic", "card-generic")
    scoped = create_machine_knowledge_candidate(
        "sig-scoped", title="Scoped", content="scoped rule", db_path=database, scope="knowledge"
    )
    generic = create_machine_knowledge_candidate(
        "sig-generic", title="Generic", content="generic rule", db_path=database
    )
    for approval in (
        MachineKnowledgeApproval(
            approval_id="approve-scoped", candidate_id=scoped.unit_id, reviewer_id="r1",
            decision="approved", rationale="ok", reviewed_at="2026-07-20T16:01:00Z",
        ),
        MachineKnowledgeApproval(
            approval_id="approve-generic", candidate_id=generic.unit_id, reviewer_id="r1",
            decision="approved", rationale="ok", reviewed_at="2026-07-20T16:02:00Z",
        ),
    ):
        deprecate_machine_knowledge_candidate(approval, db_path=database)

    # Retrieval scoped to 'knowledge' sees the scoped + generic unit.
    knowledge_units = list_runtime_machine_knowledge(db_path=database, scope="knowledge")
    assert {u.unit_id for u in knowledge_units} == {scoped.unit_id, generic.unit_id}

    # Retrieval scoped elsewhere must NOT see the 'knowledge' scoped unit.
    other_units = list_runtime_machine_knowledge(db_path=database, scope="research")
    assert other_units and generic.unit_id in {u.unit_id for u in other_units}
    assert scoped.unit_id not in {u.unit_id for u in other_units}

    # Default (no scope) retrieval keeps backward compatibility: sees all approved.
    all_units = list_runtime_machine_knowledge(db_path=database)
    assert {u.unit_id for u in all_units} == {scoped.unit_id, generic.unit_id}
