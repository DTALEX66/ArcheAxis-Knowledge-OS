from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


class CoreObject(BaseModel):
    id: str = Field(default_factory=lambda: new_id("obj"))
    object_type: str = "document"
    content: str
    source: str = "unknown"
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=now_iso)
    attention_score: float = 0.0
    route: str | None = None


class AttentionDecision(BaseModel):
    route: Literal["KB", "IR", "TASK", "DROP", "REVIEW"]
    score: float
    reasons: list[str] = Field(default_factory=list)
    risk_level: Literal["low", "medium", "high"] = "low"


class ContextPack(BaseModel):
    query: str
    items: list[CoreObject] = Field(default_factory=list)
    summary: str = ""
    token_budget: int = 4000
    score: float = 0.0
    score_reasons: list[str] = Field(default_factory=list)


class TaskPack(BaseModel):
    id: str = Field(default_factory=lambda: new_id("task"))
    goal: str
    steps: list[dict[str, Any]] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)
    risk_level: Literal["low", "medium", "high"] = "low"
    success_criteria: list[str] = Field(default_factory=list)


class ExecutionTrace(BaseModel):
    id: str = Field(default_factory=lambda: new_id("trace"))
    task_id: str | None = None
    events: list[dict[str, Any]] = Field(default_factory=list)
    result: dict[str, Any] = Field(default_factory=dict)
    success: bool | None = None
    created_at: str = Field(default_factory=now_iso)


class EvaluationDimension(BaseModel):
    status: Literal["passed", "failed", "unverified"]
    reason: str


class EvalResult(BaseModel):
    success: bool
    score: float
    failure_reason: str = ""
    improvement: str = ""
    dimensions: dict[str, EvaluationDimension] = Field(default_factory=dict)


class MachineLesson(BaseModel):
    id: str = Field(default_factory=lambda: new_id("lesson"))
    pattern: str
    lesson_type: Literal["success", "failure", "anti_pattern", "constraint"]
    future_constraint: str
    evidence_trace_id: str | None = None
    created_at: str = Field(default_factory=now_iso)


class PermissionDecision(BaseModel):
    id: str = Field(default_factory=lambda: new_id("perm"))
    task_id: str
    risk_level: Literal["low", "medium", "high", "critical"] = "low"
    allowed_tools: list[str] = Field(default_factory=list)
    blocked_tools: list[str] = Field(default_factory=list)
    requires_human_review: bool = False
    reason: str = ""
    created_at: str = Field(default_factory=now_iso)
