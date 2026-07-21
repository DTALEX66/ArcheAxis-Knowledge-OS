from __future__ import annotations

import sqlite3
from contextlib import closing

import pytest


def test_evaluation_candidate_requires_explicit_review_before_lesson(tmp_path):
    from app.core.compiler import compile_task
    from app.evaluation.governance import (
        EvaluationApproval,
        approve_evaluation_candidate,
        create_evaluation_candidate,
        list_reviewed_feedback,
    )
    from app.schemas import ContextPack, ExecutionTrace
    from shared.migration_runner import MigrationOperator

    database = tmp_path / "evaluation.sqlite"
    with closing(sqlite3.connect(database)):
        pass
    MigrationOperator(db_path=database, backup_dir=tmp_path / "backups").apply("core.sqlite")
    trace = ExecutionTrace(task_id="task-1", success=True, result={"status": "done"}, events=[{"step": {"tool": "file_read"}, "result": {"tool": "file_read", "status": "ok", "dry_run": False, "path": "AGENTS.md", "content": "x"}}])
    candidate = create_evaluation_candidate(trace, db_path=database)
    assert candidate.status == "candidate"
    assert create_evaluation_candidate(trace, db_path=database) == candidate
    conflicting_trace = trace.model_copy(
        update={
            "events": [
                {
                    "step": {"tool": "file_read"},
                    "result": {
                        "tool": "file_read",
                        "status": "error",
                        "dry_run": False,
                    },
                }
            ],
            "success": False,
        }
    )
    with pytest.raises(RuntimeError, match="evaluation trace id conflicts"):
        create_evaluation_candidate(conflicting_trace, db_path=database)
    approval = EvaluationApproval(candidate_id=candidate.candidate_id, reviewer_id="reviewer-1", rationale="trace reviewed", reviewed_at="2026-07-20T17:00:00Z")
    lesson = approve_evaluation_candidate(approval, db_path=database)
    assert lesson.lesson_type == "success"
    assert approve_evaluation_candidate(approval, db_path=database).lesson_type == "success"
    with pytest.raises(RuntimeError, match="reviewed evaluation conflicts"):
        approve_evaluation_candidate(
            approval.model_copy(update={"rationale": "overwrite attempt"}), db_path=database
        )

    feedback = list_reviewed_feedback(db_path=database)
    assert len(feedback) == 1
    assert feedback[0].trace_id == trace.id
    assert feedback[0].reviewer_id == "reviewer-1"
    assert feedback[0].evaluation.dimensions["correctness"].status == "unverified"
    task = compile_task(
        ContextPack(query="read file: AGENTS.md"), reviewed_feedback=feedback
    )
    assert any("trace reviewed" in constraint for constraint in task.constraints)
    assert any(feedback[0].evaluation.improvement in constraint for constraint in task.constraints)


def test_runtime_run_consumes_reviewed_feedback_before_planning(monkeypatch):
    import app.main as main_module
    from app.evaluation.governance import ReviewedFeedback
    from app.facades import runtime as runtime_module
    from app.schemas import ContextPack, EvalResult, EvaluationDimension

    feedback = ReviewedFeedback(
        candidate_id="evaluation-reviewed",
        trace_id="trace-reviewed",
        evaluation=EvalResult(
            success=True,
            score=1.0,
            improvement="preserve reviewed evidence on the next run",
            dimensions={
                "correctness": EvaluationDimension(
                    status="unverified", reason="no human truth pair"
                )
            },
        ),
        reviewer_id="reviewer-1",
        rationale="reuse the reviewed constraint",
        reviewed_at="2026-07-20T17:00:00Z",
    )
    monkeypatch.setattr(main_module, "save_memory", lambda document: None)
    monkeypatch.setattr(
        main_module,
        "retrieve",
        lambda query: ContextPack(query=query, summary="reviewed feedback context"),
    )
    monkeypatch.setattr(main_module, "save_lesson", lambda lesson: None)
    monkeypatch.setattr(runtime_module, "log_trace", lambda trace: None)
    monkeypatch.setattr(
        main_module,
        "list_reviewed_feedback",
        lambda **kwargs: [feedback],
        raising=False,
    )

    response = main_module.run(
        {"content": "read file: AGENTS.md", "source": "reviewed-feedback-test"}
    )

    assert response["status"] == "done"
    assert any(
        "reuse the reviewed constraint" in constraint
        for constraint in response["task"].constraints
    )
