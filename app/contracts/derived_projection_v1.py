"""Read-only derived retrieval/graph/research projection receipt contract."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ProjectionItemV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_id: str = Field(min_length=1)
    source_revision: str = Field(min_length=1)
    score: float = Field(ge=0, le=1)
    anchor_id: str | None = None


class DerivedProjectionReceiptV1(BaseModel):
    """A rebuildable, non-canonical result of retrieval or graph projection."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    schema_: Literal["archeaxis.derived-projection/v1"] = Field(
        default="archeaxis.derived-projection/v1", alias="schema"
    )
    projection_id: str = Field(min_length=1)
    projection_kind: Literal["fts", "embedding", "reranked", "graph", "hybrid", "research"]
    query: str = Field(min_length=1)
    algorithm: str = Field(min_length=1)
    algorithm_version: str = Field(min_length=1)
    canonical_source_ids: list[str] = Field(min_length=1)
    items: list[ProjectionItemV1] = Field(default_factory=list)
    generated_at: str = Field(min_length=1)
    rebuildable: Literal[True] = True
    writes_canonical: Literal[False] = False

    @model_validator(mode="after")
    def validate_projection_sources(self) -> "DerivedProjectionReceiptV1":
        allowed = set(self.canonical_source_ids)
        unknown = sorted({item.source_id for item in self.items} - allowed)
        if unknown:
            raise ValueError(f"projection item references unknown canonical sources: {unknown}")
        if len(set(self.canonical_source_ids)) != len(self.canonical_source_ids):
            raise ValueError("canonical_source_ids must be unique")
        return self
