"""R6 A05 multiformat execution receipt tests."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.contracts.format_execution_v1 import (
    FallbackInfoV1,
    FormatExecutionReceiptV1,
    QualityFactV1,
)
from app.ingestion.conversion_run import create_conversion_run


def _quality() -> list[QualityFactV1]:
    return [QualityFactV1(name="anchor_match", status="measured", value=True, unit="boolean")]


def test_conversion_run_adapts_to_loss_aware_receipt() -> None:
    run = create_conversion_run(
        "a" * 64,
        "notes.md",
        [{"kind": "paragraph", "text": "hello", "anchor": {"ordinal": 1}}],
        engine="passthrough",
    )
    receipt = FormatExecutionReceiptV1.from_conversion_run(
        run, source_format="md", quality_facts=_quality(), status="partial"
    )
    assert receipt.original.retained is True
    assert receipt.transform.engine == "passthrough"
    assert receipt.structure.block_count == 1
    assert receipt.anchors[0].locator == {"ordinal": 1}
    assert receipt.loss.status == "none"


def test_complete_requires_loss_free_anchored_output_and_no_fallback() -> None:
    run = create_conversion_run(
        "b" * 64,
        "notes.md",
        [{"kind": "paragraph", "text": "hello", "anchor": {"ordinal": 1}}],
        engine="passthrough",
    )
    receipt = FormatExecutionReceiptV1.from_conversion_run(
        run, source_format="md", quality_facts=_quality(), status="complete"
    )
    assert receipt.status == "complete"
    with pytest.raises(ValidationError, match="complete execution cannot use fallback"):
        FormatExecutionReceiptV1.from_conversion_run(
            run,
            source_format="md",
            quality_facts=_quality(),
            status="complete",
            fallback=FallbackInfoV1(
                used=True, attempted_engines=["markitdown"], reason="engine unavailable"
            ),
        )


def test_fallback_and_quality_status_are_explicit() -> None:
    with pytest.raises(ValidationError, match="requires attempted_engines"):
        FallbackInfoV1(used=True)
    with pytest.raises(ValidationError, match="quality_facts"):
        FormatExecutionReceiptV1(
            receipt_id="r1",
            status="unsupported",
            original={"sha256": "c" * 64, "name": "x.bin", "format": "bin", "retained": True},
            transform={"engine": "none", "engine_version": "none", "derived_document_id": "d1"},
            loss={"status": "unknown", "notes": ["no adapter"]},
            structure={"block_count": 0, "block_kinds": []},
            anchors=[],
            quality_facts=[],
            fallback={"used": False},
        )


def test_versioned_schema_is_present_and_has_required_receipt_sections() -> None:
    import json
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    schema = json.loads((root / "packages/contracts/v1/format-execution-receipt.schema.json").read_text(encoding="utf-8"))
    assert schema["properties"]["schema"]["const"] == "archeaxis.format-execution-receipt/v1"
    assert set(("original", "transform", "loss", "structure", "anchors", "quality_facts", "fallback")).issubset(schema["required"])


def test_product_boundary_can_override_source_name_to_avoid_path_leak() -> None:
    run = create_conversion_run(
        "d" * 64,
        r"D:\private\notes.md",
        [{"kind": "paragraph", "text": "hello", "anchor": {"ordinal": 1}}],
        engine="passthrough",
    )
    receipt = FormatExecutionReceiptV1.from_conversion_run(
        run,
        source_name="notes.md",
        source_format="md",
        quality_facts=_quality(),
    )
    assert receipt.original.name == "notes.md"
