"""Obsidian-style backlinks engine — parse wikilinks and compute reverse links.

Absorbs Obsidian's core capability: automatic backlink discovery.
Scans content for [[wikilinks]], [[link|alias]], and ![[embeds]],
then builds a reference graph for bidirectional navigation.

Usage:
    from shared.backlinks import parse_links, compute_backlinks
    refs = parse_links(content)         # → [(target, alias, is_embed), ...]
    bl = compute_backlinks("doc_001")    # → [{source_id, snippet}, ...]
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_PROJECT_ROOT))

# ── Wikilink patterns ───────────────────────────────────

# [[target]] or [[target|alias]]
_WIKILINK_RE = re.compile(r"\[\[([^\]|#]+?)(?:\|[^\]]+?)?(?:#[^\]]+?)?\]\]")

# ![[embed]]
_EMBED_RE = re.compile(r"!\[\[([^\]]+?)\]\]")

# Markdown [text](url)
_MD_LINK_RE = re.compile(r"\[([^\]]*)\]\(([^)]+)\)")


def parse_links(content: str) -> list[dict[str, Any]]:
    """Parse all wikilinks, embeds, and markdown links from content.

    Returns:
        List of {target, alias, is_embed, link_type}.
    """
    results = []

    # Wikilinks: [[target]] or [[target|alias]]
    for match in _WIKILINK_RE.finditer(content):
        target = match.group(1).strip()
        # Fix spaces (Obsidian uses %20 in filenames)
        target = target.replace("%20", " ")
        results.append(
            {
                "target": target,
                "alias": target,
                "is_embed": False,
                "link_type": "wikilink",
            }
        )

    # Embeds: ![[target]]
    for match in _EMBED_RE.finditer(content):
        target = match.group(1).strip().replace("%20", " ")
        results.append(
            {
                "target": target,
                "alias": target,
                "is_embed": True,
                "link_type": "embed",
            }
        )

    # Markdown links: [text](url)
    for match in _MD_LINK_RE.finditer(content):
        alias = match.group(1)
        url = match.group(2)
        if url and not url.startswith(("http://", "https://", "#")):
            results.append(
                {
                    "target": url,
                    "alias": alias or url,
                    "is_embed": False,
                    "link_type": "md_link",
                }
            )

    return results


def index_document_links(doc_id: str, content: str) -> int:
    """Parse and store all outgoing links from a document.

    Args:
        doc_id: the source document ID.
        content: the document body text.

    Returns:
        Number of links indexed.
    """
    from shared.storage import insert

    links = parse_links(content)
    count = 0
    for link in links:
        import uuid

        lid = f"link_{uuid.uuid4().hex[:12]}"
        insert(
            "kb_links",
            {
                "id": lid,
                "source_id": doc_id,
                "target_id": link["target"],
                "link_type": link["link_type"],
                "alias": link["alias"],
                "is_embed": 1 if link["is_embed"] else 0,
            },
        )
        count += 1

    return count


def compute_backlinks(target_id: str, limit: int = 50) -> list[dict[str, Any]]:
    """Find all documents that link TO the given target.

    Equivalent to Obsidian's backlinks pane.
    """
    from shared.storage import select_all, select_one

    all_links = select_all("kb_links", limit=2000)
    backlinks = []

    for link in all_links:
        if link.get("target_id") == target_id:
            source = select_one("kb_documents", link["source_id"])
            if not source:
                source = select_one("kb_cards", link["source_id"])
            backlinks.append(
                {
                    "source_id": link["source_id"],
                    "source_title": source.get("title", "") if source else "",
                    "link_type": link.get("link_type", "wikilink"),
                    "alias": link.get("alias", ""),
                    "snippet": (source.get("content", "") if source else "")[:200],
                }
            )

    return backlinks[:limit]


def compute_graph(limit: int = 200) -> dict[str, Any]:
    """Compute the full link graph for visualization.

    Returns nodes (documents/cards) and edges (links between them).
    """
    from shared.storage import select_all

    all_links = select_all("kb_links", limit=2000)
    all_docs = {d["id"]: d for d in select_all("kb_documents", limit=500)}
    all_cards = {c["id"]: c for c in select_all("kb_cards", limit=500)}

    nodes: dict[str, dict] = {}
    edges: list[dict] = []

    for link in all_links[:limit]:
        sid = link["source_id"]
        tid = link["target_id"]

        # Add source node
        if sid not in nodes:
            src = all_docs.get(sid) or all_cards.get(sid) or {}
            nodes[sid] = {
                "id": sid,
                "title": src.get("title", sid)[:60],
                "type": "card" if sid in all_cards else "document",
            }

        # Add target node (may be unresolved — that's OK)
        if tid not in nodes:
            tgt = all_docs.get(tid) or all_cards.get(tid) or {}
            nodes[tid] = {
                "id": tid,
                "title": tgt.get("title", tid)[:60],
                "type": "card" if tid in all_cards else "document",
            }

        edges.append(
            {
                "source": sid,
                "target": tid,
                "link_type": link.get("link_type", "wikilink"),
            }
        )

    return {
        "nodes": list(nodes.values())[:limit],
        "edges": edges[:limit],
    }
