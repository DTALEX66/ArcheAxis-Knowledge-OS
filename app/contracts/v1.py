"""Canonical version 1 contracts.

These models describe stable exchange objects. They do not replace legacy runtime
or SQLite objects; adapters own those transitions explicitly.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

CONTRACT_VERSION = "1.0.0"
TASKPACK_SCHEMA_ID = "https://cognitive-loop-os.local/contracts/v1/taskpack.schema.json"
EXECUTION_TRACE_SCHEMA_ID = (
    "https://cognitive-loop-os.local/contracts/v1/execution-trace.schema.json"
)
EVALUATION_SCHEMA_ID = "https://cognitive-loop-os.local/contracts/v1/evaluation.schema.json"
LESSON_SCHEMA_ID = "https://cognitive-loop-os.local/contracts/v1/lesson.schema.json"
SOURCE_RECORD_SCHEMA_ID = (
    "https://cognitive-loop-os.local/contracts/v1/source-record.schema.json"
)
CLAIM_SCHEMA_ID = "https://cognitive-loop-os.local/contracts/v1/claim.schema.json"


class TaskStepV1(BaseModel):
    """A single requested execution step."""

    model_config = ConfigDict(extra="forbid")

    step_id: str
    action: str
    tool: str


class TaskPackV1(BaseModel):
    """Lossless canonical representation of the current KB TaskPack."""

    model_config = ConfigDict(extra="forbid", json_schema_extra={"$id": TASKPACK_SCHEMA_ID})

    schema_version: Literal["1.0.0"]
    task_id: str
    context_id: str = ""
    goal: str
    steps: list[TaskStepV1] = Field(default_factory=list)
    requested_tools: list[str] = Field(default_factory=list)
    declared_allowed_tools: list[str] = Field(default_factory=list)
    explicitly_blocked_tools: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    success_criteria: list[str] = Field(default_factory=list)
    risk_level: Literal["low", "medium", "high", "critical"] = "low"
    requires_review: bool = False


class SourceRecordV1(BaseModel):
    """Versioned source content with explicit provenance and quarantine state."""

    model_config = ConfigDict(
        extra="forbid", json_schema_extra={"$id": SOURCE_RECORD_SCHEMA_ID}
    )

    schema_version: Literal["1.0.0"]
    source_id: str
    title: str
    content: str
    source_locator: str
    tags: list[str] = Field(default_factory=list)
    provenance_status: Literal["unverified", "verified", "rejected"] = "unverified"
    quarantine_status: Literal["candidate", "released", "rejected"] = "candidate"
    created_at: str


class ClaimV1(BaseModel):
    """Atomic research claim with explicit provenance and review governance."""

    model_config = ConfigDict(extra="forbid", json_schema_extra={"$id": CLAIM_SCHEMA_ID})

    schema_version: Literal["1.0.0"]
    claim_id: str = Field(min_length=1)
    statement: str = Field(min_length=1)
    source_record_ids: list[str] = Field(min_length=1)
    status: Literal["candidate", "verified", "rejected", "conflicted", "unknown"]
    provenance_status: Literal["caller_supplied", "server_verified"]
    requires_human_review: bool
    created_at: str

    @model_validator(mode="after")
    def enforce_provenance_governance(self) -> ClaimV1:
        if self.status == "verified" and self.provenance_status != "server_verified":
            raise ValueError("verified claim requires server_verified provenance")
        if self.provenance_status == "caller_supplied" and not self.requires_human_review:
            raise ValueError("caller_supplied claim requires human review")
        return self


class ExecutionTraceV1(BaseModel):
    """Lossless canonical representation of the current runtime execution trace."""

    model_config = ConfigDict(
        extra="forbid", json_schema_extra={"$id": EXECUTION_TRACE_SCHEMA_ID}
    )

    schema_version: Literal["1.0.0"]
    trace_id: str
    task_id: str | None = None
    events: list[dict[str, object]] = Field(default_factory=list)
    result: dict[str, object] = Field(default_factory=dict)
    success: bool | None = None
    created_at: str


class EvaluationV1(BaseModel):
    """Lossless canonical representation of the current runtime evaluation."""

    model_config = ConfigDict(
        extra="forbid", json_schema_extra={"$id": EVALUATION_SCHEMA_ID}
    )

    schema_version: Literal["1.0.0"]
    success: bool
    score: float
    failure_reason: str = ""
    improvement: str = ""


class LessonV1(BaseModel):
    """Lossless canonical representation of the current runtime machine lesson."""

    model_config = ConfigDict(extra="forbid", json_schema_extra={"$id": LESSON_SCHEMA_ID})

    schema_version: Literal["1.0.0"]
    lesson_id: str
    pattern: str
    lesson_type: Literal["success", "failure", "anti_pattern", "constraint"]
    future_constraint: str
    evidence_trace_id: str | None = None
    created_at: str
