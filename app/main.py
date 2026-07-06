"""Cognitive-OS v2 — unified runtime for the Cognitive Loop.

Port 8000: Core OS (route → execute → trace → eval → lesson)
Port 8000/kb: Knowledge-Base (102 endpoints, dashboard, all capabilities)

Start: uvicorn app.main:app --host 0.0.0.0 --port 8000
Then:  http://localhost:8000/docs     — Core API
       http://localhost:8000/kb/docs   — Knowledge-Base API
       http://localhost:8000/kb        — Dashboard
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_PROJECT_ROOT))
sys.path.insert(0, str(_PROJECT_ROOT / "Knowledge-Base"))

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# ── Core app ─────────────────────────────────────────────

app = FastAPI(
    title="Cognitive-Loop-OS",
    version="0.4.0",
    description="AI cognitive runtime with 102-endpoint Knowledge-Base. "
    "Absorbs Obsidian, Tana, Notion, Logseq, Roam, Heptabase, GraphRAG, Zettelkasten.",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()

    # ── Auth check (skip allowlist) ──
    from shared.auth import requires_auth, verify_token
    if requires_auth(request.url.path):
        api_key = request.headers.get("X-API-Key", "")
        auth_header = request.headers.get("Authorization", "")
        token = auth_header.replace("Bearer ", "") if auth_header.startswith("Bearer ") else ""

        user = verify_token(token or api_key)
        if not user:
            return JSONResponse(
                status_code=401,
                content={"error": "unauthorized", "detail": "Valid API key or token required. Use X-API-Key header."},
            )

    response = await call_next(request)
    duration = round((time.time() - start) * 1000, 1)
    response.headers["X-Process-Time-ms"] = str(duration)
    return response
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"error": "internal_error", "detail": str(exc)[:200]},
    )


# ── Mount Knowledge-Base as sub-app ──────────────────────

# Import KB app (handles hyphen in dir name)
import importlib.util

_kb_spec = importlib.util.spec_from_file_location(
    "kb_api", str(_PROJECT_ROOT / "Knowledge-Base" / "api.py")
)
_kb_mod = importlib.util.module_from_spec(_kb_spec)
_kb_spec.loader.exec_module(_kb_mod)
app.mount("/kb", _kb_mod.app)


# ── Core endpoints ───────────────────────────────────────

from app.agent.executor import execute
from app.api.ingest import ingest
from app.core.compiler import compile_task
from app.core.permissions import check_permission
from app.core.router import route
from app.core.trace import list_traces, log_trace
from app.evaluation.evaluator import evaluate
from app.evaluation.feedback import compile_lesson
from app.ingestion.file import IngestionError, ingest_directory, ingest_file
from app.ingestion.multi_format import convert_directory as multi_convert_directory
from app.ingestion.multi_format import convert_file, convert_url
from app.memory.store import list_lessons, save_lesson, save_memory, search_memory
from app.tools.registry import list_tools


@app.get("/health")
def health():
    """Comprehensive system health check."""
    from shared.storage import count as _c

    return {
        "status": "ok",
        "system": "cognitive-loop-os",
        "version": "0.4.0",
        "endpoints": {
            "core": 11,
            "kb": 102,
            "total": 113,
        },
        "stats": {
            "documents": _c("kb_documents"),
            "cards": _c("kb_cards"),
            "reviews": _c("kb_reviews"),
            "machine_knowledge": _c("machine_knowledge_units"),
            "graph_nodes": _c("graph_entities"),
            "tools": len(list_tools()),
        },
    }


@app.get("/version")
def version():
    return {
        "version": "0.4.0",
        "build": "Cognitive-Loop-OS unified runtime",
        "capabilities": [
            "FTS5 full-text search",
            "sqlite-vec vector search",
            "SM-2 spaced repetition",
            "A→B machine knowledge translation",
            "NetworkX graph database",
            "Obsidian bidirectional bridge",
            "Backlinks + Wikilinks",
            "Dataview query engine",
            "Collection views (table/board/calendar/gallery/list)",
            "Canvas whiteboard",
            "Auto-tagging + progressive summarization",
            "Knowledge gardening (orphans/gaps/evergreen)",
            "GraphRAG multi-hop search",
            "RSS/Atom feed collection",
            "Web search + content extraction",
            "YouTube transcript extraction",
            "Fact extraction (SPO triples)",
            "Cross-reference + credibility scoring",
            "Evidence tracking + health radar",
            "Learning analytics + streak tracking",
            "Retro summaries + daily missions",
            "Project generator",
        ],
    }


@app.get("/tools")
def tools():
    return {"items": list_tools()}


@app.post("/ingest")
def ingest_api(input_data: dict):
    doc = ingest(input_data)
    save_memory(doc)
    return doc


@app.post("/ingest/file")
def ingest_file_api(payload: dict):
    try:
        doc = ingest_file(
            str(payload.get("path", "")),
            source=payload.get("source"),
            metadata=payload.get("metadata"),
        )
    except IngestionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    decision = route(doc)
    doc.attention_score = decision.score
    doc.route = decision.route
    if decision.route != "DROP":
        save_memory(doc)
    return {"document": doc, "route": decision}


@app.post("/ingest/directory")
def ingest_directory_api(payload: dict):
    try:
        docs = ingest_directory(
            str(payload.get("path", "")),
            pattern=str(payload.get("pattern", "*.md")),
            limit=int(payload.get("limit", 50)),
            source=payload.get("source"),
            metadata=payload.get("metadata"),
        )
    except IngestionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    items = []
    for doc in docs:
        decision = route(doc)
        doc.attention_score = decision.score
        doc.route = decision.route
        if decision.route != "DROP":
            save_memory(doc)
        items.append({"document": doc, "route": decision})
    return {"count": len(items), "items": items}


@app.post("/route")
def route_api(input_data: dict):
    doc = ingest(input_data)
    return route(doc)


@app.post("/run")
def run(input_data: dict):
    doc = ingest(input_data)
    decision = route(doc)
    doc.attention_score = decision.score
    doc.route = decision.route
    if decision.route == "DROP":
        return {"status": "ignored", "document": doc, "route": decision}
    if decision.route == "REVIEW":
        save_memory(doc)
        return {"status": "needs_review", "document": doc, "route": decision}
    save_memory(doc)
    context = retrieve(doc.content)
    task = compile_task(context)
    perm = check_permission(task, doc.content)
    if perm.requires_human_review:
        return {
            "status": "blocked", "document": doc, "route": decision,
            "task": task, "permission": perm.model_dump(),
        }
    trace = execute(task, perm)
    log_trace(trace)
    eval_result = evaluate(trace)
    lesson = compile_lesson(eval_result, trace)
    save_lesson(lesson)
    return {
        "status": "done", "document": doc, "route": decision,
        "context": context, "task": task, "trace": trace,
        "eval": eval_result, "lesson": lesson,
    }


@app.post("/convert/file")
def convert_file_api(payload: dict):
    path = str(payload.get("path", ""))
    fmt = payload.get("format")
    try:
        content, engine = convert_file(path, fmt)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"path": path, "format": fmt or "auto", "engine": engine,
            "content": content, "char_count": len(content)}


@app.post("/convert/url")
def convert_url_api(payload: dict):
    url = str(payload.get("url", ""))
    try:
        content, engine = convert_url(url)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"url": url, "engine": engine, "content": content,
            "char_count": len(content)}


@app.post("/convert/directory")
def convert_directory_api(payload: dict):
    directory = str(payload.get("path", ""))
    pattern = str(payload.get("pattern", "*.*"))
    limit = int(payload.get("limit", 50))
    results = multi_convert_directory(directory, pattern, limit)
    return {"path": directory, "count": len(results), "items": results}


@app.post("/memory/search")
def memory_search(payload: dict):
    query = str(payload.get("query", ""))
    top_k = int(payload.get("top_k", 5))
    return {"query": query, "items": search_memory(query, top_k=top_k)}


@app.get("/traces")
def traces():
    return {"items": list_traces()}


@app.get("/memory/lessons")
def lessons():
    return {"items": list_lessons()}


# ── Auth + Backup + Architecture ─────────────────────────


@app.post("/auth/token")
def auth_token(user_id: str = "", role: str = "user", expires_hours: int = 24):
    """Generate a JWT token."""
    from shared.auth import create_token
    token = create_token(user_id=user_id, role=role, expires_hours=expires_hours)
    return {"token": token, "expires_in_hours": expires_hours}


@app.post("/backup")
def backup_db():
    """Create a database backup."""
    from shared.backup import auto_backup
    return auto_backup()


@app.get("/backup/list")
def backup_list():
    """List available backups."""
    from shared.backup import list_backups
    return {"backups": list_backups()}


@app.get("/architecture")
def architecture():
    """Return system architecture as Mermaid diagram."""
    return {
        "mermaid": """```mermaid
graph TB
    subgraph Clients["客户端"]
        Web["🌐 Dashboard"]; API["📡 API"]; Agent["🤖 MCP"]; Cron["⏰ Cron"]
    end
    subgraph Gateway["网关 :8000"]
        Auth["🔐 JWT"]; CORS["🌍 CORS"]; Log["📝 Log"]
    end
    subgraph Core["Core"]
        Router["🧭 Route"]; Pipeline["⚡ Pipeline"]; Tools["🔧 Tools"]
    end
    subgraph KB["Knowledge-Base"]
        Search["🔍 Search"]; Garden["🌱 Garden"]; Review["📚 SM-2"]
        Canvas["🎨 Canvas"]; MKU["🤖 MKU"]
    end
    subgraph Data["数据"]
        SQLite[("💾 SQLite")]; VecDB[("🧬 Vec")]; GraphDB[("🕸️ Graph")]; Backup[("📦 Backup")]
    end
    Web-->Auth; API-->Auth; Agent-->Auth; Cron-->Auth
    Auth-->Router; Router-->Pipeline; Pipeline-->Search; Pipeline-->Garden
    Search-->SQLite; Search-->VecDB; Garden-->GraphDB; Review-->SQLite; SQLite-->Backup
```""",
        "version": "0.4.0", "modules": 36, "tests": 106,
    }
