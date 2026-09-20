"""R6 A11 local model capability pool inventory contract."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ModelRoleEntryV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: Literal["asr", "ocr", "vision_caption", "video_extract", "llm_text", "embedding", "document"]
    model: str = Field(min_length=1)
    quantization: str = Field(min_length=1)
    runtime: str = Field(min_length=1)
    memory_mib: int | None = Field(default=None, ge=0)
    fallback: str = Field(min_length=1)
    status: Literal["measured_historical", "measured_current", "unmeasured", "blocked"]
    evidence_refs: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_measured_evidence(self) -> ModelRoleEntryV1:
        if self.status in {"measured_current", "measured_historical"} and not self.evidence_refs:
            raise ValueError("measured model entries require evidence_refs")
        return self


class ModelCapabilityPoolV1(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    schema_: Literal["archeaxis.model-capability-pool/v1"] = Field(
        default="archeaxis.model-capability-pool/v1", alias="schema"
    )
    profile_id: str = Field(min_length=1)
    platform: str = Field(min_length=1)
    entries: list[ModelRoleEntryV1] = Field(min_length=1)
    inventory_scope: Literal["repository_profile", "shared_model_library_readonly", "runtime_probe"]
    benchmark_status: Literal["not_run", "partial", "complete"]
