"""Inspiration-Research API — SQLite-backed, v0.2."""
import sys, uuid
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_PROJECT_ROOT))
sys.path.insert(0, str(_PROJECT_ROOT / "Inspiration-Research"))

from fastapi import FastAPI
from pydantic import BaseModel

from project_radar.scoring.scorer import score_project
from project_radar.outputs.generator import (
    build_daily_brief, screen_project, export_screening_csv, BriefItem,
)
from project_radar.collectors.github_trending import (
    collect_trending, collect_trending_fallback, TrendingRepo,
)
from intake.generator import generate_intake_card
from contracts.generator import generate_contract
from shared.storage import insert, select_all, count

app = FastAPI(title="Inspiration-Research", version="0.2.0")


class ResearchNoteIn(BaseModel):
    title: str; content: str; source: str = "manual"; tags: list[str] = []

class IntakeRequest(BaseModel):
    title: str; why: str; what_to_absorb: list[str]
    what_not_to_absorb: list[str] = []; risk_level: str = "low"
    target_repo: str = "Knowledge-Base"

class ContractRequest(BaseModel):
    intake_id: str; goal: str; deliverables: list[str]
    acceptance_criteria: list[str] = []; blocked_actions: list[str] = []
    risk_level: str = "low"; target_repo: str = "Cognitive-OS"

class ScoreRequest(BaseModel):
    token_saving: float = 0.0; efficiency_gain: float = 0.0
    local_first: float = 0.0; system_fit: float = 0.0
    risk_penalty: float = 0.0; risk_level: str = "low"

class BriefSectionIn(BaseModel):
    title: str; summary: str; impact: str = "watch"

class DailyBriefRequest(BaseModel):
    gold: list[BriefSectionIn] = []; design: list[BriefSectionIn] = []
    technology: list[BriefSectionIn] = []; ai: list[BriefSectionIn] = []

class ScreenRequest(BaseModel):
    repo: str; category: str; summary: str = ""
    token_saving: float = 0.0; efficiency_gain: float = 0.0
    local_first: float = 0.0; system_fit: float = 0.0
    risk_penalty: float = 0.0; risk_level: str = "low"
    absorption_mode: str = "reference"; recommended_target: str = "IR"


@app.get("/health")
def health(): return {"status": "ok", "system": "inspiration-research"}

@app.post("/research-note")
def create_research_note(note: ResearchNoteIn):
    r = {"id": f"note_{uuid.uuid4().hex[:12]}", **note.model_dump()}
    insert("ir_research_notes", r); return r

@app.get("/research-notes")
def list_research_notes(limit: int = 20):
    return {"count": count("ir_research_notes"), "items": select_all("ir_research_notes", limit)}

@app.post("/intake-card")
def create_intake_card(req: IntakeRequest):
    card = generate_intake_card(title=req.title, why=req.why, what_to_absorb=req.what_to_absorb,
                                what_not_to_absorb=req.what_not_to_absorb, risk_level=req.risk_level,
                                target_repo=req.target_repo)
    insert("ir_intake_cards", card.to_dict()); return card.to_dict()

@app.get("/intake-cards")
def list_intake_cards(limit: int = 20):
    return {"count": count("ir_intake_cards"), "items": select_all("ir_intake_cards", limit)}

@app.post("/engineering-contract")
def create_contract(req: ContractRequest):
    c = generate_contract(goal=req.goal, deliverables=req.deliverables,
                          acceptance_criteria=req.acceptance_criteria,
                          blocked_actions=req.blocked_actions,
                          risk_level=req.risk_level, target_repo=req.target_repo)
    insert("ir_contracts", c.to_dict()); return c.to_dict()

@app.get("/contracts")
def list_contracts(limit: int = 20):
    return {"count": count("ir_contracts"), "items": select_all("ir_contracts", limit)}

@app.post("/score-project")
def score_project_endpoint(req: ScoreRequest):
    r = score_project(**req.model_dump())
    return {"scores": {k: getattr(r, k) for k in ["token_saving","efficiency_gain","local_first","system_fit","risk_penalty","total"]}, "qualifies": r.qualifies}

@app.post("/daily-brief")
def create_daily_brief(req: DailyBriefRequest):
    brief = build_daily_brief(
        gold_items=[BriefItem(**g.model_dump()) for g in req.gold] if req.gold else None,
        design_items=[BriefItem(**d.model_dump()) for d in req.design] if req.design else None,
        tech_items=[BriefItem(**t.model_dump()) for t in req.technology] if req.technology else None,
        ai_items=[BriefItem(**a.model_dump()) for a in req.ai] if req.ai else None)
    insert("ir_daily_briefs", brief.to_dict()); return brief.to_dict()

@app.get("/daily-briefs")
def list_daily_briefs(limit: int = 10):
    return {"count": count("ir_daily_briefs"), "items": select_all("ir_daily_briefs", limit)}

@app.post("/screen-project")
def screen_project_endpoint(req: ScreenRequest):
    e = screen_project(**req.model_dump())
    return {"repo": e.repo, "category": e.category, "absorption_mode": e.absorption_mode,
            "scores": {k: getattr(e.scores, k) for k in ["token_saving","efficiency_gain","local_first","system_fit","risk_penalty","total"]},
            "qualifies": e.scores.qualifies, "next_action": e.next_action}

@app.post("/screen-projects/batch")
def screen_projects_batch(requests: list[ScreenRequest]):
    entries = [screen_project(**r.model_dump()) for r in requests]
    csv_path = export_screening_csv(entries)
    return {"count": len(entries), "qualified": sum(1 for e in entries if e.scores.qualifies),
            "items": [{"repo": e.repo, "total": e.scores.total, "qualifies": e.scores.qualifies} for e in entries],
            "csv_exported": str(csv_path)}

@app.get("/trending")
def get_trending(since: str = "weekly", count: int = 10):
    repos = collect_trending(since=since, per_page=count) or collect_trending_fallback(count)
    return {"since": since, "count": len(repos),
            "items": [{"repo": r.repo, "description": r.description, "stars": r.stars,
                        "language": r.language, "url": r.url, "topics": r.topics} for r in repos]}

@app.post("/daily-brief/auto")
def auto_daily_brief(since: str = "weekly", count: int = 10):
    repos = collect_trending(since=since, per_page=count) or collect_trending_fallback(count)
    entries = []
    for r in repos:
        d = (r.description + " " + " ".join(r.topics)).lower()
        entries.append(screen_project(
            repo=r.repo, category=_guess(d), summary=r.description[:200],
            token_saving=_score(d, "ai|coding|agent|auto", 3.5),
            efficiency_gain=_score(d, "ai|coding|tool|pipeline", 3.5),
            local_first=_score(d, "local|self-hosted|offline|oss", 4.0),
            system_fit=_score(d, "ai|llm|agent|rag|mcp|coding", 4.0),
            risk_penalty=0.5 if any(k in d for k in ["shell","exec","sudo"]) else 0.0,
            risk_level="low", absorption_mode="candidate", recommended_target="IR"))
    brief = build_daily_brief(ai_items=[BriefItem(title=r.repo, summary=r.description[:100], impact="evaluate") for r in repos[:5]])
    brief.github_ai_projects = [e.repo for e in entries if e.scores.qualifies]
    csv_path = export_screening_csv(entries)
    insert("ir_daily_briefs", brief.to_dict())
    # Bridge to KB
    from shared.bridge import bridge_trending_to_kb
    bridged = bridge_trending_to_kb([{"repo": e.repo, "qualifies": e.scores.qualifies} for e in entries])
    return {"brief": brief.to_dict(), "qualified": sum(1 for e in entries if e.scores.qualifies),
            "total": len(entries), "csv": str(csv_path), "bridged_to_kb": bridged}

def _guess(text: str) -> str:
    for kw, cat in [("crawl|scrape|parser|extract","Crawler"),("convert|markdown|pdf|doc","Document to Markdown"),
                     ("agent|coding|codex|copilot","AI Agent/Coding"),("llm|gateway|model","LLM Gateway"),
                     ("rag|knowledge|search","RAG/Document Intelligence"),("memory","Memory"),("mcp|tool","Agent SDK")]:
        if any(k in text for k in kw.split("|")): return cat
    return "AI Agent/Coding"

def _score(text: str, pattern: str, base: float) -> float:
    import re; return min(base + len(re.findall(pattern, text)) * 0.5, 5.0)
