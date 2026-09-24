"""AXW-020B: Import/Conversion/Derived contracts.

A ConversionRun captures converting one raw asset into a DerivedDocument made
of DerivedBlocks, recording per-block and aggregate LossReport. IDs are stable
(deterministic from the raw asset hash), versions are explicit, and the
run→document→block relation is queryable.
"""
from __future__ import annotations

import json
import sqlite3

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


def test_structured_plugin_manifest_provenance_round_trips(tmp_path) -> None:
    db = tmp_path / "plugin-provenance.sqlite"
    provenance = {
        "id": "ax.builtin.converter.html",
        "version": "1.0.0",
        "content_hash": "f" * 64,
    }
    run = create_conversion_run(
        "d" * 64,
        "article.html",
        [{"kind": "paragraph", "text": "Plugin output", "anchor": {"ordinal": 1}}],
        engine="html-adapter",
        plugin_provenance=provenance,
    )

    store_conversion_run(db, run)

    resolved = resolve_conversion_run(db, run.run_id)
    assert resolved is not None
    assert resolved.plugin_provenance == provenance

    same = create_conversion_run(
        "d" * 64,
        "article.html",
        [{"kind": "paragraph", "text": "Plugin output", "anchor": {"ordinal": 1}}],
        engine="html-adapter",
        plugin_provenance=provenance,
    )
    changed = create_conversion_run(
        "d" * 64,
        "article.html",
        [{"kind": "paragraph", "text": "Plugin output", "anchor": {"ordinal": 1}}],
        engine="html-adapter",
        plugin_provenance={**provenance, "version": "1.0.1"},
    )
    changed_hash = create_conversion_run(
        "d" * 64,
        "article.html",
        [{"kind": "paragraph", "text": "Plugin output", "anchor": {"ordinal": 1}}],
        engine="html-adapter",
        plugin_provenance={**provenance, "content_hash": "0" * 64},
    )
    assert same.run_id == run.run_id
    assert same.document.document_id == run.document.document_id
    assert changed.run_id != run.run_id
    assert changed.document.document_id != run.document.document_id
    assert changed_hash.run_id != run.run_id
    assert changed_hash.document.document_id != run.document.document_id


def test_absent_plugin_provenance_preserves_legacy_receipt_shape(tmp_path) -> None:
    db = tmp_path / "legacy-receipt.sqlite"
    run = create_conversion_run(
        "e" * 64,
        "legacy.txt",
        [{"kind": "paragraph", "text": "Legacy output", "anchor": {"ordinal": 1}}],
        engine="plain-text",
    )

    from app.ingestion.conversion_run import ensure_conversion_run_schema

    ensure_conversion_run_schema(db)
    with sqlite3.connect(db) as connection:
        connection.execute(
            "INSERT INTO conversion_runs "
            "(run_id, raw_sha256, source_name, engine, version, document_json, "
            "loss_report_json, created_at) VALUES (?,?,?,?,?,?,?,?)",
            (
                run.run_id,
                run.raw_sha256,
                run.source_name,
                run.engine,
                run.version,
                json.dumps(
                    {
                        "document_id": run.document.document_id,
                        "raw_sha256": run.document.raw_sha256,
                        "engine": run.document.engine,
                        "version": run.document.version,
                    },
                    sort_keys=True,
                ),
                json.dumps(
                    {
                        "block_count": run.loss_report.block_count,
                        "loss_notes": run.loss_report.loss_notes,
                        "attempted_engines": run.loss_report.attempted_engines,
                        "fallback_reason": run.loss_report.fallback_reason,
                    },
                    sort_keys=True,
                ),
                "legacy",
            ),
        )
        connection.executemany(
            "INSERT INTO derived_blocks "
            "(block_id, run_id, document_id, kind, text, anchor_json) VALUES (?,?,?,?,?,?)",
            [
                (
                    block.block_id,
                    run.run_id,
                    run.document.document_id,
                    block.kind,
                    block.text,
                    json.dumps(block.anchor, sort_keys=True),
                )
                for block in run.blocks
            ],
        )
        connection.commit()
    resolved = resolve_conversion_run(db, run.run_id)
    assert resolved is not None
    assert resolved.plugin_provenance is None


def test_conversion_run_requires_nonempty_blocks() -> None:
    with pytest.raises(ValueError):
        create_conversion_run("d" * 64, "z.pdf", [], engine="markitdown")


def test_conversion_run_replay_is_idempotent_but_conflicts_on_changed_receipt(tmp_path) -> None:
    db = tmp_path / "immutable-conversions.sqlite"
    first = create_conversion_run(
        "e" * 64,
        "stable.pdf",
        [{"kind": "page", "text": "first", "anchor": {"page": 1}}],
        engine="pdfplumber",
        loss_notes=["page 1: image semantics unavailable"],
    )
    store_conversion_run(db, first)
    store_conversion_run(db, first)
    changed = create_conversion_run(
        "e" * 64,
        "stable.pdf",
        [{"kind": "page", "text": "changed", "anchor": {"page": 1}}],
        engine="pdfplumber",
    )
    assert changed.run_id == first.run_id
    with pytest.raises(RuntimeError, match="immutable receipt"):
        store_conversion_run(db, changed)
