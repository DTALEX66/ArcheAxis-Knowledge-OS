"""Unified pipeline — one endpoint to rule them all.

Chains the full IR→KB pipeline: discover → extract → recognize → structure → analyze.
Replaces scattered API calls with a single intelligent orchestrator.

Usage:
    POST /pipeline
    {
        "source": "url" | "text" | "youtube" | "file" | "rss" | "search",
        "input": "...",
        "actions": ["extract", "tag", "index", "summarize", "crossref"]  // default: all
    }
"""

from __future__ import annotations

import sys
from contextlib import suppress
from pathlib import Path
from typing import Any

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_PROJECT_ROOT))
sys.path.insert(0, str(_PROJECT_ROOT / "Knowledge-Base"))


def run_pipeline(
    source: str,
    input_data: str,
    actions: list[str] | None = None,
    auto_ingest: bool = True,
) -> dict[str, Any]:
    """Execute a full knowledge pipeline.

    Args:
        source: 'url' | 'text' | 'youtube' | 'file' | 'rss' | 'search'.
        input_data: the URL, text, file path, or search query.
        actions: which pipeline stages to run. Default: all.
        auto_ingest: if True, auto-save results to KB.

    Returns:
        Full pipeline result with each stage's output.
    """
    if actions is None:
        actions = ["extract", "tag", "summarize", "index"]

    result: dict[str, Any] = {"source": source, "input": input_data, "stages": {}}
    content = ""
    title = ""

    # ── Stage 1: Extract ─────────────────────────────
    if source == "url":
        from shared.web_search import extract_content

        ext = extract_content(input_data)
        content = ext.get("content", "")
        title = ext.get("title", "")
        result["stages"]["extract"] = {
            "engine": ext.get("engine"),
            "chars": ext.get("char_count", 0),
        }
    elif source == "text":
        content = input_data
        result["stages"]["extract"] = {"engine": "passthrough", "chars": len(content)}
    elif source == "youtube":
        from shared.youtube_extractor import get_transcript

        yt = get_transcript(input_data)
        content = yt.get("full_text", "")
        title = yt.get("title", "")
        result["stages"]["extract"] = {"engine": "youtube-transcript", "chars": len(content)}
    elif source == "rss":
        from shared.feed_collector import collect_and_ingest

        rss = collect_and_ingest([input_data], max_items=5)
        result["stages"]["extract"] = {"engine": "rss", "items": rss.get("collected", 0)}
        return result  # RSS auto-ingests
    elif source == "search":
        from shared.web_search import search_and_extract

        sr = search_and_extract(input_data, search_limit=3, extract_limit=2)
        result["stages"]["extract"] = {
            "engine": "duckduckgo+trafilatura",
            "results": len(sr.get("extracted", [])),
        }
        if auto_ingest and sr.get("extracted"):
            content = sr["extracted"][0].get("content", "")
            title = sr["extracted"][0].get("title", "")

    if not content:
        return result

    # ── Stage 2: Tag + Recognize ─────────────────────
    if "tag" in actions:
        from shared.auto_tagger import detect_atomicity, extract_keywords, suggest_tags

        tags = suggest_tags(content, max_tags=8)
        keywords = extract_keywords(content, top_k=10)
        atomic = detect_atomicity(content)
        result["stages"]["tag"] = {
            "tags": tags,
            "keywords": [k["keyword"] for k in keywords[:5]],
            "is_atomic": atomic["is_atomic"],
        }

    # ── Stage 3: Summarize ───────────────────────────
    if "summarize" in actions:
        from shared.auto_tagger import progressive_summarize

        summary = progressive_summarize(content)
        result["stages"]["summarize"] = {"executive": summary["layer_4_executive"][:300]}

    # ── Stage 4: Extract Facts ───────────────────────
    if "facts" in actions:
        from shared.fact_extractor import extract_facts

        facts = extract_facts(content, max_facts=10)
        result["stages"]["facts"] = {"count": len(facts), "sample": facts[:5]}

    # ── Stage 5: Index into KB ───────────────────────
    kb_id = ""
    if "index" in actions and auto_ingest:
        import uuid

        from shared.storage import fts5_sync, insert

        if not title:
            keywords = result["stages"].get("tag", {}).get("keywords", [])
            title = keywords[0] if keywords else "Untitled"

        tags = result["stages"].get("tag", {}).get("tags", [])
        doc_id = f"doc_{uuid.uuid4().hex[:12]}"
        doc = {
            "id": doc_id,
            "title": title[:200],
            "content": content[:10000],
            "source": f"pipeline:{source}",
            "tags": tags,
        }
        insert("kb_documents", doc)
        with suppress(Exception):
            fts5_sync("kb_documents", {"id": doc_id, "title": title, "content": content[:10000]})
        kb_id = doc_id
        result["stages"]["index"] = {"kb_id": kb_id, "title": title}

        # Also vector index + wikilinks
        with suppress(Exception):
            from search import vector_search

            vector_search.index_document(kb_id, title + " " + content)
            from shared.backlinks import index_document_links

            index_document_links(kb_id, content)

    # ── Stage 6: Cross-reference ─────────────────────
    if "crossref" in actions and kb_id:
        from shared.cross_reference import score_credibility

        cred = score_credibility({"title": title, "content": content, "url": input_data})
        result["stages"]["crossref"] = cred

    result["kb_id"] = kb_id
    result["title"] = title
    return result
