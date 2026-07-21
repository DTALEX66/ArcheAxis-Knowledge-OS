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


class ReviewedFeedback(BaseModel):
    model_config = ConfigDict(extra="forbid")
    candidate_id: str
    trace_id: str
    evaluation: EvalResult
    reviewer_id: str
    rationale: str
    reviewed_at: str


def create_evaluation_candidate(trace: ExecutionTrace, *, db_path: str | Path) -> EvaluationCandidate:
    evaluation = evaluate(trace)
    candidate = EvaluationCandidate(candidate_id="evaluation_" + sha256(trace.id.encode()).hexdigest()[:24], trace_id=trace.id, evaluation=evaluation)
    with sqlite3.connect(Path(db_path)) as connection:
        connection.row_factory = sqlite3.Row
        core_schema.validate(connection)
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute(
            "SELECT evaluation_json FROM evaluation_candidates_v1 "
            "WHERE id=? OR trace_id=?",
            (candidate.candidate_id, trace.id),
        ).fetchone()
        if row is not None:
            recorded = EvaluationCandidate.model_validate_json(row["evaluation_json"])
            if recorded != candidate:
                raise RuntimeError("evaluation trace id conflicts with the recorded candidate")
            return recorded
        connection.execute(
            "INSERT INTO evaluation_candidates_v1"
            "(id, trace_id, evaluation_json, status) VALUES (?, ?, ?, 'candidate')",
            (candidate.candidate_id, trace.id, candidate.model_dump_json()),
        )
        connection.commit()
    return candidate


def approve_evaluation_candidate(approval: EvaluationApproval, *, db_path: str | Path) -> MachineLesson:
    with sqlite3.connect(Path(db_path)) as connection:
        connection.row_factory = sqlite3.Row
        core_schema.validate(connection)
        row = connection.execute(
            "SELECT evaluation_json, status, reviewer_id, rationale, reviewed_at "
            "FROM evaluation_candidates_v1 WHERE id=?",
            (approval.candidate_id,),
        ).fetchone()
        if row is None:
            raise ValueError("evaluation candidate not found")
        candidate = EvaluationCandidate.model_validate_json(row["evaluation_json"])
        trace = ExecutionTrace(id=candidate.trace_id)
        lesson = compile_lesson(candidate.evaluation, trace)
        recorded_review = (row["reviewer_id"], row["rationale"], row["reviewed_at"])
        requested_review = (
            approval.reviewer_id,
            approval.rationale,
            approval.reviewed_at,
        )
        if row["status"] == "approved":
            if recorded_review != requested_review:
                raise RuntimeError("reviewed evaluation conflicts with the recorded receipt")
            return lesson
        connection.execute(
            "UPDATE evaluation_candidates_v1 "
            "SET status='approved', reviewer_id=?, rationale=?, reviewed_at=? "
            "WHERE id=? AND status='candidate'",
            (*requested_review, candidate.candidate_id),
        )
        connection.commit()
        return lesson


def list_reviewed_feedback(
    *, db_path: str | Path, limit: int = 20
) -> list[ReviewedFeedback]:
    if limit < 1:
        return []
    database = Path(db_path)
    if not database.is_file():
        return []
    with sqlite3.connect(database) as connection:
        connection.row_factory = sqlite3.Row
        core_schema.validate(connection)
        rows = connection.execute(
            "SELECT id, evaluation_json, reviewer_id, rationale, reviewed_at "
            "FROM evaluation_candidates_v1 WHERE status='approved' "
            "ORDER BY reviewed_at DESC, id LIMIT ?",
            (limit,),
        ).fetchall()
    feedback = []
    for row in rows:
        candidate = EvaluationCandidate.model_validate_json(row["evaluation_json"])
        feedback.append(
            ReviewedFeedback(
                candidate_id=str(row["id"]),
                trace_id=candidate.trace_id,
                evaluation=candidate.evaluation,
                reviewer_id=str(row["reviewer_id"]),
                rationale=str(row["rationale"]),
                reviewed_at=str(row["reviewed_at"]),
            )
        )
    return feedback
