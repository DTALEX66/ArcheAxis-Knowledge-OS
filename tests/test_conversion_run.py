"""AXW-020B: Import/Conversion/Derived contracts.

A ConversionRun captures converting one raw asset into a DerivedDocument made
of DerivedBlocks, recording per-block and aggregate LossReport. IDs are stable
(deterministic from the raw asset hash), versions are explicit, and the
run→document→block relation is queryable.
"""
from __future__ import annotations

import pytest

from app.ingestion.conversion_run import (
    LossReport,
    create_conversion_run,
    resolve_conversion_run,
    store_conversion_run,
)


def test_conversion_run_builds_stable_id_and_blocks() -> None:
    run = create_conversion_run(
        raw_sha256="a" * 64,
        source_name="a.pdf",
        blocks=[
            {"kind": "text", "text": "First block", "anchor": {"page": 1}},
            {"kind": "text", "text": "Second block", "anchor": {"page": 1}},
        ],
        engine="markitdown",
    )
    # Stable ID derived from raw hash + source, not random.
    assert run.run_id.startswith("run_")
    assert run.raw_sha256 == "a" * 64
    assert run.engine == "markitdown"
    assert run.version == 1
    assert len(run.blocks) == 2
    assert run.document.document_id.startswith("derived_")
    # Blocks carry stable per-block IDs and anchors.
    assert run.document.blocks[0].block_id.startswith("block_")
    assert run.document.blocks[0].anchor == {"page": 1}
    # Loss report reflects conversion result.
    assert isinstance(run.loss_report, LossReport)
    assert run.loss_report.block_count == 2


def test_conversion_run_same_input_same_ids() -> None:
    a = create_conversion_run("b" * 64, "x.pdf", [{"kind": "text", "text": "hi"}], engine="pdfplumber")
    b = create_conversion_run("b" * 64, "x.pdf", [{"kind": "text", "text": "hi"}], engine="pdfplumber")
    assert a.run_id == b.run_id
    assert a.document.document_id == b.document.document_id
    assert a.document.blocks[0].block_id == b.document.blocks[0].block_id


def test_conversion_run_store_and_resolve(tmp_path) -> None:
    db = tmp_path / "conversions.sqlite"
    run = create_conversion_run(
        "c" * 64, "y.pdf", [{"kind": "table", "text": "row", "anchor": {"page": 3}}], engine="markitdown"
    )
    store_conversion_run(db, run)

    resolved = resolve_conversion_run(db, run.run_id)
    assert resolved is not None
    assert resolved.run_id == run.run_id
    assert resolved.raw_sha256 == run.raw_sha256
    assert len(resolved.blocks) == 1
    assert resolved.blocks[0].anchor == {"page": 3}
    assert resolved.loss_report.block_count == 1

    # Unknown id resolves to None.
    assert resolve_conversion_run(db, "run_missing") is None


def test_conversion_run_requires_nonempty_blocks() -> None:
    with pytest.raises(ValueError):
        create_conversion_run("d" * 64, "z.pdf", [], engine="markitdown")
