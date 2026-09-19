"""Auditable multiformat execution receipt contract for R6 A05."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class OriginalAssetV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    name: str = Field(min_length=1)
    format: str = Field(min_length=1)
    retained: Literal[True] = True


class TransformInfoV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    engine: str = Field(min_length=1)
    engine_version: str = Field(min_length=1)
    derived_document_id: str = Field(min_length=1)


class LossInfoV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["none", "partial", "unknown"]
    notes: list[str] = Field(default_factory=list)


class StructureInfoV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    block_count: int = Field(ge=0)
    block_kinds: list[str] = Field(default_factory=list)


class AnchorFactV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    block_id: str = Field(min_length=1)
    kind: str = Field(min_length=1)
    locator: dict[str, object]


class QualityFactV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    status: Literal["measured", "unmeasured", "unsupported"]
    value: float | int | bool | None = None
    unit: str | None = None
    note: str | None = None


class FallbackInfoV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    used: bool
    attempted_engines: list[str] = Field(default_factory=list)
    selected_engine: str | None = None
    reason: str | None = None

    @model_validator(mode="after")
    def validate_fallback(self) -> "FallbackInfoV1":
        if self.used and not self.attempted_engines:
            raise ValueError("fallback used requires attempted_engines")
        if self.used and not self.reason:
            raise ValueError("fallback used requires reason")
        return self


class FormatExecutionReceiptV1(BaseModel):
    """One loss-aware, anchor-aware receipt for a format execution."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    schema_: Literal["archeaxis.format-execution-receipt/v1"] = Field(
        default="archeaxis.format-execution-receipt/v1", alias="schema"
    )
    receipt_id: str = Field(min_length=1)
    status: Literal["complete", "partial", "unsupported", "failed"]
    original: OriginalAssetV1
    transform: TransformInfoV1
    loss: LossInfoV1
    structure: StructureInfoV1
    anchors: list[AnchorFactV1]
    quality_facts: list[QualityFactV1] = Field(min_length=1)
    fallback: FallbackInfoV1

    @model_validator(mode="after")
    def validate_execution_semantics(self) -> "FormatExecutionReceiptV1":
        if self.status == "complete":
            if self.loss.status != "none":
                raise ValueError("complete execution cannot have loss status")
            if self.fallback.used:
                raise ValueError("complete execution cannot use fallback")
            if self.structure.block_count < 1 or not self.anchors:
                raise ValueError("complete execution requires structured anchored output")
        if self.status in {"complete", "partial"} and self.structure.block_count < 1:
            raise ValueError("successful execution requires at least one block")
        return self

    @classmethod
    def from_conversion_run(
        cls,
        run: object,
        *,
        source_format: str,
        quality_facts: list[QualityFactV1],
        status: Literal["complete", "partial", "unsupported", "failed"] = "partial",
        fallback: FallbackInfoV1 | None = None,
    ) -> "FormatExecutionReceiptV1":
        """Adapt the existing ConversionRun without changing its storage schema."""
        blocks = list(getattr(run, "blocks"))
        loss_report = getattr(run, "loss_report")
        engine = str(getattr(run, "engine"))
        version = str(getattr(run, "version"))
        loss_notes = list(getattr(loss_report, "loss_notes", []))
        return cls(
            receipt_id=str(getattr(run, "run_id")),
            status=status,
            original=OriginalAssetV1(
                sha256=str(getattr(run, "raw_sha256")),
                name=str(getattr(run, "source_name")),
                format=source_format,
            ),
            transform=TransformInfoV1(
                engine=engine,
                engine_version=version,
                derived_document_id=str(getattr(getattr(run, "document"), "document_id")),
            ),
            loss=LossInfoV1(status="partial" if loss_notes else "none", notes=loss_notes),
            structure=StructureInfoV1(
                block_count=len(blocks),
                block_kinds=sorted({str(getattr(block, "kind")) for block in blocks}),
            ),
            anchors=[
                AnchorFactV1(
                    block_id=str(getattr(block, "block_id")),
                    kind=str(getattr(block, "kind")),
                    locator=dict(getattr(block, "anchor")),
                )
                for block in blocks
            ],
            quality_facts=quality_facts,
            fallback=fallback or FallbackInfoV1(used=False),
        )
