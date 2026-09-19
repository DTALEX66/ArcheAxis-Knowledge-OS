"""R6 A09 domain learning pack contract."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class DomainPackV1(BaseModel):
    """Stable domain configuration; content remains canonical and reviewable."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    schema_: Literal["archeaxis.domain-pack/v1"] = Field(
        default="archeaxis.domain-pack/v1", alias="schema"
    )
    pack_id: str = Field(pattern=r"^[a-z][a-z0-9-]+$")
    domain: Literal["general", "math_physics", "programming", "design"]
    version: str = Field(min_length=1)
    title: str = Field(min_length=1)
    status: Literal["contract_only", "content_ready", "runtime_verified"]
    source_policy: Literal["canonical_only", "canonical_plus_reviewed"]
    learning_modes: list[Literal["read", "practice", "problem_solving", "code", "design", "simulation", "teach_back"]] = Field(min_length=1)
    assessment_types: list[Literal["recall", "worked_problem", "code_run", "design_critique", "teach_back", "project"]] = Field(min_length=1)
    canonical_object_types: list[Literal["source", "knowledge", "lesson", "exercise", "assessment"]] = Field(min_length=1)
    entrypoint: str = Field(min_length=1)
