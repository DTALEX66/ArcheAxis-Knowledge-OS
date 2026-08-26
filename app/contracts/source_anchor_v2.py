"""Versioned Source, Anchor, and PROV-O-compatible provenance contracts."""
from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field


class SourceObjectV2(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_id: str = Field(min_length=1)
    version: int = Field(ge=1)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    byte_size: int = Field(ge=0)
    media_type: str = Field(min_length=1)
    rights_status: Literal["owned", "licensed", "public-domain", "permission-recorded"]
    original_retained: Literal[True]
    created_at: str = Field(min_length=1)


class TextQuoteSelector(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["TextQuoteSelector"] = "TextQuoteSelector"
    exact: str = Field(min_length=1)
    prefix: str | None = None
    suffix: str | None = None


class TextPositionSelector(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["TextPositionSelector"] = "TextPositionSelector"
    start: int = Field(ge=0)
    end: int = Field(gt=0)


class FragmentSelector(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["FragmentSelector"] = "FragmentSelector"
    value: str = Field(min_length=1)
    conforms_to: str | None = None


class PdfPageRegionSelector(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["PdfPageRegionSelector"] = "PdfPageRegionSelector"
    page: int = Field(ge=1)
    x: float = Field(ge=0)
    y: float = Field(ge=0)
    width: float = Field(gt=0)
    height: float = Field(gt=0)


class MediaTimeSelector(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["MediaTimeSelector"] = "MediaTimeSelector"
    start_s: float = Field(ge=0)
    end_s: float = Field(gt=0)


AnchorSelector = Annotated[
    TextQuoteSelector | TextPositionSelector | FragmentSelector | PdfPageRegionSelector | MediaTimeSelector,
    Field(discriminator="type"),
]


class AnchorV2(BaseModel):
    model_config = ConfigDict(extra="forbid")

    anchor_id: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    source_version: int = Field(ge=1)
    selector: AnchorSelector
    created_at: str = Field(min_length=1)

    def state_for(self, source: SourceObjectV2) -> Literal["CURRENT", "STALE"]:
        if source.source_id != self.source_id or source.version != self.source_version:
            return "STALE"
        return "CURRENT"


class ProvenanceActivityV2(BaseModel):
    model_config = ConfigDict(extra="forbid")

    activity_id: str = Field(min_length=1)
    activity_type: str = Field(min_length=1)
    used: list[str] = Field(min_length=1)
    generated: list[str] = Field(min_length=1)
    agent: str = Field(min_length=1)
    started_at: str = Field(min_length=1)
    ended_at: str = Field(min_length=1)

    def as_prov(self) -> dict[str, object]:
        return {
            "@context": {"prov": "http://www.w3.org/ns/prov#"},
            "@id": self.activity_id,
            "@type": "prov:Activity",
            "archeaxis:activityType": self.activity_type,
            "prov:used": self.used,
            "prov:generated": self.generated,
            "prov:wasAssociatedWith": self.agent,
            "prov:startedAtTime": self.started_at,
            "prov:endedAtTime": self.ended_at,
        }
