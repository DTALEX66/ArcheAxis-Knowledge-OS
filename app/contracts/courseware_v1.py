"""R6 A10 courseware and interactive learning artifact contract."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


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
