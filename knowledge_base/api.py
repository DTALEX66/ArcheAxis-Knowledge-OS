"""Knowledge-Base API — SQLite-backed, v0.4.2.

Route counts are reported live by the mounted Core ``/health`` endpoint.
Full OpenAPI documentation at /docs.
"""

from __future__ import annotations

import time
import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from knowledge_base.cards import KnowledgeCard
from knowledge_base.context_pack import build_context_pack
from knowledge_base.routers.composite import router as composite_router
from knowledge_base.routers.projection import router as projection_router
from knowledge_base.routers.quality import router as quality_router
from knowledge_base.search import hybrid_search, keyword_search, vector_search
from knowledge_base.taskpack import build_taskpack
from shared.config import config, validate_runtime_config
from shared.obsidian_projection import write_projection
from shared.research_boundary import unreviewed_research_references
from shared.storage import count, fts5_sync, insert, select_all, select_one

# ── App setup ────────────────────────────────────────────

validate_runtime_config(config)

app = FastAPI(
    title="Cognitive-Loop-OS Knowledge-Base",
    version="0.4.2",
    description="Knowledge management runtime. Absorbs capabilities from Obsidian, Tana, Notion, Logseq, Roam, Heptabase, Capacities, Anytype, GraphRAG, and Zettelkasten.",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.get("cors.allow_origins", ["*"]),
    allow_methods=config.get("cors.allow_methods", ["GET", "POST"]),
    allow_headers=config.get("cors.allow_headers", ["Authorization", "Content-Type"]),
)
app.include_router(composite_router)
app.include_router(projection_router)
app.include_router(quality_router)

# Templates
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


# ── Middleware: request logging + timing ──────────────────


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    from shared.auth import authenticate_request, authorize_request

    user = authenticate_request(
        request.url.path,
        request.headers.get("X-API-Key", ""),
        request.headers.get("Authorization", ""),
    )
    if not user:
        return JSONResponse(
            status_code=401,
            content={
                "error": "unauthorized",
                "detail": "Valid API key or token required. Use X-API-Key header.",
            },
        )
    canonical_path = f"/kb{request.url.path}"
    if not authorize_request(user, request.method, canonical_path):
        return JSONResponse(
            status_code=403,
            content={"error": "forbidden", "detail": "role is not authorized for this operation"},
        )
    request.state.identity = user
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
    environment = str(config.get("app.environment", "development")).lower()
    detail = str(exc)[:200] if environment not in {"production", "prod"} else "request failed"
    return JSONResponse(
        status_code=500,
        content={"error": "internal_error", "detail": detail},
    )


class DocumentIn(BaseModel):
    title: str
    content: str
    source: str = "unknown"
    tags: list[str] = []


class CardRequest(BaseModel):
    title: str
    content: str
    source_ids: list[str] = []
    tags: list[str] = []


class ContextPackRequest(BaseModel):
    goal: str
    sources: list[str] = []
    constraints: list[str] = []


def _reject_unreviewed_research_references(references: list[str]) -> None:
    if unreviewed_research_references(references):
        raise HTTPException(
            status_code=409,
            detail="candidate or external sources require server-owned Phase 5 review provenance",
        )


class TaskPackRequest(BaseModel):
    goal: str
    steps: list[dict] = []
    allowed_tools: list[str] = ["echo", "file_read"]
    risk_level: str = "low"


@app.get("/health")
def health():
    return {"status": "ok", "system": "knowledge-base"}


@app.post("/documents")
def create_document(doc: DocumentIn):
    _reject_unreviewed_research_references([doc.source])
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
    _reject_unreviewed_research_references(req.source_ids)
    card = KnowledgeCard(
        card_id=f"card_{uuid.uuid4().hex[:12]}",
        title=req.title,
        content=req.content,
        source_ids=req.source_ids,
        tags=req.tags,
    )
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
    _reject_unreviewed_research_references(req.sources)
    ctx = build_context_pack(goal=req.goal, sources=req.sources, constraints=req.constraints)
    insert("kb_context_packs", ctx.to_dict())
    return ctx.to_dict()


@app.get("/context-packs")
def list_context_packs(limit: int = 20):
    return {"count": count("kb_context_packs"), "items": select_all("kb_context_packs", limit)}


@app.post("/taskpack")
def create_taskpack(req: TaskPackRequest):
    task = build_taskpack(
        goal=req.goal, steps=req.steps, allowed_tools=req.allowed_tools, risk_level=req.risk_level
    )
    insert("kb_taskpacks", task.to_dict())
    return task.to_dict()


@app.get("/taskpacks")
def list_taskpacks(limit: int = 20):
    return {"count": count("kb_taskpacks"), "items": select_all("kb_taskpacks", limit)}


# ── Dashboard (Web UI) ────────────────────────────────────


@app.get("/", response_class=HTMLResponse)
@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Render the main knowledge dashboard."""
    from shared.knowledge_gardener import find_orphans
    from shared.storage import count as _c
    from shared.storage import select_all

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
            "active_units": sum(
                1 for m in select_all("machine_knowledge_units", limit=200) if m.get("active", True)
            ),
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
    from knowledge_base.mistakes import record_mistake
    from knowledge_base.reviews import schedule_review

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
    from knowledge_base.reviews import get_due_reviews

    items = get_due_reviews(limit=limit)
    return {"count": len(items), "items": items}


@app.get("/reviews/history/{card_id}")
def review_history(card_id: str, limit: int = 20):
    """Return review history for a card."""
    from knowledge_base.reviews import get_review_history

    items = get_review_history(card_id, limit=limit)
    return {"card_id": card_id, "count": len(items), "items": items}


# ── Mistakes (P2-1) ─────────────────────────────────────


class MistakeResolveRequest(BaseModel):
    resolution_note: str = ""


@app.get("/mistakes")
def list_mistakes(limit: int = 50):
    """Return unresolved mistakes."""
    from knowledge_base.mistakes import get_unresolved_mistakes

    items = get_unresolved_mistakes(limit=limit)
    return {"count": len(items), "items": items}


@app.get("/mistakes/patterns")
def mistake_patterns():
    """Analyze mistake patterns and return recommendations."""
    from knowledge_base.mistakes import analyze_patterns

    return analyze_patterns()


@app.post("/mistakes/{mistake_id}/resolve")
def resolve_mistake_endpoint(mistake_id: str, req: MistakeResolveRequest):
    """Mark a mistake as resolved."""
    from knowledge_base.mistakes import resolve_mistake

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
    from knowledge_base.machine_knowledge.a_to_b import find_mastered_cards

    items = find_mastered_cards(limit=limit)
    return {"count": len(items), "items": items}


@app.post("/a-to-b/translate")
def a_to_b_translate(req: TranslateRequest):
    """Create an A→B candidate from a card."""
    from knowledge_base.machine_knowledge.a_to_b import translate_card

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
    from knowledge_base.machine_knowledge.a_to_b import list_candidates

    items = list_candidates("pending")
    return {"count": len(items), "items": items}


@app.post("/a-to-b/publish/{candidate_id}")
def a_to_b_publish(candidate_id: str, confidence: float = 0.7):
    """Publish an A→B candidate as a machine knowledge unit."""
    from knowledge_base.machine_knowledge.a_to_b import publish_candidate

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
    from knowledge_base.machine_knowledge import create_unit

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
    from knowledge_base.machine_knowledge import search_units

    items = search_units(q, limit=limit)
    return {"query": q, "count": len(items), "items": items}


@app.get("/machine-knowledge/{unit_id}")
def machine_knowledge_get(unit_id: str):
    """Get a single machine knowledge unit."""
    from knowledge_base.machine_knowledge import get_unit

    unit = get_unit(unit_id)
    if not unit:
        return {"error": "not found"}
    return unit


@app.get("/machine-knowledge")
def machine_knowledge_list(unit_type: str = "", limit: int = 20):
    """List machine knowledge units, optionally filtered by type."""
    from knowledge_base.machine_knowledge import list_by_type, stats

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
    from knowledge_base.machine_knowledge import deactivate_unit

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


def _required_vault_root(raw: str) -> str:
    if not raw.strip():
        raise HTTPException(status_code=400, detail="vault_root is required")
    return raw


@app.post("/obsidian/scan")
def obsidian_scan(req: ObsidianScanRequest):
    """Scan an Obsidian vault and return categorized inventory (read-only)."""
    from shared.obsidian_importer import scan_vault

    vault = _required_vault_root(req.vault_root)
    return scan_vault(vault, max_files=req.max_files)


@app.post("/obsidian/import")
def obsidian_import(req: ObsidianImportRequest):
    """Import notes from an Obsidian vault into KB (dry-run by default)."""
    from shared.obsidian_importer import import_vault

    vault = _required_vault_root(req.vault_root)
    folders = req.folders if req.folders else None
    return import_vault(vault, folders=folders, max_files=req.max_files, dry_run=True)


@app.post("/obsidian/import/apply")
def obsidian_import_apply(req: ObsidianImportRequest):
    """Import notes from Obsidian vault (real write)."""
    from shared.obsidian_importer import import_vault

    vault = _required_vault_root(req.vault_root)
    folders = req.folders if req.folders else None
    return import_vault(vault, folders=folders, max_files=req.max_files, dry_run=False)


@app.post("/obsidian/import/course")
def obsidian_import_course(vault_root: str = "", course_path: str = "", dry_run: bool = True):
    """Import a single course folder as KB cards."""
    from shared.obsidian_importer import import_course_to_cards

    vault = _required_vault_root(vault_root)
    return import_course_to_cards(vault, course_path, dry_run=dry_run)


@app.post("/obsidian/project/card/{card_id}")
def obsidian_project_card(card_id: str, vault_root: str = "", dry_run: bool = True):
    """Project a KB card to Obsidian markdown."""
    from shared.obsidian_projection import render_card

    card = select_one("kb_cards", card_id)
    if not card:
        return {"error": "card not found"}
    proj = render_card(card)
    return write_projection(proj, vault_root=vault_root, dry_run=dry_run)


@app.post("/obsidian/project/review/{card_id}")
def obsidian_project_review(card_id: str, vault_root: str = "", dry_run: bool = True):
    """Project a card with review history to Obsidian."""
    from knowledge_base.reviews import get_review_history
    from shared.obsidian_projection import render_review_card

    card = select_one("kb_cards", card_id)
    if not card:
        return {"error": "card not found"}
    reviews = get_review_history(card_id, limit=20)
    proj = render_review_card(card, reviews)
    return write_projection(proj, vault_root=vault_root, dry_run=dry_run)


@app.post("/obsidian/project/mku/{unit_id}")
def obsidian_project_mku(unit_id: str, vault_root: str = "", dry_run: bool = True):
    """Project a machine knowledge unit to Obsidian."""
    from shared.obsidian_projection import render_machine_knowledge

    unit = select_one("machine_knowledge_units", unit_id)
    if not unit:
        return {"error": "unit not found"}
    proj = render_machine_knowledge(unit)
    return write_projection(proj, vault_root=vault_root, dry_run=dry_run)


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

    result = query(query_str)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@app.get("/daily")
def daily_note(day: str = ""):
    """Read a daily note without creating it."""
    from shared.daily_notes import get_daily

    note = get_daily(day)
    if note is None:
        raise HTTPException(status_code=404, detail="daily note not found")
    return note


@app.post("/daily")
def daily_note_create(day: str = ""):
    """Create the requested daily note if it does not exist."""
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
    import json

    from shared.object_types import register_type

    props = json.loads(properties) if properties else None
    result = register_type(name, parent=parent, description=description, properties=props)
    return result


@app.post("/types/validate")
def validate_object(obj_type: str = "", data: str = "{}"):
    """Validate an object against its type schema."""
    import json

    from shared.object_types import validate

    obj_data = json.loads(data)
    return validate(obj_type, obj_data)


# ── Absorbed from Logseq/Roam: Block References ──────────


@app.get("/blocks/resolve")
def resolve_block_ref(ref: str = ""):
    """Resolve a block reference like 'doc_001#introduction'."""
    from shared.block_refs import embed_block

    result = embed_block(ref)
    if not result:
        return {"error": "block not found", "ref": ref}
    return result


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

    try:
        return render_view(
            table,
            view_type=view_type,
            group_by=group_by or "review_status",
            limit=limit,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/views/{table}/aggregate")
def collection_aggregate(
    table: str = "kb_cards",
    group_by: str = "review_status",
    func: str = "count",
):
    """Aggregate data like Notion rollups."""
    from shared.collection_views import aggregate

    try:
        return aggregate(table, group_by=group_by, aggregate_func=func)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


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

    try:
        return add_card(canvas_id, object_id, object_type, x=x, y=y)
    except ValueError as exc:
        if "server-owned Phase 5 review provenance" in str(exc):
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        raise


@app.post("/canvas/{canvas_id}/connect")
def canvas_add_connection(
    canvas_id: str,
    source_node_id: str = "",
    target_node_id: str = "",
    label: str = "",
):
    """Add a connection between two cards on a canvas."""
    from shared.canvas import add_connection

    try:
        return add_connection(canvas_id, source_node_id, target_node_id, label)
    except ValueError as exc:
        if "server-owned Phase 5 review provenance" in str(exc):
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        raise


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
    """Reject the retired feed-to-research-note persistence bypass."""
    del urls, categories, max_items
    raise HTTPException(
        status_code=409,
        detail="Legacy feed ingestion is disabled; use a governed candidate path",
    )


@app.post("/ir/youtube/transcript")
def ir_youtube_transcript(url: str = "", languages: str = ""):
    """Fetch YouTube video transcript."""
    from shared.youtube_extractor import get_transcript

    langs = [lang.strip() for lang in languages.split(",") if lang.strip()] if languages else None
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
    import json

    from shared.cross_reference import cross_reference

    src_list = json.loads(sources)
    cr = cross_reference(src_list)
    return cr


@app.post("/ir/fuse")
def ir_fuse_sources(sources: str = "[]"):
    """Fuse multiple sources into unified knowledge summary."""
    import json

    from shared.cross_reference import fuse_sources

    src_list = json.loads(sources)
    return fuse_sources(src_list)


@app.post("/ir/credibility")
def ir_score_credibility(title: str = "", content: str = "", url: str = ""):
    """Score a source's credibility."""
    from shared.cross_reference import score_credibility

    return score_credibility({"title": title, "content": content, "url": url})


# ── Adapted from Obsidian-Assistance v6/v7/v8 ─────────────


@app.get("/evidence/{doc_id}")
def evidence_get(doc_id: str):
    """Get all evidence for a document + health score."""
    from shared.evidence_index import evidence_health, get_evidence

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
    from shared.source_discovery import discover_sources

    discovery = discover_sources(root_dir, max_files=max_files)
    return discovery


@app.post("/sources/match")
def sources_match(source_dir: str = ""):
    """Match discovered sources to existing KB cards."""
    from shared.source_discovery import match_sources_to_cards

    return match_sources_to_cards(source_dir)


@app.get("/diversity/radar")
def diversity_radar(limit: int = 20):
    """Content diversity radar (richest → text_only)."""
    from shared.diversity_audit import diversity_radar

    return {"items": diversity_radar(limit=limit)}


@app.get("/diversity/{doc_id}")
def diversity_analyze(doc_id: str):
    """Analyze content modality diversity for a document."""
    from shared.diversity_audit import analyze_diversity

    return analyze_diversity(doc_id)


@app.get("/mermaid/flowchart")
def mermaid_flowchart(title: str = "", steps: str = "[]"):
    """Generate Mermaid flowchart from steps JSON."""
    import json

    from shared.mermaid_gen import flowchart

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
