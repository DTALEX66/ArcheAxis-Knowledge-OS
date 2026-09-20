"""R6 A08 human learning kernel exposure and schedule receipt."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class LearningKernelReceiptV1(BaseModel):
    """One human exposure with source provenance and deterministic FSRS output."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    schema_: Literal["archeaxis.learning-kernel/v1"] = Field(
        default="archeaxis.learning-kernel/v1", alias="schema"
    )
    item_key: str = Field(min_length=1)
    question_version: str = Field(min_length=1)
    knowledge_version: str = Field(min_length=1)
    source_anchor_ids: list[str] = Field(min_length=1)
    exposure_id: str = Field(min_length=1)
    client_event_id: str = Field(min_length=1)
    correct: bool
    rating: int = Field(ge=1, le=4)
    state_before: Literal["new", "learning", "review", "relearning"]
    state_after: Literal["new", "learning", "review", "relearning"]
    due_before: str | None = None
    due_after: str | None = None
    scheduled_days: int = Field(ge=0)
    scheduler: Literal["fsrs"]
    scheduler_version: str = Field(min_length=1)
    restart_key: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_review_semantics(self) -> LearningKernelReceiptV1:
        if len(set(self.source_anchor_ids)) != len(self.source_anchor_ids):
            raise ValueError("source_anchor_ids must be unique")
        if self.correct and self.rating == 1:
            raise ValueError("correct exposure cannot use rating 1")
        if not self.correct and self.rating != 1:
            raise ValueError("incorrect exposure must use rating 1")
        if self.restart_key != self.client_event_id:
            raise ValueError("restart_key must equal client_event_id for idempotent replay")
        return self
