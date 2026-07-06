"""Knowledge-Base API — SQLite-backed, v0.2."""
import sys
import uuid
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_PROJECT_ROOT))
sys.path.insert(0, str(_PROJECT_ROOT / "Knowledge-Base"))

from cards import KnowledgeCard
from context_pack import build_context_pack
from fastapi import FastAPI
from pydantic import BaseModel
from search import hybrid_search, keyword_search, vector_search
from taskpack import build_taskpack

from shared.storage import count, fts5_sync, insert, select_all

app = FastAPI(title="Knowledge-Base", version="0.2.0")


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
    # Auto-index for FTS5 + vector search
    try:
        fts5_sync("kb_documents", {"id": r["id"], "title": r["title"], "content": r["content"]})
        vector_search.index_document(r["id"], r["title"] + " " + r["content"])
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


# ── Obsidian projection ──

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
