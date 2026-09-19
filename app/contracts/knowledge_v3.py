"""R6 Knowledge/Source V3 governance contracts.

The contract intentionally separates provenance attributes from admission. Human
personal knowledge may be accepted without external evidence; machine candidates
never become verified merely because they carry links or confidence values.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

KNOWLEDGE_SOURCE_TYPES = Literal[
    "personal_experience",
    "personal_note",
    "personal_definition",
    "project_observation",
    "external_document",
    "authoritative_reference",
    "derived_inference",
    "machine_candidate",
    "imported_legacy",
    "research_result",
]
KNOWLEDGE_STATUS = Literal["candidate", "accepted", "verified", "rejected", "superseded"]
SUPPORT_LEVEL = Literal["none", "weak", "moderate", "strong", "authoritative"]
RISK_LEVEL = Literal["low", "medium", "high", "critical"]
OWNER = Literal["human", "machine", "system"]


def _check_dates(valid_from: str | None, valid_to: str | None) -> None:
    if valid_from is None or valid_to is None:
        return
    if datetime.fromisoformat(valid_to) < datetime.fromisoformat(valid_from):
        raise ValueError("valid_to must not precede valid_from")


class _KnowledgeGovernanceV3(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_type: KNOWLEDGE_SOURCE_TYPES
    owner: OWNER
    status: KNOWLEDGE_STATUS
    support_level: SUPPORT_LEVEL = "none"
    # Legacy records may not carry a confidence measurement. Keep that state
    # explicit instead of converting UNKNOWN to a numeric zero.
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    risk_level: RISK_LEVEL = "low"
    valid_from: str | None = None
    valid_to: str | None = None
    supersedes: list[str] = Field(default_factory=list)
    superseded_by: list[str] = Field(default_factory=list)
    external_evidence: list[str] = Field(default_factory=list)
    requires_human_review: bool = True

    @model_validator(mode="after")
    def enforce_r6_governance(self):
        _check_dates(self.valid_from, self.valid_to)
        if self.source_type == "machine_candidate" and self.status not in {
            "candidate",
            "rejected",
            "superseded",
        }:
            raise ValueError("machine_candidate cannot be accepted or verified automatically")
        if self.owner == "machine" and self.source_type != "machine_candidate":
            raise ValueError("machine owner must use source_type=machine_candidate")
        if self.status == "verified" and self.support_level == "none":
            raise ValueError("verified knowledge must declare a support_level")
        if self.status == "verified" and self.requires_human_review:
            raise ValueError("verified knowledge must have completed human review")
        return self


class KnowledgeSourceV3(_KnowledgeGovernanceV3):
    """A source/origin object; evidence is an attribute, not admission gate."""

    schema_version: Literal["3.0.0"]
    source_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    content: str
    source_locator: str | None = None
    created_at: str = Field(min_length=1)


class KnowledgeObjectV3(_KnowledgeGovernanceV3):
    """Canonical knowledge object derived from a source or human experience."""

    schema_version: Literal["3.0.0"]
    knowledge_id: str = Field(min_length=1)
    source_id: str | None = None
    title: str = Field(min_length=1)
    body: str
    created_at: str = Field(min_length=1)
    updated_at: str = Field(min_length=1)
