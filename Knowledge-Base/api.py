"""Knowledge-Base API — SQLite-backed, v0.4.0.

102 endpoints across 14 tag groups.
Full OpenAPI documentation at /docs.
"""

from __future__ import annotations

import sys
import time
import uuid
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_PROJECT_ROOT))
sys.path.insert(0, str(_PROJECT_ROOT / "Knowledge-Base"))

from cards import KnowledgeCard
from context_pack import build_context_pack
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from search import hybrid_search, keyword_search, vector_search
from taskpack import build_taskpack

from shared.storage import count, fts5_sync, insert, select_all

# ── App setup ────────────────────────────────────────────

app = FastAPI(
    title="Cognitive-Loop-OS Knowledge-Base",
    version="0.4.0",
    description="102-endpoint knowledge management runtime. Absorbs capabilities from Obsidian, Tana, Notion, Logseq, Roam, Heptabase, Capacities, Anytype, GraphRAG, and Zettelkasten.",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Templates
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


# ── Middleware: request logging + timing ──────────────────


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = round((time.time() - start) * 1000, 1)
    response.headers["X-Process-Time-ms"] = str(duration)
    from shared.logging import logger
    logger.debug(f"{request.method} {request.url.path} → {response.status_code} ({duration}ms)")
    return response


# ── Global exception handler ─────────────────────────────


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    from shared.logging import logger
    logger.error(f"Unhandled error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": "internal_error", "detail": str(exc)[:200]},
    )


class DocumentIn(BaseModel):
    title: str; content: str; source: str = "unknown"; tags: list[str] = []

class CardRequest(BaseModel):
    title: str; content: str; source_ids: list[str] = []; tags: list[str] = []

class ContextPackRequest(BaseModel):
    goal: str; sources: list[str] = []; constraints: list[str] = []

class TaskPackRequest(BaseModel):
    goal: str; steps: list[dict] = []
    allowed_tools: list[str] = ["echo", "file_read"]; risk_level: str = "low"


@app.get("/health")
def health(): return {"status": "ok", "system": "knowledge-base"}

@app.post("/documents")
def create_document(doc: DocumentIn):
    r = {"id": f"doc_{uuid.uuid4().hex[:12]}", **doc.model_dump()}
    insert("kb_documents", r)
    # Auto-index for FTS5 + vector search + backlinks
    try:
        fts5_sync("kb_documents", {"id": r["id"], "title": r["title"], "content": r["content"]})
        vector_search.index_document(r["id"], r["title"] + " " + r["content"])
        from shared.backlinks import index_document_links
        index_document_links(r["id"], r["content"])
    except Exception:
        pass  # non-critical
    return r

@app.get("/documents")
def list_documents(limit: int = 20):
    return {"count": count("kb_documents"), "items": select_all("kb_documents", limit)}

@app.post("/cards")
def create_card(req: CardRequest):
    card = KnowledgeCard(card_id=f"card_{uuid.uuid4().hex[:12]}", title=req.title,
                          content=req.content, source_ids=req.source_ids, tags=req.tags)
    insert("kb_cards", card.to_dict())
    # Auto-index for FTS5 + vector search
    try:
        fts5_sync("kb_cards", {"id": card.card_id, "title": card.title, "content": card.content})
        vector_search.index_card(card.card_id, card.title + " " + card.content)
    except Exception:
        pass
    return card.to_dict()

@app.get("/cards")
def list_cards(limit: int = 20):
    return {"count": count("kb_cards"), "items": select_all("kb_cards", limit)}

@app.post("/context-pack")
def create_context_pack(req: ContextPackRequest):
    ctx = build_context_pack(goal=req.goal, sources=req.sources, constraints=req.constraints)
    insert("kb_context_packs", ctx.to_dict()); return ctx.to_dict()

@app.get("/context-packs")
def list_context_packs(limit: int = 20):
    return {"count": count("kb_context_packs"), "items": select_all("kb_context_packs", limit)}

@app.post("/taskpack")
def create_taskpack(req: TaskPackRequest):
    task = build_taskpack(goal=req.goal, steps=req.steps, allowed_tools=req.allowed_tools, risk_level=req.risk_level)
    insert("kb_taskpacks", task.to_dict()); return task.to_dict()

@app.get("/taskpacks")
def list_taskpacks(limit: int = 20):
    return {"count": count("kb_taskpacks"), "items": select_all("kb_taskpacks", limit)}


# ── Dashboard (Web UI) ────────────────────────────────────


@app.get("/", response_class=HTMLResponse)
@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Render the main knowledge dashboard."""
    from shared.storage import count as _c, select_all
    from shared.knowledge_gardener import find_orphans

    docs = select_all("kb_documents", limit=10)
    cards = select_all("kb_cards", limit=10)
    mkus = select_all("machine_knowledge_units", limit=10)
    reviews_due_list = select_all("kb_reviews", limit=10, order="next_review_at ASC")
    daily_list = select_all("daily_notes", limit=7, order="date DESC")
    canvas_list = select_all("canvases", limit=10)
    orphans = find_orphans(limit=10)

    ctx = {
        "stats": {
            "documents": _c("kb_documents"),
            "cards": _c("kb_cards"),
            "reviews": _c("kb_reviews"),
            "mistakes": _c("kb_mistakes"),
            "mku": _c("machine_knowledge_units"),
            "daily_notes": _c("daily_notes"),
            "graph_nodes": _c("graph_entities"),
            "orphans": len(orphans),
            "active_units": sum(1 for m in select_all("machine_knowledge_units", limit=200) if m.get("active", True)),
        },
        "recent_cards": cards,
        "recent_mku": mkus,
        "due_reviews": reviews_due_list,
        "canvases": canvas_list,
        "daily_timeline": daily_list,
    }
    return templates.TemplateResponse(request=request, name="dashboard.html", context=ctx)


# ── Search ───────────��────────────────────────────────

class SearchRequest(BaseModel):
    query: str
    top_k: int = 5
    mode: str = "hybrid"  # "hybrid" | "vector" | "keyword"


@app.post("/search")
def search(req: SearchRequest):
    """Unified search endpoint: vector + keyword hybrid by default.

    Modes:
    - ``hybrid``: combine sqlite-vec vector search with LIKE keyword search
    - ``vector``: sqlite-vec semantic search only
    - ``keyword``: LIKE-based keyword search only
    """
    if req.mode == "vector":
        items = vector_search.search_all(req.query, top_k=req.top_k)
        return {"query": req.query, "mode": "vector", "count": len(items), "items": items}
    elif req.mode == "keyword":
        items = keyword_search(req.query, top_k=req.top_k)
        return {"query": req.query, "mode": "keyword", "count": len(items), "items": items}
    else:
        items = hybrid_search(req.query, top_k=req.top_k)
        return {"query": req.query, "mode": "hybrid", "count": len(items), "items": items}


@app.get("/search/stats")
def search_stats():
    """Return vector index statistics."""
    return vector_search.stats()


@app.post("/search/rebuild")
def search_rebuild():
    """Drop and recreate all vector indexes."""
    return vector_search.rebuild_index()


# ── Review (P2-1) ───────────────────────────────────────


class ReviewRequest(BaseModel):
    card_id: str
    quality: int  # 0-5
    error_type: str = ""  # optional mistake tracking
    error_detail: str = ""
    source_topic: str = ""


@app.post("/reviews")
def create_review(req: ReviewRequest):
    """Record a card review with SM-2 spacing.

    Returns the review record with next review date.
    If quality < 3, automatically records a mistake.
    """
    from reviews import schedule_review
    from mistakes import record_mistake

    result = schedule_review(req.card_id, req.quality)

    # Auto-record mistake for low-quality reviews
    if req.quality < 3 and req.error_type:
        mistake = record_mistake(
            req.card_id,
            error_type=req.error_type or "recall_failure",
            detail=req.error_detail,
            source_topic=req.source_topic,
        )
        result["mistake"] = mistake

    return result


@app.get("/reviews/due")
def due_reviews(limit: int = 20):
    """Return cards due for review."""
    from reviews import get_due_reviews

    items = get_due_reviews(limit=limit)
    return {"count": len(items), "items": items}


@app.get("/reviews/history/{card_id}")
def review_history(card_id: str, limit: int = 20):
    """Return review history for a card."""
    from reviews import get_review_history

    items = get_review_history(card_id, limit=limit)
    return {"card_id": card_id, "count": len(items), "items": items}


# ── Mistakes (P2-1) ─────────────────────────────────────


class MistakeResolveRequest(BaseModel):
    resolution_note: str = ""


@app.get("/mistakes")
def list_mistakes(limit: int = 50):
    """Return unresolved mistakes."""
    from mistakes import get_unresolved_mistakes

    items = get_unresolved_mistakes(limit=limit)
    return {"count": len(items), "items": items}


@app.get("/mistakes/patterns")
def mistake_patterns():
    """Analyze mistake patterns and return recommendations."""
    from mistakes import analyze_patterns

    return analyze_patterns()


@app.post("/mistakes/{mistake_id}/resolve")
def resolve_mistake_endpoint(mistake_id: str, req: MistakeResolveRequest):
    """Mark a mistake as resolved."""
    from mistakes import resolve_mistake

    result = resolve_mistake(mistake_id, req.resolution_note)
    if not result:
        return {"error": "not found"}
    return result


# ── Phase 5: A→B Translation ────────────────────────────

class TranslateRequest(BaseModel):
    card_id: str
    unit_type: str = "rule"
    override_title: str = ""
    override_content: str = ""


@app.get("/a-to-b/candidates")
def a_to_b_candidates(limit: int = 20):
    """Find cards mastered enough for A→B translation."""
    from machine_knowledge.a_to_b import find_mastered_cards

    items = find_mastered_cards(limit=limit)
    return {"count": len(items), "items": items}


@app.post("/a-to-b/translate")
def a_to_b_translate(req: TranslateRequest):
    """Create an A→B candidate from a card."""
    from machine_knowledge.a_to_b import translate_card

    result = translate_card(
        req.card_id,
        unit_type=req.unit_type,
        override_title=req.override_title,
        override_content=req.override_content,
    )
    return result


@app.get("/a-to-b/pending")
def a_to_b_pending():
    """List pending A→B candidates."""
    from machine_knowledge.a_to_b import list_candidates

    items = list_candidates("pending")
    return {"count": len(items), "items": items}


@app.post("/a-to-b/publish/{candidate_id}")
def a_to_b_publish(candidate_id: str, confidence: float = 0.7):
    """Publish an A→B candidate as a machine knowledge unit."""
    from machine_knowledge.a_to_b import publish_candidate

    return publish_candidate(candidate_id, confidence=confidence)


# ── Machine Knowledge ───────────────────────────────────

class MachineKnowledgeCreateRequest(BaseModel):
    title: str
    content: str = ""
    unit_type: str = "rule"
    tags: list[str] = []
    confidence: float = 0.5


@app.post("/machine-knowledge")
def machine_knowledge_create(req: MachineKnowledgeCreateRequest):
    """Create a machine knowledge unit manually."""
    from machine_knowledge import create_unit

    return create_unit(
        title=req.title,
        content=req.content,
        unit_type=req.unit_type,
        tags=req.tags,
        confidence=req.confidence,
    )


@app.get("/machine-knowledge/search")
def machine_knowledge_search(q: str = "", limit: int = 20):
    """Search machine knowledge units."""
    from machine_knowledge import search_units

    items = search_units(q, limit=limit)
    return {"query": q, "count": len(items), "items": items}


@app.get("/machine-knowledge/{unit_id}")
def machine_knowledge_get(unit_id: str):
    """Get a single machine knowledge unit."""
    from machine_knowledge import get_unit

    unit = get_unit(unit_id)
    if not unit:
        return {"error": "not found"}
    return unit


@app.get("/machine-knowledge")
def machine_knowledge_list(unit_type: str = "", limit: int = 20):
    """List machine knowledge units, optionally filtered by type."""
    from machine_knowledge import list_by_type, stats

    if unit_type:
        items = list_by_type(unit_type, limit=limit)
    else:
        from shared.storage import select_all

        items = select_all("machine_knowledge_units", limit=limit)

    return {
        "count": len(items),
        "items": items,
        "stats": stats(),
    }


@app.post("/machine-knowledge/{unit_id}/deactivate")
def machine_knowledge_deactivate(unit_id: str):
    """Deactivate a machine knowledge unit."""
    from machine_knowledge import deactivate_unit

    result = deactivate_unit(unit_id)
    if not result:
        return {"error": "not found"}
    return result


# ── Obsidian bridge (Phase 6) ────────────────────────────

class ObsidianScanRequest(BaseModel):
    vault_root: str = ""
    max_files: int = 200


class ObsidianImportRequest(BaseModel):
    vault_root: str = ""
    folders: list[str] = []
    max_files: int = 50


@app.post("/obsidian/scan")
def obsidian_scan(req: ObsidianScanRequest):
    """Scan an Obsidian vault and return categorized inventory (read-only)."""
    from shared.obsidian_importer import scan_vault

    vault = req.vault_root or "E:/BaiduSyncdisk/Obsidian知识库"
    return scan_vault(vault, max_files=req.max_files)


@app.post("/obsidian/import")
def obsidian_import(req: ObsidianImportRequest):
    """Import notes from an Obsidian vault into KB (dry-run by default)."""
    from shared.obsidian_importer import import_vault

    vault = req.vault_root or "E:/BaiduSyncdisk/Obsidian知识库"
    folders = req.folders if req.folders else None
    return import_vault(vault, folders=folders, max_files=req.max_files, dry_run=True)


@app.post("/obsidian/import/apply")
def obsidian_import_apply(req: ObsidianImportRequest):
    """Import notes from Obsidian vault (real write)."""
    from shared.obsidian_importer import import_vault

    vault = req.vault_root or "E:/BaiduSyncdisk/Obsidian知识库"
    folders = req.folders if req.folders else None
    return import_vault(vault, folders=folders, max_files=req.max_files, dry_run=False)


@app.post("/obsidian/import/course")
def obsidian_import_course(vault_root: str = "", course_path: str = "", dry_run: bool = True):
    """Import a single course folder as KB cards."""
    from shared.obsidian_importer import import_course_to_cards

    vault = vault_root or "E:/BaiduSyncdisk/Obsidian知识库"
    return import_course_to_cards(vault, course_path, dry_run=dry_run)


@app.post("/obsidian/project/card/{card_id}")
def obsidian_project_card(card_id: str, dry_run: bool = True):
    """Project a KB card to Obsidian markdown."""
    from shared.obsidian_projection import render_card

    card = select_one("kb_cards", card_id)
    if not card:
        return {"error": "card not found"}
    proj = render_card(card)
    return write_projection(proj, dry_run=dry_run)


@app.post("/obsidian/project/review/{card_id}")
def obsidian_project_review(card_id: str, dry_run: bool = True):
    """Project a card with review history to Obsidian."""
    from shared.obsidian_projection import render_review_card
    from reviews import get_review_history

    card = select_one("kb_cards", card_id)
    if not card:
        return {"error": "card not found"}
    reviews = get_review_history(card_id, limit=20)
    proj = render_review_card(card, reviews)
    return write_projection(proj, dry_run=dry_run)


@app.post("/obsidian/project/mku/{unit_id}")
def obsidian_project_mku(unit_id: str, dry_run: bool = True):
    """Project a machine knowledge unit to Obsidian."""
    from shared.obsidian_projection import render_machine_knowledge

    unit = select_one("machine_knowledge_units", unit_id)
    if not unit:
        return {"error": "unit not found"}
    proj = render_machine_knowledge(unit)
    return write_projection(proj, dry_run=dry_run)


# ── Obsidian-absorbed: Backlinks + Graph + Dataview + Daily ──


@app.get("/backlinks/{target_id}")
def backlinks(target_id: str, limit: int = 50):
    """Find all documents/cards that link TO the target (reverse links)."""
    from shared.backlinks import compute_backlinks

    items = compute_backlinks(target_id, limit=limit)
    return {"target": target_id, "count": len(items), "items": items}


@app.get("/graph")
def graph_view(center: str = "", depth: int = 2):
    """Return the knowledge graph (nodes + edges) for visualization."""
    from shared.dataview import query_graph

    return query_graph(center_id=center, depth=depth)


@app.post("/dataview/query")
def dataview_query(query_str: str = ""):
    """Dataview-style query: FROM <table> WHERE <cond> SORT <field> LIMIT N."""
    from shared.dataview import query

    return query(query_str)


@app.get("/daily")
def daily_note(day: str = ""):
    """Get or create today's daily note."""
    from shared.daily_notes import get_or_create_daily

    return get_or_create_daily(day)


@app.post("/daily/append")
def daily_append(content: str = "", day: str = "", heading: str = ""):
    """Append content to a daily note."""
    from shared.daily_notes import append_to_daily

    return append_to_daily(content, day=day, heading=heading)


@app.get("/daily/timeline")
def daily_timeline(days: int = 7):
    """Return daily notes for the last N days."""
    from shared.daily_notes import timeline

    items = timeline(days=days)
    return {"days": days, "count": len(items), "items": items}


# ── Absorbed from Tana/Capacities: Object Types ──────────


@app.get("/types")
def list_object_types():
    """List all registered object types with their property schemas."""
    from shared.object_types import list_types

    return {"types": list_types()}


@app.get("/types/{type_name}")
def get_object_type(type_name: str):
    """Get property schema for a specific type."""
    from shared.object_types import get_property_schema

    schema = get_property_schema(type_name)
    if not schema.get("properties"):
        return {"error": "type not found"}
    return schema


@app.post("/types")
def register_object_type(
    name: str = "",
    parent: str = "document",
    description: str = "",
    properties: str = "{}",  # JSON string
):
    """Register a custom object type (like Tana Supertag)."""
    from shared.object_types import register_type
    import json

    props = json.loads(properties) if properties else None
    result = register_type(name, parent=parent, description=description, properties=props)
    return result


@app.post("/types/validate")
def validate_object(obj_type: str = "", data: str = "{}"):
    """Validate an object against its type schema."""
    from shared.object_types import validate
    import json

    obj_data = json.loads(data)
    return validate(obj_type, obj_data)


# ── Absorbed from Logseq/Roam: Block References ──────────


@app.get("/blocks/{source_id}")
def extract_blocks(source_id: str):
    """Extract block-level sections from a document."""
    from shared.block_refs import extract_blocks
    from shared.storage import select_one

    doc = select_one("kb_documents", source_id)
    if not doc:
        doc = select_one("kb_cards", source_id)
    if not doc:
        return {"error": "document not found"}

    blocks = extract_blocks(doc.get("content", ""), source_id)
    return {"source_id": source_id, "count": len(blocks), "blocks": blocks}


@app.get("/blocks/resolve")
def resolve_block_ref(ref: str = ""):
    """Resolve a block reference like 'doc_001#introduction'."""
    from shared.block_refs import resolve_block_ref, embed_block

    result = embed_block(ref)
    if not result:
        return {"error": "block not found", "ref": ref}
    return result


# ── Absorbed from Notion: Collection Views ───────────────


@app.get("/views/{table}")
def collection_view(
    table: str = "kb_cards",
    view_type: str = "table",
    group_by: str = "",
    limit: int = 50,
):
    """Render a collection view (table/board/calendar/gallery/list)."""
    from shared.collection_views import render_view

    return render_view(
        table, view_type=view_type,
        group_by=group_by or "review_status",
        limit=limit,
    )


@app.get("/views/{table}/aggregate")
def collection_aggregate(
    table: str = "kb_cards",
    group_by: str = "review_status",
    func: str = "count",
):
    """Aggregate data like Notion rollups."""
    from shared.collection_views import aggregate

    return aggregate(table, group_by=group_by, aggregate_func=func)


# ── Absorbed from Heptabase: Canvas / Whiteboard ─────────


@app.post("/canvas")
def create_canvas_endpoint(name: str = "", description: str = ""):
    """Create a new canvas/whiteboard."""
    from shared.canvas import create_canvas

    return create_canvas(name, description)


@app.get("/canvas")
def list_canvases_endpoint():
    """List all canvases."""
    from shared.canvas import list_canvases

    return {"canvases": list_canvases()}


@app.get("/canvas/{canvas_id}")
def get_canvas_endpoint(canvas_id: str):
    """Get a canvas with all its cards and connections."""
    from shared.canvas import get_canvas

    result = get_canvas(canvas_id)
    if not result:
        return {"error": "canvas not found"}
    return result


@app.post("/canvas/{canvas_id}/card")
def canvas_add_card(
    canvas_id: str,
    object_id: str = "",
    object_type: str = "card",
    x: float = 0,
    y: float = 0,
):
    """Place a card on a canvas."""
    from shared.canvas import add_card

    return add_card(canvas_id, object_id, object_type, x=x, y=y)


@app.post("/canvas/{canvas_id}/connect")
def canvas_add_connection(
    canvas_id: str,
    source_node_id: str = "",
    target_node_id: str = "",
    label: str = "",
):
    """Add a connection between two cards on a canvas."""
    from shared.canvas import add_connection

    return add_connection(canvas_id, source_node_id, target_node_id, label)


@app.delete("/canvas/{canvas_id}")
def delete_canvas_endpoint(canvas_id: str):
    """Delete a canvas and all its contents."""
    from shared.canvas import delete_canvas

    ok = delete_canvas(canvas_id)
    return {"deleted": ok}


# ── Enhancement: Auto-tagger ─────────────────────────────


@app.post("/auto/tags")
def auto_tags(text: str = "", top_k: int = 10):
    """Extract keywords and suggest tags from text."""
    from shared.auto_tagger import extract_keywords, suggest_tags

    return {
        "keywords": extract_keywords(text, top_k=top_k),
        "suggested_tags": suggest_tags(text, max_tags=top_k),
    }


@app.post("/auto/atomicity")
def auto_atomicity(text: str = ""):
    """Check if a note is atomic (Zettelkasten single-idea)."""
    from shared.auto_tagger import detect_atomicity

    return detect_atomicity(text)


@app.post("/auto/summarize")
def auto_summarize(text: str = ""):
    """Generate 4-layer progressive summary."""
    from shared.auto_tagger import progressive_summarize

    return progressive_summarize(text)


# ── Enhancement: Knowledge Gardener ──────────────────────


@app.get("/garden/orphans")
def garden_orphans(limit: int = 50):
    """Find orphaned notes with no links."""
    from shared.knowledge_gardener import find_orphans

    return {"orphans": find_orphans(limit=limit)}


@app.get("/garden/suggest/{doc_id}")
def garden_suggest_connections(doc_id: str, top_k: int = 5):
    """Suggest connections for a document."""
    from shared.knowledge_gardener import suggest_connections

    return {"suggestions": suggest_connections(doc_id, top_k=top_k)}


@app.get("/garden/gaps")
def garden_gaps():
    """Detect knowledge gaps (thin topics)."""
    from shared.knowledge_gardener import detect_gaps

    return detect_gaps()


@app.get("/garden/evergreen/{doc_id}")
def garden_evergreen(doc_id: str):
    """Score how evergreen a note is."""
    from shared.knowledge_gardener import score_evergreen

    return score_evergreen(doc_id)


# ── Enhancement: GraphRAG ────────────────────────────────


@app.post("/graphrag/index")
def graphrag_index():
    """Index all KB entities into graph + vector for GraphRAG."""
    from shared.graph_rag import index_for_graphrag

    result = index_for_graphrag()
    return {"status": "indexed", "stats": result}


@app.post("/graphrag/search")
def graphrag_search(query: str = "", top_k: int = 5, max_hops: int = 2):
    """GraphRAG multi-hop search: vector + graph traversal."""
    from shared.graph_rag import graph_rag_search

    return graph_rag_search(query, top_k=top_k, max_hops=max_hops)


# ── IR Pipeline: Search → Extract → Analyze ──────────────


@app.post("/ir/search")
def ir_web_search(query: str = "", limit: int = 5):
    """Search the web (DuckDuckGo, no API key)."""
    from shared.web_search import search_web

    return search_web(query, limit=limit)


@app.post("/ir/extract")
def ir_extract_content(url: str = "", max_chars: int = 10000):
    """Extract clean content from a URL."""
    from shared.web_search import extract_content

    return extract_content(url, max_chars=max_chars)


@app.post("/ir/search-and-extract")
def ir_search_and_extract(query: str = "", search_limit: int = 3, extract_limit: int = 2):
    """Search + extract top results in one call."""
    from shared.web_search import search_and_extract

    return search_and_extract(query, search_limit=search_limit, extract_limit=extract_limit)


@app.post("/ir/feeds")
def ir_collect_feeds(urls: str = "", categories: str = "", max_items: int = 10):
    """Collect articles from RSS/Atom feeds."""
    from shared.feed_collector import collect_feeds, discover_feeds, collect_and_ingest

    if urls:
        url_list = [u.strip() for u in urls.split(",") if u.strip()]
    elif categories:
        cat_list = [c.strip() for c in categories.split(",")]
        discovered = discover_feeds(cat_list)
        url_list = []
        for feeds in discovered.values():
            url_list.extend(feeds)
    else:
        url_list = [
            "https://arxiv.org/rss/cs.AI",
            "https://huggingface.co/blog/feed.xml",
        ]

    return collect_and_ingest(url_list, max_items=max_items)


@app.post("/ir/youtube/transcript")
def ir_youtube_transcript(url: str = "", languages: str = ""):
    """Fetch YouTube video transcript."""
    from shared.youtube_extractor import get_transcript

    langs = [l.strip() for l in languages.split(",") if l.strip()] if languages else None
    return get_transcript(url, languages=langs)


@app.post("/ir/youtube/search")
def ir_youtube_search(query: str = "", max_results: int = 5):
    """Search YouTube via RSS feed (no API key)."""
    from shared.youtube_extractor import search_youtube

    results = search_youtube(query, max_results=max_results)
    return {"query": query, "count": len(results), "results": results}


@app.post("/ir/facts")
def ir_extract_facts(text: str = "", max_facts: int = 20):
    """Extract subject-predicate-object triples from text."""
    from shared.fact_extractor import extract_facts, text_to_knowledge_graph

    facts = extract_facts(text, max_facts=max_facts)
    graph = text_to_knowledge_graph(text)
    return {"facts": facts, "knowledge_graph": graph}


@app.post("/ir/cross-reference")
def ir_cross_reference(sources: str = "[]"):
    """Cross-reference multiple sources for agreements/contradictions."""
    from shared.cross_reference import cross_reference, fuse_sources
    import json

    src_list = json.loads(sources)
    cr = cross_reference(src_list)
    return cr


@app.post("/ir/fuse")
def ir_fuse_sources(sources: str = "[]"):
    """Fuse multiple sources into unified knowledge summary."""
    from shared.cross_reference import fuse_sources
    import json

    src_list = json.loads(sources)
    return fuse_sources(src_list)


@app.post("/ir/credibility")
def ir_score_credibility(title: str = "", content: str = "", url: str = ""):
    """Score a source's credibility."""
    from shared.cross_reference import score_credibility

    return score_credibility({"title": title, "content": content, "url": url})


# ── Adapted from Obsidian-Assistance v6/v7/v8 ─────────────


@app.post("/evidence")
def evidence_add(
    doc_id: str = "",
    source_type: str = "manual",
    source_path: str = "",
    confidence: str = "medium",
    caption: str = "",
):
    """Add an evidence record for a KB asset."""
    from shared.evidence_index import index_evidence

    return index_evidence(doc_id, source_type=source_type,
                          source_path=source_path, confidence=confidence, caption=caption)


@app.get("/evidence/{doc_id}")
def evidence_get(doc_id: str):
    """Get all evidence for a document + health score."""
    from shared.evidence_index import get_evidence, evidence_health

    return {
        "evidence": get_evidence(doc_id),
        "health": evidence_health(doc_id),
    }


@app.get("/health/radar")
def health_radar():
    """Global KB evidence health radar (adapted from v6)."""
    from shared.evidence_index import vault_health_radar

    return vault_health_radar()


@app.get("/analytics/streak")
def analytics_streak(days: int = 30):
    """Learning streak and stats (adapted from v8)."""
    from shared.learning_analytics import review_streak

    return review_streak(days=days)


@app.get("/analytics/heatmap")
def analytics_heatmap(limit: int = 20):
    """Topic activity heatmap."""
    from shared.learning_analytics import topic_heatmap

    return {"topics": topic_heatmap(limit=limit)}


@app.get("/retro/weekly")
def retro_weekly(days: int = 7):
    """Weekly retrospective summary (adapted from v8)."""
    from shared.retro_summary import weekly_summary

    return weekly_summary(days=days)


@app.get("/missions/daily")
def missions_daily():
    """Auto-generate daily learning missions (adapted from v8)."""
    from shared.retro_summary import generate_daily_missions

    return generate_daily_missions()


@app.post("/projects/generate")
def projects_generate(topic: str = "", difficulty: str = "medium"):
    """Generate a project taskpack from mastered topic (adapted from v7)."""
    from shared.project_generator import generate_project_from_topic

    return generate_project_from_topic(topic, difficulty=difficulty)


@app.get("/projects/suggest")
def projects_suggest(limit: int = 5):
    """Suggest project-worthy topics."""
    from shared.project_generator import suggest_projects

    return {"suggestions": suggest_projects(limit=limit)}


# ── Adapted from Obsidian-Assistance v4/v5/v6 ─────────────


@app.post("/media/inventory")
def media_inventory(source_dir: str = ""):
    """Scan a directory for PDFs and videos."""
    from shared.media_extractor import media_inventory

    return media_inventory(source_dir)


@app.post("/sources/discover")
def sources_discover(root_dir: str = "", max_files: int = 100):
    """Discover evidence source files in a directory."""
    from shared.source_discovery import discover_sources, match_sources_to_cards

    discovery = discover_sources(root_dir, max_files=max_files)
    return discovery


@app.post("/sources/match")
def sources_match(source_dir: str = ""):
    """Match discovered sources to existing KB cards."""
    from shared.source_discovery import match_sources_to_cards

    return match_sources_to_cards(source_dir)


@app.get("/diversity/{doc_id}")
def diversity_analyze(doc_id: str):
    """Analyze content modality diversity for a document."""
    from shared.diversity_audit import analyze_diversity

    return analyze_diversity(doc_id)


@app.get("/diversity/radar")
def diversity_radar(limit: int = 20):
    """Content diversity radar (richest → text_only)."""
    from shared.diversity_audit import diversity_radar

    return {"items": diversity_radar(limit=limit)}


@app.get("/mermaid/flowchart")
def mermaid_flowchart(title: str = "", steps: str = "[]"):
    """Generate Mermaid flowchart from steps JSON."""
    from shared.mermaid_gen import flowchart
    import json

    step_list = json.loads(steps)
    return {"mermaid": flowchart(title, step_list)}


@app.get("/mermaid/graph")
def mermaid_graph(center_id: str = "", max_nodes: int = 20):
    """Generate Mermaid knowledge graph."""
    from shared.mermaid_gen import knowledge_graph_mermaid

    return {"mermaid": knowledge_graph_mermaid(center_id, max_nodes=max_nodes)}


@app.get("/mermaid/timeline/{card_id}")
def mermaid_timeline(card_id: str):
    """Generate Mermaid review timeline for a card."""
    from shared.mermaid_gen import review_timeline_mermaid

    return {"mermaid": review_timeline_mermaid(card_id)}


# ── Obsidian projection (legacy) ──

from shared.obsidian_projection import (
    render_daily_brief,
    render_lesson,
    render_taskpack,
    render_trace,
    write_projection,
)
from shared.storage import select_one


@app.post("/project/taskpack/{task_id}")
def project_taskpack(task_id: str, dry_run: bool = True):
    task = select_one("kb_taskpacks", task_id)
    if not task:
        return {"error": "not found"}
    proj = render_taskpack(task)
    return write_projection(proj, dry_run=dry_run)


@app.post("/project/trace/{trace_id}")
def project_trace(trace_id: str, dry_run: bool = True):
    from app.memory.database import list_traces_db
    traces = [t for t in list_traces_db(limit=200) if t.get("trace_id") == trace_id or t.get("id") == trace_id]
    if not traces:
        return {"error": "not found"}
    proj = render_trace(traces[0])
    return write_projection(proj, dry_run=dry_run)


@app.post("/project/lesson/{lesson_id}")
def project_lesson(lesson_id: str, dry_run: bool = True):
    from app.memory.database import list_lessons_db
    lessons = [ll for ll in list_lessons_db(limit=200) if ll.get("lesson_id") == lesson_id or ll.get("id") == lesson_id]
    if not lessons:
        return {"error": "not found"}
    proj = render_lesson(lessons[0])
    return write_projection(proj, dry_run=dry_run)


@app.post("/project/daily-brief/{brief_id}")
def project_brief(brief_id: str, dry_run: bool = True):
    brief = select_one("ir_daily_briefs", brief_id)
    if not brief:
        return {"error": "not found"}
    proj = render_daily_brief(brief)
    return write_projection(proj, dry_run=dry_run)
