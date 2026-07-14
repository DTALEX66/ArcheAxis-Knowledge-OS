"""Canonical version 1 contracts.

These models describe stable exchange objects. They do not replace legacy runtime
or SQLite objects; adapters own those transitions explicitly.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

CONTRACT_VERSION = "1.0.0"
TASKPACK_SCHEMA_ID = "https://cognitive-loop-os.local/contracts/v1/taskpack.schema.json"


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
