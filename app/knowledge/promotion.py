"""Explicit approval contracts for Research-to-Knowledge candidate promotion."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ResearchKnowledgeApproval(BaseModel):
    """Auditable human decision required before creating Knowledge candidates."""

    model_config = ConfigDict(extra="forbid")

    approval_id: str = Field(min_length=1)
    package_id: str = Field(min_length=1)
    reviewer_id: str = Field(min_length=1)
    decision: Literal["approved", "rejected", "deprecated"]
    rationale: str = Field(min_length=1)
    reviewed_at: str = Field(min_length=1)
