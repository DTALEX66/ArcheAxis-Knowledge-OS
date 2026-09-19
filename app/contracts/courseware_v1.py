"""R6 A10 courseware and interactive learning artifact contract."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CoursewareArtifactV1(BaseModel):
    """Source-grounded courseware output; renderer state is derived only."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    schema_: Literal["archeaxis.courseware-artifact/v1"] = Field(
        default="archeaxis.courseware-artifact/v1", alias="schema"
    )
    artifact_id: str = Field(min_length=1)
    artifact_type: Literal[
        "lesson", "slide", "quiz", "visual", "simulation", "pbl", "coding_activity", "audio_video"
    ]
    title: str = Field(min_length=1)
    domain_pack_id: str = Field(pattern=r"^[a-z][a-z0-9-]+$")
    source_ids: list[str] = Field(min_length=1)
    knowledge_ids: list[str] = Field(min_length=1)
    renderer: str = Field(min_length=1)
    renderer_version: str = Field(min_length=1)
    status: Literal["candidate", "reviewed", "ready", "blocked"]
    interactive: bool
    derived_only: Literal[True] = True
    human_review_required: bool = True

    @model_validator(mode="after")
    def validate_provenance_ids(self) -> "CoursewareArtifactV1":
        """Keep source and knowledge bindings deterministic and unambiguous."""
        for field_name in ("source_ids", "knowledge_ids"):
            values = getattr(self, field_name)
            if any(not value.strip() for value in values):
                raise ValueError(f"{field_name} must contain non-empty ids")
            if len(values) != len(set(values)):
                raise ValueError(f"{field_name} must contain unique ids")
        return self
