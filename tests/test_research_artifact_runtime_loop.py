from __future__ import annotations

from pathlib import Path


def test_reviewed_artifact_runs_only_explicit_low_risk_task_and_creates_evaluation_candidate(tmp_path, monkeypatch):
    from app.contracts.v1 import TaskPackV1, TaskStepV1
    from app.evaluation.governance import EvaluationCandidate
    from app.facades.research_runtime import run_reviewed_artifact_task

    task = TaskPackV1(
        schema_version="1.0.0", task_id="task-1", context_id="artifact-1", goal="read file: AGENTS.md",
        steps=[TaskStepV1(step_id="step-1", action="read", tool="file_read", parameters={"path": str(Path.cwd() / "AGENTS.md")})], requested_tools=["file_read"],
        declared_allowed_tools=["file_read"], constraints=["project-contained"],
        success_criteria=["attributable evidence"], risk_level="low", requires_review=False,
    )
    monkeypatch.setattr("app.facades.research_runtime.log_trace", lambda trace: None)
    result = run_reviewed_artifact_task("artifact-1", task, db_path=tmp_path / "loop.sqlite")
    assert result.trace.success is True
    assert isinstance(result.evaluation, EvaluationCandidate)
    assert result.evaluation.status == "candidate"
