"""Tests for shared.block_refs (Obsidian/Logseq/Roam-style block references)."""

from __future__ import annotations

from shared.block_refs import (
    embed_block,
    extract_blocks,
    parse_block_refs,
    resolve_block_ref,
)


def test_extract_blocks_heading_ids() -> None:
    content = "# Title\nIntro text.\n\n## Introduction\nFirst paragraph.\n\n### Details\nMore detail.\n"
    blocks = extract_blocks(content, source_id="doc_001")
    assert len(blocks) >= 3
    ids = [b["block_id"] for b in blocks]
    assert "doc_001#introduction" in ids
    assert "doc_001#details" in ids
    intro = next(b for b in blocks if b["block_id"] == "doc_001#introduction")
    assert intro["heading"] == "Introduction"
    assert intro["level"] == 2
    assert "First paragraph." in intro["text"]


def test_extract_blocks_paragraph_ids() -> None:
    # Pure-paragraph content (no headings) is one block with a paragraph id.
    content = "First para.\n\nSecond para.\n"
    blocks = extract_blocks(content, source_id="doc_001")
    assert len(blocks) == 1
    assert blocks[0]["block_id"] == "doc_001#p1"

    # With a heading boundary, each heading-less section gets its own p-id.
    mixed = "## Intro\nFirst.\n\n## More\nSecond.\n"
    blocks = extract_blocks(mixed, source_id="doc_001")
    ids = [b["block_id"] for b in blocks]
    assert "doc_001#intro" in ids
    assert "doc_001#more" in ids


def test_extract_blocks_no_source_id() -> None:
    blocks = extract_blocks("## Intro\nText.\n")
    assert blocks[0]["block_id"] == "intro"


def test_resolve_block_ref_heading(monkeypatch) -> None:
    doc = {"id": "doc_001", "title": "Test Doc", "content": "## Introduction\nHello world.\n"}
    monkeypatch.setattr("shared.storage.select_one", lambda table, sid: doc)
    result = resolve_block_ref("doc_001#introduction")
    assert result is not None
    assert result["heading"] == "Introduction"
    assert "Hello world." in result["text"]
    assert result["source_title"] == "Test Doc"


def test_resolve_block_ref_falls_back_to_cards(monkeypatch) -> None:
    calls = []

    def fake_select_one(table, sid):
        calls.append(table)
        if table == "kb_documents":
            return None
        return {"id": "card_1", "title": "Card", "content": "## Notes\nBody.\n"}

    monkeypatch.setattr("shared.storage.select_one", fake_select_one)
    result = resolve_block_ref("card_1#notes")
    assert result is not None
    assert result["source_title"] == "Card"
    assert calls == ["kb_documents", "kb_cards"]


def test_resolve_block_ref_missing_returns_none(monkeypatch) -> None:
    monkeypatch.setattr("shared.storage.select_one", lambda table, sid: None)
    assert resolve_block_ref("doc_999#missing") is None


def test_resolve_block_ref_invalid_format() -> None:
    assert resolve_block_ref("no-anchor") is None
    assert resolve_block_ref("") is None
    assert resolve_block_ref("#anchor-only") is None


def test_parse_block_refs() -> None:
    content = "See ((doc_001#intro)) and ((card_1)) for more."
    refs = parse_block_refs(content)
    assert refs == ["doc_001#intro", "card_1"]


def test_parse_block_refs_empty() -> None:
    assert parse_block_refs("No references here.") == []


def test_embed_block_resolves_nested(monkeypatch) -> None:
    docs = {
        "doc_a": {"id": "doc_a", "title": "A", "content": "## Main\nSee ((doc_b#sub)) here.\n"},
        "doc_b": {"id": "doc_b", "title": "B", "content": "## Sub\nNested content.\n"},
    }
    monkeypatch.setattr("shared.storage.select_one", lambda table, sid: docs.get(sid))
    result = embed_block("doc_a#main")
    assert result is not None
    assert result["heading"] == "Main"
    assert len(result["nested_refs"]) == 1
    assert result["nested_refs"][0]["heading"] == "Sub"


def test_embed_block_missing_returns_none(monkeypatch) -> None:
    monkeypatch.setattr("shared.storage.select_one", lambda table, sid: None)
    assert embed_block("doc_zz#none") is None
