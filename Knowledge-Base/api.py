"""Knowledge-Base API — SQLite-backed, v0.2."""
import sys, uuid
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_PROJECT_ROOT))
sys.path.insert(0, str(_PROJECT_ROOT / "Knowledge-Base"))

from fastapi import FastAPI
from pydantic import BaseModel

from cards import KnowledgeCard
from context_pack import build_context_pack
from taskpack import build_taskpack
from shared.storage import insert, select_all, count

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
    insert("kb_documents", r); return r

@app.get("/documents")
def list_documents(limit: int = 20):
    return {"count": count("kb_documents"), "items": select_all("kb_documents", limit)}

@app.post("/cards")
def create_card(req: CardRequest):
    card = KnowledgeCard(card_id=f"card_{uuid.uuid4().hex[:12]}", title=req.title,
                          content=req.content, source_ids=req.source_ids, tags=req.tags)
    insert("kb_cards", card.to_dict()); return card.to_dict()

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


# ── Obsidian projection ──

from shared.obsidian_projection import (
    render_taskpack, render_trace, render_lesson, render_daily_brief, write_projection,
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
    lessons = [l for l in list_lessons_db(limit=200) if l.get("lesson_id") == lesson_id or l.get("id") == lesson_id]
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
