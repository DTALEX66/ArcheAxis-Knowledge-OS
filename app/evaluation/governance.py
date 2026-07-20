"""Reviewer-gated evaluation feedback projection."""
from __future__ import annotations

import sqlite3
from hashlib import sha256
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from app.evaluation.evaluator import evaluate
from app.evaluation.feedback import compile_lesson
from app.schemas import EvalResult, ExecutionTrace, MachineLesson
from shared import core_schema


class EvaluationCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    candidate_id: str
    trace_id: str
    evaluation: EvalResult
    status: str = "candidate"


class EvaluationApproval(BaseModel):
    model_config = ConfigDict(extra="forbid")
    candidate_id: str = Field(min_length=1)
    reviewer_id: str = Field(min_length=1)
    rationale: str = Field(min_length=1)
    reviewed_at: str = Field(min_length=1)


def create_evaluation_candidate(trace: ExecutionTrace, *, db_path: str | Path) -> EvaluationCandidate:
    evaluation = evaluate(trace)
    candidate = EvaluationCandidate(candidate_id="evaluation_" + sha256(trace.id.encode()).hexdigest()[:24], trace_id=trace.id, evaluation=evaluation)
    with sqlite3.connect(Path(db_path)) as connection:
        core_schema.validate(connection)
        connection.execute("INSERT OR IGNORE INTO evaluation_candidates_v1(id, trace_id, evaluation_json, status) VALUES (?, ?, ?, 'candidate')", (candidate.candidate_id, trace.id, candidate.model_dump_json()))
        connection.commit()
    return candidate


def approve_evaluation_candidate(approval: EvaluationApproval, *, db_path: str | Path) -> MachineLesson:
    with sqlite3.connect(Path(db_path)) as connection:
        connection.row_factory = sqlite3.Row
        core_schema.validate(connection)
        row = connection.execute("SELECT evaluation_json FROM evaluation_candidates_v1 WHERE id=?", (approval.candidate_id,)).fetchone()
        if row is None:
            raise ValueError("evaluation candidate not found")
        candidate = EvaluationCandidate.model_validate_json(row["evaluation_json"])
        trace = ExecutionTrace(id=candidate.trace_id)
        lesson = compile_lesson(candidate.evaluation, trace)
        connection.execute("UPDATE evaluation_candidates_v1 SET status='approved', reviewer_id=?, rationale=?, reviewed_at=? WHERE id=?", (approval.reviewer_id, approval.rationale, approval.reviewed_at, candidate.candidate_id))
        connection.commit()
        return lesson
