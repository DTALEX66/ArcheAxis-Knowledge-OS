"""R6 A07 machine experience growth and review receipt contract."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


GrowthStage = Literal["experience", "lesson", "skill_candidate", "review", "reuse"]
GrowthState = Literal["observed", "created", "pending", "approved", "rejected", "used", "skipped"]


class GrowthStepV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    stage: GrowthStage
    state: GrowthState
    actor: Literal["system", "human"]
    evidence_refs: list[str] = Field(default_factory=list)


class MachineGrowthReceiptV1(BaseModel):
    """Append-only trace for machine learning from experience, never verified truth."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    schema_: Literal["archeaxis.machine-growth/v1"] = Field(
        default="archeaxis.machine-growth/v1", alias="schema"
    )
    receipt_id: str = Field(min_length=1)
    source_event_ids: list[str] = Field(min_length=1)
    goal: str = Field(min_length=1)
    outcome: Literal["success", "failure", "partial", "unknown"]
    steps: list[GrowthStepV1] = Field(min_length=1)
    machine_verified: Literal[False] = False

    @model_validator(mode="after")
    def validate_lifecycle(self) -> "MachineGrowthReceiptV1":
        stages = [step.stage for step in self.steps]
        if stages[0] != "experience":
            raise ValueError("growth lifecycle must start with experience")
        if "skill_candidate" in stages and "lesson" not in stages:
            raise ValueError("skill_candidate requires a lesson stage")
        review_steps = [step for step in self.steps if step.stage == "review"]
        if any(step.state == "approved" and step.actor != "human" for step in review_steps):
            raise ValueError("approved growth review requires a human actor")
        if any(step.stage == "reuse" and step.state == "used" for step in self.steps):
            if not any(step.stage == "review" and step.state == "approved" for step in review_steps):
                raise ValueError("reuse requires an approved human review")
        return self
