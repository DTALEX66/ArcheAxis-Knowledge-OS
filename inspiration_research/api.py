"""Inspiration Research API — SQLite-backed, v0.2."""

import re
import time
import uuid

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.facades.research import (
    get_research_package,
    ingest_candidate,
    research_github_repository,
)
from inspiration_research.project_radar.outputs.generator import (
    BriefItem,
    build_daily_brief,
    export_screening_csv,
    screen_project,
)
from inspiration_research.project_radar.scoring.scorer import score_project
from shared.config import config, validate_runtime_config
from shared.research_store import ResearchPersistenceError
from shared.safe_http import SafeHTTPError
from shared.storage import count, insert, select_all

validate_runtime_config(config)
app = FastAPI(title="Inspiration-Research", version="0.2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.get("cors.allow_origins", ["*"]),
    allow_methods=config.get("cors.allow_methods", ["GET", "POST"]),
    allow_headers=config.get("cors.allow_headers", ["Authorization", "Content-Type"]),
)


@app.middleware("http")
async def authenticate_and_log(request: Request, call_next):
    from shared.auth import authenticate_request

    started = time.time()

    user = authenticate_request(
        request.url.path,
        request.headers.get("X-API-Key", ""),
        request.headers.get("Authorization", ""),
    )
    if not user:
        return JSONResponse(
            status_code=401,
            content={"error": "unauthorized", "detail": "Valid API key or token required."},
        )
    response = await call_next(request)
    response.headers["X-Process-Time-ms"] = str(round((time.time() - started) * 1000, 1))
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    environment = str(config.get("app.environment", "development")).lower()
    detail = str(exc)[:200] if environment not in {"production", "prod"} else "request failed"
    return JSONResponse(status_code=500, content={"error": "internal_error", "detail": detail})


class ResearchNoteIn(BaseModel):
    title: str
    content: str
    source: str = "manual"
    tags: list[str] = []


class IntakeRequest(BaseModel):
    title: str
    why: str
    what_to_absorb: list[str]
    what_not_to_absorb: list[str] = []
    risk_level: str = "low"
    target_repo: str = "Knowledge-Base"


class GitHubResearchRequest(BaseModel):
    repository_url: str


class ContractRequest(BaseModel):
    intake_id: str
    goal: str
    deliverables: list[str]
    acceptance_criteria: list[str] = []
    blocked_actions: list[str] = []
    risk_level: str = "low"
    target_repo: str = "Cognitive-OS"


class ScoreRequest(BaseModel):
    token_saving: float = 0.0
    efficiency_gain: float = 0.0
    local_first: float = 0.0
    system_fit: float = 0.0
    risk_penalty: float = 0.0
    risk_level: str = "low"


class BriefSectionIn(BaseModel):
    title: str
    summary: str
    impact: str = "watch"


class DailyBriefRequest(BaseModel):
    gold: list[BriefSectionIn] = []
    design: list[BriefSectionIn] = []
    technology: list[BriefSectionIn] = []
    ai: list[BriefSectionIn] = []


class ScreenRequest(BaseModel):
    repo: str
    category: str
    summary: str = ""
    token_saving: float = 0.0
    efficiency_gain: float = 0.0
    local_first: float = 0.0
    system_fit: float = 0.0
    risk_penalty: float = 0.0
    risk_level: str = "low"
    absorption_mode: str = "reference"
    recommended_target: str = "IR"


@app.get("/health")
def health():
    return {"status": "ok", "system": "inspiration-research"}


@app.post("/research-note")
def create_research_note(note: ResearchNoteIn):
    if note.source.strip().lower() not in {"manual", "local"}:
        raise HTTPException(
            status_code=409,
            detail="external research notes must use the governed ResearchPackage candidate path",
        )
    r = {"id": f"note_{uuid.uuid4().hex[:12]}", **note.model_dump()}
    insert("ir_research_notes", r)
    return r


@app.get("/research-notes")
def list_research_notes(limit: int = 20):
    return {"count": count("ir_research_notes"), "items": select_all("ir_research_notes", limit)}


@app.post("/intake-card")
def create_intake_card(req: IntakeRequest):
    return ingest_candidate(**req.model_dump()).model_dump()


@app.get("/intake-cards")
def list_intake_cards(limit: int = 20):
    return {"count": count("ir_intake_cards"), "items": select_all("ir_intake_cards", limit)}


@app.post("/research/github-repository")
def create_github_research_package(req: GitHubResearchRequest, request: Request):
    fetcher = getattr(request.app.state, "research_github_fetcher", None)
    try:
        return research_github_repository(req.repository_url, fetcher=fetcher).model_dump()
    except SafeHTTPError as exc:
        raise HTTPException(status_code=502, detail="GitHub response failed safety policy") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RuntimeError as exc:
        if "research schema migration is pending" in str(exc):
            raise HTTPException(status_code=503, detail="Research migration is pending") from exc
        raise


@app.get("/research/packages/{package_id}")
def get_research_package_endpoint(package_id: str):
    try:
        return get_research_package(package_id).model_dump()
    except ResearchPersistenceError as exc:
        if "research package not found" in str(exc):
            raise HTTPException(status_code=404, detail="Research package not found") from exc
        raise
    except RuntimeError as exc:
        if "research schema migration is pending" in str(exc):
            raise HTTPException(status_code=503, detail="Research migration is pending") from exc
        raise


@app.post("/engineering-contract")
def create_contract(req: ContractRequest):
    del req
    raise HTTPException(
        status_code=409,
        detail="engineering-contract promotion requires server-owned Phase 5 review provenance",
    )


@app.get("/contracts")
def list_contracts(limit: int = 20):
    return {"count": count("ir_contracts"), "items": select_all("ir_contracts", limit)}


@app.post("/score-project")
def score_project_endpoint(req: ScoreRequest):
    r = score_project(**req.model_dump())
    return {
        "scores": {
            k: getattr(r, k)
            for k in [
                "token_saving",
                "efficiency_gain",
                "local_first",
                "system_fit",
                "risk_penalty",
                "total",
            ]
        },
        "qualifies": r.qualifies,
    }


@app.post("/daily-brief")
def create_daily_brief(req: DailyBriefRequest):
    brief = build_daily_brief(
        gold_items=[BriefItem(**g.model_dump()) for g in req.gold] if req.gold else None,
        design_items=[BriefItem(**d.model_dump()) for d in req.design] if req.design else None,
        tech_items=[BriefItem(**t.model_dump()) for t in req.technology]
        if req.technology
        else None,
        ai_items=[BriefItem(**a.model_dump()) for a in req.ai] if req.ai else None,
    )
    insert("ir_daily_briefs", brief.to_dict())
    return brief.to_dict()


@app.get("/daily-briefs")
def list_daily_briefs(limit: int = 10):
    return {"count": count("ir_daily_briefs"), "items": select_all("ir_daily_briefs", limit)}


@app.post("/screen-project")
def screen_project_endpoint(req: ScreenRequest):
    e = screen_project(**req.model_dump())
    return {
        "repo": e.repo,
        "category": e.category,
        "absorption_mode": e.absorption_mode,
        "scores": {
            k: getattr(e.scores, k)
            for k in [
                "token_saving",
                "efficiency_gain",
                "local_first",
                "system_fit",
                "risk_penalty",
                "total",
            ]
        },
        "qualifies": e.scores.qualifies,
        "next_action": e.next_action,
    }


@app.post("/screen-projects/batch")
def screen_projects_batch(requests: list[ScreenRequest]):
    entries = [screen_project(**r.model_dump()) for r in requests]
    try:
        csv_path = export_screening_csv(entries)
    except ValueError as exc:
        if "server-owned Phase 5 review provenance" in str(exc):
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        raise
    return {
        "count": len(entries),
        "qualified": sum(1 for e in entries if e.scores.qualifies),
        "items": [
            {"repo": e.repo, "total": e.scores.total, "qualifies": e.scores.qualifies}
            for e in entries
        ],
        "csv_exported": str(csv_path),
    }


@app.get("/trending")
def get_trending(since: str = "weekly", count: int = 10):
    del since, count
    raise HTTPException(
        status_code=409,
        detail="legacy external collection is disabled; use /research/github-repository",
    )


@app.post("/daily-brief/auto")
def auto_daily_brief(since: str = "weekly", count: int = 10):
    del since, count
    raise HTTPException(
        status_code=409,
        detail="legacy external collection is disabled; use /research/github-repository",
    )


def _guess(text: str) -> str:
    for kw, cat in [
        ("crawl|scrape|parser|extract", "Crawler"),
        ("convert|markdown|pdf|doc", "Document to Markdown"),
        ("agent|coding|codex|copilot", "AI Agent/Coding"),
        ("llm|gateway|model", "LLM Gateway"),
        ("rag|knowledge|search", "RAG/Document Intelligence"),
        ("memory", "Memory"),
        ("mcp|tool", "Agent SDK"),
    ]:
        if any(k in text for k in kw.split("|")):
            return cat
    return "AI Agent/Coding"


def _score(text: str, pattern: str, base: float) -> float:
    return min(base + len(re.findall(pattern, text)) * 0.5, 5.0)
