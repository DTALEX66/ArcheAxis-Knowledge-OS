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

import os
from contextlib import suppress
from pathlib import Path
from typing import Any


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
    external_sources = {"url", "youtube", "rss", "search"}
    if source in external_sources and auto_ingest:
        raise RuntimeError(
            "external pipeline auto-ingest is disabled; use a governed candidate path"
        )
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
    elif source == "file":
        from shared.approved_paths import ApprovedRoots

        configured_roots = os.environ.get("COGNITIVE_APPROVED_SOURCE_ROOTS", "")
        source_roots = [Path(item) for item in configured_roots.split(os.pathsep) if item.strip()]
        if not source_roots:
            raise RuntimeError("file pipeline requires COGNITIVE_APPROVED_SOURCE_ROOTS")
        path = ApprovedRoots(source_roots=source_roots).resolve_source(input_data)
        if not path.is_file():
            raise RuntimeError("file pipeline source must be a regular file")
        if path.stat().st_size > 2_000_000:
            raise RuntimeError("file pipeline source exceeds 2000000 bytes")
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            raise RuntimeError("file pipeline source must be valid UTF-8") from exc
        title = path.stem
        result["stages"]["extract"] = {
            "engine": "approved-local-file",
            "chars": len(content),
        }
    elif source == "youtube":
        from shared.youtube_extractor import get_transcript

        yt = get_transcript(input_data)
        content = yt.get("full_text", "")
        title = yt.get("title", "")
        result["stages"]["extract"] = {"engine": "youtube-transcript", "chars": len(content)}
    elif source == "rss":
        from shared.feed_collector import collect_feeds

        items = collect_feeds([input_data], max_items=5)
        result["stages"]["extract"] = {"engine": "rss", "items": len(items)}
        return result
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
            from knowledge_base.search import vector_search

            vector_search.index_document(kb_id, title + " " + content)
            from shared.backlinks import index_document_links

            index_document_links(kb_id, content)

    # ── Stage 6: Cross-reference ─────────────────────
    # MFX-012: crossref is a credibility heuristic independent of the KB
    # index stage; it must run whenever content exists (kb_id is an index
    # artifact, not a crossref prerequisite).
    if "crossref" in actions and content:
        from shared.cross_reference import score_credibility

        # MFX-012: score_credibility is a legacy domain/keyword heuristic.
        # It is stored only as an internal stage hint (classification
        # 'legacy_heuristic'); it must NEVER be promoted to a 'verified',
        # 'web-verified', or evidence state. Real claim verification uses the
        # EvidenceConnector / obsidian-web-crosscheck pipeline.
        cross_title = title or result["stages"].get("tag", {}).get("keywords", [""])[0]
        cred = score_credibility(
            {"title": cross_title, "content": content, "url": input_data}
        )
        cred["classification"] = "legacy_heuristic"
        cred["verified"] = False
        result["stages"]["crossref"] = cred

    # ── Stage 7: Public evidence ────────────────────
    # H2: EvidenceConnectors (Crossref/DataCite/OpenAlex/Wikidata) wired
    # into the cross-validation pipeline. Optional action; only runs when
    # explicitly requested. When a DOI is present in the content it is
    # queried directly; otherwise the content is used as an OpenAlex
    # claim-text search. Results are structured hits, never 'verified'.
    if "evidence" in actions and content:
        import re as _re

        from shared.cross_reference import enrich_with_public_sources

        doi_match = _re.search(r"10\.\d{4,9}/[^\s]+", content)
        doi = doi_match.group(0).rstrip(".,;:") if doi_match else None
        evidence = enrich_with_public_sources(doi=doi) if doi else enrich_with_public_sources(
            claim_text=(title or content)[:300]
        )
        evidence["classification"] = "public-evidence"
        evidence["verified"] = False
        evidence["doi"] = doi
        result["stages"]["evidence"] = evidence

    result["kb_id"] = kb_id
    result["title"] = title
    return result
