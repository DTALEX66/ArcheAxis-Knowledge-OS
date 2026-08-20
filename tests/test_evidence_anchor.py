"""AXW-020C: EvidenceAnchor and IndexRevision.

An EvidenceAnchor locates content within a source version — by page, block,
character/region, or source revision. An IndexRevision marks a rebuildable
derived index that must never be presented as the source of truth.
"""
from __future__ import annotations

import pytest

from app.evidence.anchor import (
    build_evidence_anchor,
    mark_index_revision,
    rebuild_index_revision,
    resolve_evidence_anchor,
    store_evidence_anchor,
)


def test_evidence_anchor_supports_page_and_block() -> None:
    anchor = build_evidence_anchor(
        raw_sha256="a" * 64,
        source_revision="rev-1",
        locator={"page": 3, "block": "block_abc"},
    )
    assert anchor.anchor_id.startswith("ev_")
    assert anchor.raw_sha256 == "a" * 64
    assert anchor.source_revision == "rev-1"
    assert anchor.locator == {"page": 3, "block": "block_abc"}


def test_evidence_anchor_supports_char_region() -> None:
    anchor = build_evidence_anchor(
        raw_sha256="b" * 64,
        source_revision="rev-2",
        locator={"char_start": 100, "char_end": 200},
    )
    assert anchor.locator == {"char_start": 100, "char_end": 200}
    assert anchor.source_revision == "rev-2"


def test_evidence_anchor_requires_locator_and_revision() -> None:
    with pytest.raises(ValueError):
        build_evidence_anchor(raw_sha256="c" * 64, source_revision="", locator={})
    with pytest.raises(ValueError):
        build_evidence_anchor(raw_sha256="", source_revision="rev-3", locator={"page": 1})


def test_evidence_anchor_store_and_resolve(tmp_path) -> None:
    db = tmp_path / "anchors.sqlite"
    anchor = build_evidence_anchor("d" * 64, "rev-4", {"page": 1, "block": "block_x"})
    store_evidence_anchor(db, anchor)
    resolved = resolve_evidence_anchor(db, anchor.anchor_id)
    assert resolved is not None
    assert resolved.anchor_id == anchor.anchor_id
    assert resolved.locator == {"page": 1, "block": "block_x"}
    assert resolve_evidence_anchor(db, "ev_missing") is None


def test_evidence_anchor_replay_is_idempotent_but_tampering_conflicts(tmp_path) -> None:
    db = tmp_path / "immutable-anchor.sqlite"
    anchor = build_evidence_anchor("f" * 64, "rev-7", {"page": 2})
    store_evidence_anchor(db, anchor)
    store_evidence_anchor(db, anchor)
    import sqlite3

    with sqlite3.connect(db) as connection:
        connection.execute(
            "UPDATE evidence_anchors SET locator_json=? WHERE anchor_id=?",
            ('{"page":999}', anchor.anchor_id),
        )
        connection.commit()
    with pytest.raises(RuntimeError, match="immutable receipt"):
        store_evidence_anchor(db, anchor)


def test_index_revision_is_rebuildable_but_never_source_of_truth(tmp_path) -> None:
    """An IndexRevision can be rebuilt from the raw source, and it must never
    be presented as the source of truth — its revision records the rebuild so
    a consumer can tell derived index from the original.
    """
    db = tmp_path / "index.sqlite"
    rev = mark_index_revision(
        db, raw_sha256="e" * 64, index_name="fts_blocks", source_revision="rev-5"
    )
    assert rev.revision_id.startswith("idx_")
    assert rev.index_name == "fts_blocks"
    assert rev.source_revision == "rev-5"
    assert rev.rebuild_count == 1

    # Rebuilding produces a new revision with an incremented rebuild count.
    rebuilt = rebuild_index_revision(db, rev.revision_id, "rev-6")
    assert rebuilt is not None
    assert rebuilt.rebuild_count == 2
    assert rebuilt.source_revision == "rev-6"
    # The revision must never claim to BE the source: it points at the raw sha.
    assert rebuilt.raw_sha256 == "e" * 64
    assert rebuilt.index_name == "fts_blocks"


def test_index_revision_requires_raw_source() -> None:
    db = "n/a"  # validation happens before any DB access
    with pytest.raises(ValueError):
        mark_index_revision(db, raw_sha256="", index_name="x", source_revision="r")
