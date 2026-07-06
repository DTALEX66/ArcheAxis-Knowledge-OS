"""Block-level references — absorbed from Logseq + Roam Research.

Enables referencing specific paragraphs/sections within documents,
not just the whole document.  Like:
- Logseq: block references ((block-id)) and block embeds
- Roam: block references with nested context

Block IDs use heading-based anchors: `doc_id#heading-slug` or
auto-generated paragraph IDs.

Usage:
    from shared.block_refs import extract_blocks, resolve_block_ref
    blocks = extract_blocks(content)           # → [{id, heading, text}, ...]
    block = resolve_block_ref("doc_001#intro") # → specific block content
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_PROJECT_ROOT))


def _slugify(text: str) -> str:
    """Convert heading text to URL-like slug."""
    slug = re.sub(r"[^\w\s-]", "", text.lower())
    slug = re.sub(r"\s+", "-", slug)
    return slug[:60]


def extract_blocks(content: str, source_id: str = "") -> list[dict[str, Any]]:
    """Extract block-level sections from markdown content.

    Splits on headings (##, ###) and assigns each block an ID.
    Block IDs: source_id#heading-slug or source_id#p{N} for paragraphs.

    Returns:
        List of {block_id, heading, text, level, start_char, end_char}.
    """
    blocks = []
    # Split on markdown headings while preserving them
    sections = re.split(r"\n(?=#{1,4}\s)", content)
    para_idx = 0

    for section in sections:
        section = section.rstrip()
        if not section:
            continue

        # Extract heading level and text
        heading_match = re.match(r"^(#{1,4})\s+(.+)", section, re.MULTILINE)
        if heading_match:
            level = len(heading_match.group(1))
            heading = heading_match.group(2).strip()
            block_id = f"{source_id}#{_slugify(heading)}" if source_id else _slugify(heading)
        else:
            level = 0
            heading = ""
            para_idx += 1
            block_id = f"{source_id}#p{para_idx}" if source_id else f"p{para_idx}"

        blocks.append({
            "block_id": block_id,
            "heading": heading,
            "level": level,
            "text": section[:1000],
            "char_count": len(section),
        })

    return blocks


def resolve_block_ref(ref: str) -> dict[str, Any] | None:
    """Resolve a block reference like 'doc_001#introduction'.

    Looks up the source document and extracts the specific block.

    Returns:
        {block_id, heading, text, source_doc} or None.
    """
    if "#" not in ref:
        return None

    source_id, _, anchor = ref.partition("#")
    if not source_id or not anchor:
        return None

    from shared.storage import select_one

    doc = select_one("kb_documents", source_id)
    if not doc:
        doc = select_one("kb_cards", source_id)
    if not doc:
        return None

    blocks = extract_blocks(doc.get("content", ""), source_id)
    for block in blocks:
        if block["block_id"] == ref or block["block_id"].endswith(f"#{anchor}"):
            return {
                "block_id": block["block_id"],
                "heading": block["heading"],
                "text": block["text"][:500],
                "source_title": doc.get("title", ""),
                "source_id": source_id,
            }

    return None


def parse_block_refs(content: str) -> list[str]:
    """Find all block references in content: ((block_id)) or ((doc#anchor)).

    Logseq/Roam style block reference syntax.
    """
    pattern = re.compile(r"\(\(([^)]+)\)\)")
    return [m.group(1) for m in pattern.finditer(content)]


def embed_block(block_ref: str) -> dict[str, Any] | None:
    """Resolve and return a block embed (like Logseq /Block Embed).

    Finds the block and returns it with resolved content.
    """
    block = resolve_block_ref(block_ref)
    if not block:
        return None

    # Also resolve nested block refs
    nested = parse_block_refs(block["text"])
    resolved_nested = []
    for nr in nested[:5]:
        nb = resolve_block_ref(nr)
        if nb:
            resolved_nested.append(nb)

    block["nested_refs"] = resolved_nested
    return block
