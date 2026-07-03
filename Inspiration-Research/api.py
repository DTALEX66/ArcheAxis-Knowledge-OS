"""Inspiration-Research API — B线研究输入层独立服务.

Run from Cognitive-Loop-OS root:
  python -m uvicorn Inspiration-Research.api:app --port 8001
"""
import sys
from pathlib import Path

# Ensure IR modules importable (run from project root)
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_PROJECT_ROOT))
sys.path.insert(0, str(_PROJECT_ROOT / "Inspiration-Research"))

from fastapi import FastAPI
from pydantic import BaseModel

from project_radar.scoring.scorer import score_project
from project_radar.outputs.generator import (
    build_daily_brief, screen_project, export_screening_csv, BriefItem,
)
from intake.generator import generate_intake_card, IntakeCard
from contracts.generator import generate_contract, EngineeringContract

app = FastAPI(title="Inspiration-Research", version="0.1.0")

# ── In-memory stores (SQLite migration in Phase 2) ──
research_notes: list[dict] = []
intake_cards: list[IntakeCard] = []
contracts: list[EngineeringContract] = []


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


@app.get("/health")
def health():
    return {"status": "ok", "system": "inspiration-research"}


@app.post("/research-note")
def create_research_note(note: ResearchNoteIn):
    record = note.model_dump()
    import uuid
    record["id"] = f"note_{uuid.uuid4().hex[:12]}"
    research_notes.append(record)
    return record


@app.get("/research-notes")
def list_research_notes(limit: int = 20):
    return {"count": len(research_notes), "items": research_notes[-limit:]}


@app.post("/intake-card")
def create_intake_card(req: IntakeRequest):
    card = generate_intake_card(
        title=req.title, why=req.why,
        what_to_absorb=req.what_to_absorb,
        what_not_to_absorb=req.what_not_to_absorb,
        risk_level=req.risk_level, target_repo=req.target_repo,
    )
    intake_cards.append(card)
    return card.to_dict()


@app.get("/intake-cards")
def list_intake_cards(limit: int = 20):
    return {"count": len(intake_cards), "items": [c.to_dict() for c in intake_cards[-limit:]]}


@app.post("/engineering-contract")
def create_contract(req: ContractRequest):
    contract = generate_contract(
        goal=req.goal, deliverables=req.deliverables,
        acceptance_criteria=req.acceptance_criteria,
        blocked_actions=req.blocked_actions,
        risk_level=req.risk_level, target_repo=req.target_repo,
    )
    contracts.append(contract)
    return contract.to_dict()


@app.get("/contracts")
def list_contracts(limit: int = 20):
    return {"count": len(contracts), "items": [c.to_dict() for c in contracts[-limit:]]}


@app.post("/score-project")
def score_project_endpoint(req: ScoreRequest):
    result = score_project(
        token_saving=req.token_saving,
        efficiency_gain=req.efficiency_gain,
        local_first=req.local_first,
        system_fit=req.system_fit,
        risk_penalty=req.risk_penalty,
        risk_level=req.risk_level,
    )
    return {
        "scores": {
            "token_saving": result.token_saving,
            "efficiency_gain": result.efficiency_gain,
            "local_first": result.local_first,
            "system_fit": result.system_fit,
            "risk_penalty": result.risk_penalty,
            "total": result.total,
        },
        "qualifies": result.qualifies,
    }


# ── Daily brief + project screening ──

daily_briefs: list = []


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


@app.post("/daily-brief")
def create_daily_brief(req: DailyBriefRequest):
    brief = build_daily_brief(
        gold_items=[BriefItem(**g.model_dump()) for g in req.gold] if req.gold else None,
        design_items=[BriefItem(**d.model_dump()) for d in req.design] if req.design else None,
        tech_items=[BriefItem(**t.model_dump()) for t in req.technology] if req.technology else None,
        ai_items=[BriefItem(**a.model_dump()) for a in req.ai] if req.ai else None,
    )
    daily_briefs.append(brief)
    return brief.to_dict()


@app.get("/daily-briefs")
def list_daily_briefs(limit: int = 10):
    return {"count": len(daily_briefs), "items": [b.to_dict() for b in daily_briefs[-limit:]]}


@app.post("/screen-project")
def screen_project_endpoint(req: ScreenRequest):
    entry = screen_project(
        repo=req.repo, category=req.category, summary=req.summary,
        token_saving=req.token_saving, efficiency_gain=req.efficiency_gain,
        local_first=req.local_first, system_fit=req.system_fit,
        risk_penalty=req.risk_penalty, risk_level=req.risk_level,
        absorption_mode=req.absorption_mode, recommended_target=req.recommended_target,
    )
    return {
        "repo": entry.repo, "category": entry.category,
        "absorption_mode": entry.absorption_mode,
        "scores": {
            "token_saving": entry.scores.token_saving,
            "efficiency_gain": entry.scores.efficiency_gain,
            "local_first": entry.scores.local_first,
            "system_fit": entry.scores.system_fit,
            "risk_penalty": entry.scores.risk_penalty,
            "total": entry.scores.total,
        },
        "qualifies": entry.scores.qualifies,
        "next_action": entry.next_action,
    }


@app.post("/screen-projects/batch")
def screen_projects_batch(requests: list[ScreenRequest]):
    entries = []
    for req in requests:
        entry = screen_project(
            repo=req.repo, category=req.category, summary=req.summary,
            token_saving=req.token_saving, efficiency_gain=req.efficiency_gain,
            local_first=req.local_first, system_fit=req.system_fit,
            risk_penalty=req.risk_penalty, risk_level=req.risk_level,
            absorption_mode=req.absorption_mode, recommended_target=req.recommended_target,
        )
        entries.append(entry)

    csv_path = export_screening_csv(entries)
    return {
        "count": len(entries),
        "qualified": sum(1 for e in entries if e.scores.qualifies),
        "items": [
            {"repo": e.repo, "total": e.scores.total, "qualifies": e.scores.qualifies}
            for e in entries
        ],
        "csv_exported": str(csv_path),
    }


# ── GitHub trending ──

from project_radar.collectors.github_trending import (
    collect_trending, collect_trending_fallback, TrendingRepo,
)


@app.get("/trending")
def get_trending(since: str = "weekly", count: int = 10):
    repos = collect_trending(since=since, per_page=count)
    if not repos:
        repos = collect_trending_fallback(count)
    return {
        "since": since,
        "count": len(repos),
        "items": [
            {"repo": r.repo, "description": r.description, "stars": r.stars,
             "language": r.language, "url": r.url, "topics": r.topics}
            for r in repos
        ],
    }


@app.post("/daily-brief/auto")
def auto_daily_brief(since: str = "weekly", count: int = 10):
    """Auto-generate daily brief from GitHub trending + score projects."""
    # Collect trending
    repos = collect_trending(since=since, per_page=count)
    if not repos:
        repos = collect_trending_fallback(count)

    # Score each repo
    entries = []
    for r in repos:
        # Heuristic scoring for trending repos
        cat = _guess_category(r.description, r.topics, r.language)
        entry = screen_project(
            repo=r.repo, category=cat, summary=r.description[:200],
            token_saving=_score_dim(r, "ai|coding|agent|automation", 3.0),
            efficiency_gain=_score_dim(r, "ai|coding|agent|tool", 3.0),
            local_first=_score_dim(r, "local|self-hosted|offline|privacy", 4.0),
            system_fit=_score_dim(r, "ai|llm|agent|rag|coding|mcp", 3.5),
            risk_penalty=0.5 if "shell" in r.description.lower() else 0.0,
            risk_level="low",
            absorption_mode="candidate",
            recommended_target="IR",
        )
        entries.append(entry)

    # Build brief
    brief = build_daily_brief(
        ai_items=[BriefItem(title=r.repo, summary=r.description[:100], impact="evaluate")
                   for r in repos[:5]],
    )
    brief.github_ai_projects = [e.repo for e in entries if e.scores.qualifies]

    # Export CSV
    csv_path = export_screening_csv(entries)
    daily_briefs.append(brief)

    return {
        "brief": brief.to_dict(),
        "qualified": sum(1 for e in entries if e.scores.qualifies),
        "total": len(entries),
        "csv": str(csv_path),
    }


def _guess_category(desc: str, topics: list, lang: str) -> str:
    d = (desc + " " + " ".join(topics)).lower()
    if any(k in d for k in ["crawl", "scrape", "parser", "extract"]): return "Crawler"
    if any(k in d for k in ["convert", "markdown", "pdf", "doc"]): return "Document to Markdown"
    if any(k in d for k in ["agent", "coding", "codex", "copilot"]): return "AI Agent/Coding"
    if any(k in d for k in ["llm", "gateway", "model"]): return "LLM Gateway"
    if any(k in d for k in ["rag", "knowledge", "search"]): return "RAG/Document Intelligence"
    if any(k in d for k in ["memory"]): return "Memory"
    if any(k in d for k in ["mcp", "tool"]): return "Agent SDK"
    return "AI Agent/Coding"


def _score_dim(repo: TrendingRepo, pattern: str, base: float) -> float:
    import re
    text = (repo.description + " " + " ".join(repo.topics)).lower()
    matches = len(re.findall(pattern, text))
    return min(base + matches * 0.5, 5.0)
