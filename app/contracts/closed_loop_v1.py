"""R6 A14 full Human↔Machine closed-loop receipt contract."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


LoopStage = Literal["source", "knowledge", "human_learning", "machine_use", "evaluation", "correction", "lesson", "retest"]


class ClosedLoopStageV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    stage: LoopStage
    status: Literal["pass", "blocked", "not_executed"]
    evidence_level: Literal["real", "synthetic", "unverified"]
    evidence_refs: list[str] = Field(default_factory=list)


class ClosedLoopReceiptV1(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    schema_: Literal["archeaxis.closed-loop/v1"] = Field(
        default="archeaxis.closed-loop/v1", alias="schema"
    )
    journey_id: str = Field(min_length=1)
    canonical_writer: Literal["archeaxis-core-rust-sqlite"]
    stages: list[ClosedLoopStageV1] = Field(min_length=8)
    overall_status: Literal["partial", "complete", "blocked"]
    synthetic: bool

    @model_validator(mode="after")
    def validate_loop(self) -> "ClosedLoopReceiptV1":
        expected = ["source", "knowledge", "human_learning", "machine_use", "evaluation", "correction", "lesson", "retest"]
        actual = [stage.stage for stage in self.stages]
        if actual != expected:
            raise ValueError("closed loop stages must follow the canonical order")
        if self.overall_status == "complete":
            if self.synthetic or any(stage.status != "pass" or stage.evidence_level != "real" for stage in self.stages):
                raise ValueError("complete closed loop requires real evidence for every stage")
            for stage_name in ("correction", "retest"):
                stage = next(stage for stage in self.stages if stage.stage == stage_name)
                if not stage.evidence_refs:
                    raise ValueError(f"complete closed loop requires {stage_name} evidence refs")
        if self.synthetic and self.overall_status == "complete":
            raise ValueError("synthetic journey cannot be complete")
        return self
