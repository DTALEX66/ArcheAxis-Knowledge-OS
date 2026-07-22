from __future__ import annotations

import json
import sqlite3
import threading
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing, suppress

import pytest


def _persist_trace(database, trace):
    with sqlite3.connect(database) as connection:
        connection.execute(
            "INSERT OR REPLACE INTO execution_traces"
            "(id, task_id, events_json, result_json, success, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                trace.id,
                trace.task_id,
                json.dumps(trace.events),
                json.dumps(trace.result),
                1 if trace.success else (0 if trace.success is False else None),
                trace.created_at,
            ),
        )
        connection.commit()


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
    _persist_trace(database, trace)
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
    with pytest.raises(RuntimeError, match="does not match the persisted execution trace"):
        create_evaluation_candidate(conflicting_trace, db_path=database)
    approval = EvaluationApproval(candidate_id=candidate.candidate_id, reviewer_id="reviewer-1", rationale="trace reviewed", reviewed_at="2026-07-20T17:00:00Z")
    lesson = approve_evaluation_candidate(approval, db_path=database)
    assert lesson.lesson_type == "success"
    assert approve_evaluation_candidate(approval, db_path=database) == lesson
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


def test_evaluation_candidate_requires_authoritative_persisted_trace(tmp_path):
    from app.evaluation.governance import create_evaluation_candidate
    from app.schemas import ExecutionTrace
    from shared.migration_runner import MigrationOperator

    database = tmp_path / "missing-trace.sqlite"
    with closing(sqlite3.connect(database)):
        pass
    MigrationOperator(db_path=database, backup_dir=tmp_path / "backups").apply("core.sqlite")

    with pytest.raises(ValueError, match="persisted execution trace not found"):
        create_evaluation_candidate(ExecutionTrace(id="trace-missing"), db_path=database)


def test_evaluation_candidate_rejects_same_id_with_different_evidence(tmp_path):
    from app.evaluation.governance import create_evaluation_candidate
    from app.schemas import ExecutionTrace
    from shared.migration_runner import MigrationOperator

    database = tmp_path / "trace-binding.sqlite"
    with closing(sqlite3.connect(database)):
        pass
    MigrationOperator(db_path=database, backup_dir=tmp_path / "backups").apply("core.sqlite")
    trace = ExecutionTrace(
        id="trace-authoritative",
        task_id="task-1",
        success=True,
        result={"status": "done"},
        events=[
            {
                "step": {"tool": "file_read"},
                "result": {
                    "tool": "file_read",
                    "risk_level": "low",
                    "status": "ok",
                    "dry_run": False,
                    "path": "AGENTS.md",
                    "content": "authoritative evidence",
                },
            }
        ],
    )
    _persist_trace(database, trace)
    create_evaluation_candidate(trace, db_path=database)

    changed = trace.model_copy(deep=True)
    changed.events[0]["result"]["path"] = "README.md"
    changed.events[0]["result"]["content"] = "substituted evidence"

    with pytest.raises(RuntimeError, match="does not match the persisted execution trace"):
        create_evaluation_candidate(changed, db_path=database)


def test_evaluation_approval_rejects_trace_tampered_after_candidate(tmp_path):
    from app.evaluation.governance import (
        EvaluationApproval,
        approve_evaluation_candidate,
        create_evaluation_candidate,
    )
    from app.schemas import ExecutionTrace
    from shared.migration_runner import MigrationOperator

    database = tmp_path / "trace-tamper.sqlite"
    with closing(sqlite3.connect(database)):
        pass
    MigrationOperator(db_path=database, backup_dir=tmp_path / "backups").apply("core.sqlite")
    trace = ExecutionTrace(id="trace-tamper", task_id="task-1")
    _persist_trace(database, trace)
    candidate = create_evaluation_candidate(trace, db_path=database)
    _persist_trace(database, trace.model_copy(update={"result": {"status": "forged"}}))

    with pytest.raises(RuntimeError, match="persisted execution trace changed"):
        approve_evaluation_candidate(
            EvaluationApproval(
                candidate_id=candidate.candidate_id,
                reviewer_id="reviewer-1",
                rationale="reviewed",
                reviewed_at="2026-07-20T17:00:00Z",
            ),
            db_path=database,
        )


def test_competing_evaluation_approvals_have_one_durable_winner(tmp_path, monkeypatch):
    from app.evaluation import governance
    from app.schemas import ExecutionTrace
    from shared.migration_runner import MigrationOperator

    database = tmp_path / "approval-race.sqlite"
    with closing(sqlite3.connect(database)):
        pass
    MigrationOperator(db_path=database, backup_dir=tmp_path / "backups").apply("core.sqlite")
    trace = ExecutionTrace(id="trace-race", task_id="task-1")
    _persist_trace(database, trace)
    candidate = governance.create_evaluation_candidate(trace, db_path=database)
    barrier = threading.Barrier(2)
    compile_lesson = governance.compile_lesson

    def synchronized_compile(*args, **kwargs):
        with suppress(threading.BrokenBarrierError):
            barrier.wait(timeout=1)
        return compile_lesson(*args, **kwargs)

    monkeypatch.setattr(governance, "compile_lesson", synchronized_compile)
    approvals = [
        governance.EvaluationApproval(
            candidate_id=candidate.candidate_id,
            reviewer_id=f"reviewer-{index}",
            rationale=f"rationale-{index}",
            reviewed_at=f"2026-07-20T17:00:0{index}Z",
        )
        for index in (1, 2)
    ]

    def approve(approval):
        try:
            return governance.approve_evaluation_candidate(approval, db_path=database)
        except RuntimeError as exc:
            return exc

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(approve, approvals))

    lessons = [result for result in results if not isinstance(result, Exception)]
    conflicts = [result for result in results if isinstance(result, RuntimeError)]
    assert len(lessons) == 1
    assert len(conflicts) == 1
    assert "conflicts with the recorded receipt" in str(conflicts[0])


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
