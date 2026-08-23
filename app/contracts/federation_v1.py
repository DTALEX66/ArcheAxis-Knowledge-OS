"""Federation V1 contracts — ArcheAxis-owned stable exchange objects.

Per TP-20260819 §6.1, ArcheAxis owns: KnowledgeQueryV1, KnowledgeProjectionV1,
CandidateSubmissionV1, CandidateReceiptV1, EvidenceIntakeV1, LearningRecordV1,
ProvenanceRecordV1, RightsRecordV1. These are the machine-readable boundary for
cross-project federation (WORK-LAB / DESIGN-LAB call these; they never write
core tables directly).
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

FEDERATION_SCHEMA_NS = "https://archeaxis.local/contracts/federation/v1"


# ── Knowledge Query / Projection ─────────────────────────────────────

class KnowledgeQueryV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = ""  # empty = list-all within kind filter
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    kind: Literal["verified", "candidate", "all"] = "verified"
    source_ref: str | None = None


class KnowledgeProjectionV1(BaseModel):
    """Verified knowledge readback with evidence anchors (paginated)."""

    model_config = ConfigDict(extra="forbid")

    query: str
    page: int
    page_size: int
    total: int
    items: list[dict[str, Any]] = Field(default_factory=list)


# ── Candidate Submission / Receipt ───────────────────────────────────

class CandidateSubmissionItemV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item_key: str = Field(min_length=1)          # stable per-item id within submission
    claim: str = Field(min_length=1)
    source_ref: str = Field(min_length=1)        # e.g. provenance://... or file hash
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    kind: str = "fact"                            # fact | rule | concept | standard
    rights: str = "unspecified"


class CandidateSubmissionV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    idempotency_key: str = Field(min_length=1)
    submitter: str = Field(min_length=1)          # permission identity (caller id)
    items: list[CandidateSubmissionItemV1] = Field(min_length=1, max_length=200)
    note: str | None = None


class CandidateReceiptV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    submission_id: str
    idempotency_key: str
    status: Literal["accepted", "rejected", "duplicate"]
    accepted: int = 0
    rejected: int = 0
    items_hash: str = Field(min_length=1)         # hash readback anchor
    created_at: str = ""


class ReviewDecisionV1(BaseModel):
    """An identity-bound, optimistic-concurrency review decision.

    The actor comes from the authenticated local desktop session; this payload
    repeats it so the service can persist a complete immutable review event.
    """

    model_config = ConfigDict(extra="forbid")

    decision: Literal["verified", "rejected", "disputed", "deprecated", "revoked"]
    reviewer_id: str = Field(min_length=1, max_length=256)
    rationale: str = Field(min_length=1, max_length=4096)
    expected_version: int = Field(ge=1)
    idempotency_key: str = Field(min_length=1, max_length=256)


# ── Evidence / Learning / Provenance / Rights ────────────────────────

class EvidenceIntakeV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evidence_id: str = Field(min_length=1)
    source_ref: str = Field(min_length=1)
    anchor: dict[str, Any] = Field(default_factory=dict)   # page/region/timecode
    content_hash: str = Field(min_length=1)
    rights: str = "unspecified"
    verified: bool = False


class LearningRecordV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    record_id: str = Field(min_length=1)
    concept: str = Field(min_length=1)
    kind: Literal["review", "quiz", "teach_back", "mastery"] = "review"
    outcome: dict[str, Any] = Field(default_factory=dict)
    source_ref: str = Field(min_length=1)


class ProvenanceRecordV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    record_id: str = Field(min_length=1)
    entity_id: str = Field(min_length=1)
    event: Literal["created", "promoted", "revoked", "superseded"]
    actor: str = Field(min_length=1)
    at: str = Field(min_length=1)
    parent_id: str | None = None
    reason: str | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def correction_events_keep_their_audit_chain(self) -> ProvenanceRecordV1:
        if self.event in {"revoked", "superseded"}:
            if not self.parent_id:
                raise ValueError(f"{self.event} provenance event requires parent_id")
            if not self.reason:
                raise ValueError(f"{self.event} provenance event requires reason")
        return self


class RightsRecordV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    record_id: str = Field(min_length=1)
    entity_id: str = Field(min_length=1)
    rights: str = Field(min_length=1)
    scope: str = "internal"
    source_ref: str | None = None


# ── External Asset Record (AA-P1-001) ────────────────────────────────

class ExternalAssetRecordV1(BaseModel):
    """Registry row for external assets — records only, NEVER copies the file."""

    model_config = ConfigDict(extra="forbid")

    asset_id: str = Field(min_length=1)
    uri: str = Field(min_length=1)                # source location (not stored content)
    hash: str = Field(min_length=1)
    media_type: str = "application/octet-stream"
    source: str = Field(min_length=1)
    rights: str = "unspecified"
    extraction: dict[str, Any] = Field(default_factory=dict)  # engine/params/derived ids
    derived_ids: list[str] = Field(default_factory=list)
    created_at: str = ""
