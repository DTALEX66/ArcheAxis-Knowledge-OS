from __future__ import annotations

import sqlite3
from pathlib import Path


def test_reviewed_artifact_runs_only_explicit_low_risk_task_and_creates_evaluation_candidate(tmp_path):
    from app.contracts.v1 import TaskPackV1, TaskStepV1
    from app.evaluation.governance import EvaluationCandidate
    from app.facades.research_runtime import run_reviewed_artifact_task

    task = TaskPackV1(
        schema_version="1.0.0", task_id="task-1", context_id="artifact-1", goal="read file: AGENTS.md",
        steps=[TaskStepV1(step_id="step-1", action="read", tool="file_read", parameters={"path": str(Path.cwd() / "AGENTS.md")})], requested_tools=["file_read"],
        declared_allowed_tools=["file_read"], constraints=["project-contained"],
        success_criteria=["attributable evidence"], risk_level="low", requires_review=False,
    )
    database = tmp_path / "loop.sqlite"
    result = run_reviewed_artifact_task("artifact-1", task, db_path=database)
    assert result.trace.success is True
    assert isinstance(result.evaluation, EvaluationCandidate)
    assert result.evaluation.status == "candidate"
    with sqlite3.connect(database) as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM execution_traces WHERE id=?", (result.trace.id,)
        ).fetchone()[0] == 1
        assert connection.execute(
            "SELECT COUNT(*) FROM evaluation_candidates_v1 WHERE trace_id=?", (result.trace.id,)
        ).fetchone()[0] == 1
