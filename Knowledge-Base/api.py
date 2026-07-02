"""Knowledge-Base API — B线核心资产层独立服务.

Run from Cognitive-Loop-OS root:
  python -m uvicorn Knowledge-Base.api:app --port 8002
"""
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_PROJECT_ROOT))
sys.path.insert(0, str(_PROJECT_ROOT / "Knowledge-Base"))

from fastapi import FastAPI
from pydantic import BaseModel

from cards import KnowledgeCard
from context_pack import build_context_pack, ContextPack
from taskpack import build_taskpack, TaskPack

app = FastAPI(title="Knowledge-Base", version="0.1.0")

# ── In-memory stores (SQLite migration in Phase 2) ──
documents: list[dict] = []
cards: list[KnowledgeCard] = []
context_packs: list[ContextPack] = []
taskpacks: list[TaskPack] = []


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


class TaskPackRequest(BaseModel):
    goal: str
    steps: list[dict] = []
    allowed_tools: list[str] = ["echo", "file_read"]
    risk_level: str = "low"


@app.get("/health")
def health():
    return {"status": "ok", "system": "knowledge-base"}


# ── Documents ──
@app.post("/documents")
def create_document(doc: DocumentIn):
    import uuid
    record = {"id": f"doc_{uuid.uuid4().hex[:12]}", **doc.model_dump()}
    documents.append(record)
    return record


@app.get("/documents")
def list_documents(limit: int = 20):
    return {"count": len(documents), "items": documents[-limit:]}


# ── Cards ──
@app.post("/cards")
def create_card(req: CardRequest):
    import uuid
    card = KnowledgeCard(
        card_id=f"card_{uuid.uuid4().hex[:12]}",
        title=req.title, content=req.content,
        source_ids=req.source_ids, tags=req.tags,
    )
    cards.append(card)
    return card.to_dict()


@app.get("/cards")
def list_cards(limit: int = 20):
    return {"count": len(cards), "items": [c.to_dict() for c in cards[-limit:]]}


# ── ContextPack ──
@app.post("/context-pack")
def create_context_pack(req: ContextPackRequest):
    ctx = build_context_pack(
        goal=req.goal, sources=req.sources, constraints=req.constraints,
    )
    context_packs.append(ctx)
    return ctx.to_dict()


@app.get("/context-packs")
def list_context_packs(limit: int = 20):
    return {"count": len(context_packs), "items": [c.to_dict() for c in context_packs[-limit:]]}


# ── TaskPack ──
@app.post("/taskpack")
def create_taskpack(req: TaskPackRequest):
    task = build_taskpack(
        goal=req.goal, steps=req.steps,
        allowed_tools=req.allowed_tools, risk_level=req.risk_level,
    )
    taskpacks.append(task)
    return task.to_dict()


@app.get("/taskpacks")
def list_taskpacks(limit: int = 20):
    return {"count": len(taskpacks), "items": [t.to_dict() for t in taskpacks[-limit:]]}
