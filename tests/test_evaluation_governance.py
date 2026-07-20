from __future__ import annotations

import sqlite3
from contextlib import closing


def test_evaluation_candidate_requires_explicit_review_before_lesson(tmp_path):
    from app.evaluation.governance import (
        EvaluationApproval,
        approve_evaluation_candidate,
        create_evaluation_candidate,
    )
    from app.schemas import ExecutionTrace
    from shared.migration_runner import MigrationOperator

    database = tmp_path / "evaluation.sqlite"
    with closing(sqlite3.connect(database)):
        pass
    MigrationOperator(db_path=database, backup_dir=tmp_path / "backups").apply("core.sqlite")
    trace = ExecutionTrace(task_id="task-1", success=True, result={"status": "done"}, events=[{"step": {"tool": "file_read"}, "result": {"tool": "file_read", "status": "ok", "dry_run": False, "path": "AGENTS.md", "content": "x"}}])
    candidate = create_evaluation_candidate(trace, db_path=database)
    assert candidate.status == "candidate"
    lesson = approve_evaluation_candidate(EvaluationApproval(candidate_id=candidate.candidate_id, reviewer_id="reviewer-1", rationale="trace reviewed", reviewed_at="2026-07-20T17:00:00Z"), db_path=database)
    assert lesson.lesson_type == "success"
