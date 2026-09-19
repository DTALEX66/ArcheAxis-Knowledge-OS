"""R6 A11 local model capability pool inventory contract."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


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
