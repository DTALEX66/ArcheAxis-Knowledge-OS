"""Governed bridge from an explicitly reviewed artifact task to runtime evidence."""
from __future__ import annotations

import sqlite3
from pathlib import Path

from pydantic import BaseModel

from app.adapters.taskpack import project_to_runtime
from app.agent.executor import execute
from app.contracts.v1 import TaskPackV1
from app.core.permissions import check_permission
from app.core.trace import log_trace
from app.evaluation.governance import EvaluationCandidate, create_evaluation_candidate
from app.schemas import ExecutionTrace
from shared.migration_runner import MigrationOperator


class ArtifactRuntimeResult(BaseModel):
    artifact_id: str
    trace: ExecutionTrace
    evaluation: EvaluationCandidate


def run_reviewed_artifact_task(
    artifact_id: str, task: TaskPackV1, *, db_path: str | Path
) -> ArtifactRuntimeResult:
    """Run an explicit low-risk task; artifact text is never interpreted as a command."""
    if task.context_id != artifact_id:
        raise ValueError("task context_id must match artifact_id")
    projection = project_to_runtime(task)
    permission = check_permission(projection.task)
    if permission.requires_human_review:
        raise ValueError("artifact task requires human review")
    trace = execute(projection.task, permission)
    log_trace(trace)
    database = Path(db_path)
    database.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(database):
        pass
    MigrationOperator(db_path=database, backup_dir=database.parent / "backups").apply("core.sqlite")
    return ArtifactRuntimeResult(
        artifact_id=artifact_id,
        trace=trace,
        evaluation=create_evaluation_candidate(trace, db_path=database),
    )
