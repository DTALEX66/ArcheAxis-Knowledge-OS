"""Daily runner: fetch trending → score → brief → CSV → IntakeCards.

Designed to be called by Hermes cron job or directly:
  python scripts/run_daily.py
"""
import json
from datetime import date

from inspiration_research.intake.generator import generate_intake_card
from inspiration_research.project_radar.collectors.github_trending import (
    collect_trending,
    collect_trending_fallback,
)
from inspiration_research.project_radar.outputs.generator import (
    BriefItem,
    build_daily_brief,
    export_screening_csv,
    screen_project,
)
from shared.config import resolve_runtime_path

OUTPUT_DIR = resolve_runtime_path("data/reports")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def run_daily(since: str = "daily", count: int = 10) -> dict:
    today = date.today().isoformat()
    print(f"=== Daily Run: {today} ===\n")

    # 1. Collect trending
    print(f"[1/5] Fetching trending repos (since={since})...")
    repos = collect_trending(since=since, per_page=count)
    if not repos:
        print("  No daily results, trying fallback...")
        repos = collect_trending_fallback(count)
    print(f"  Found {len(repos)} repos")

    # 2. Score + screen
    print("[2/5] Scoring projects...")
    entries = []
    for r in repos:
        d = (r.description + " " + " ".join(r.topics)).lower()
        entry = screen_project(
            repo=r.repo, category=_guess_category(d),
            summary=r.description[:200],
            token_saving=_score_text(d, "ai|coding|agent|auto", 3.5),
            efficiency_gain=_score_text(d, "ai|coding|tool|pipeline", 3.5),
            local_first=_score_text(d, "local|self-hosted|offline|oss", 4.0),
            system_fit=_score_text(d, "ai|llm|agent|rag|mcp|coding", 4.0),
            risk_penalty=0.5 if any(k in d for k in ["shell", "exec", "sudo"]) else 0.0,
            risk_level="low",
            absorption_mode="candidate",
            recommended_target="IR",
        )
        entries.append(entry)

    qualified = [e for e in entries if e.scores.qualifies]
    print(f"  Qualified: {len(qualified)}/{len(entries)}")

    # 3. Export CSV
    print("[3/5] Exporting screening CSV...")
    csv_path = export_screening_csv(entries)
    print(f"  {csv_path}")

    # 4. Build daily brief
    print("[4/5] Building daily brief...")
    brief = build_daily_brief(
        ai_items=[BriefItem(title=r.repo, summary=r.description[:120], impact="evaluate",
                            source=r.url) for r in repos[:8]],
    )
    brief.github_ai_projects = [e.repo for e in qualified]

    brief_path = OUTPUT_DIR / f"daily_brief_{today}.json"
    brief_path.write_text(json.dumps(brief.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  {brief_path}")

    # 5. Generate IntakeCards for qualified projects
    print("[5/5] Generating IntakeCards...")
    intake_cards = []
    for e in qualified[:5]:  # top 5
        card = generate_intake_card(
            title=f"Absorb: {e.repo}",
            why=f"Trending project: {e.summary[:80]}. Score: {e.scores.total}",
            what_to_absorb=[e.repo, "evaluate integration path", "check license"],
            what_not_to_absorb=["auto-install", "direct core DB write"],
            risk_level="low",
            target_repo="Knowledge-Base",
        )
        intake_cards.append(card.to_dict())

    intake_path = OUTPUT_DIR / f"intake_cards_{today}.json"
    intake_path.write_text(json.dumps(intake_cards, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  {intake_path} ({len(intake_cards)} cards)")

    return {
        "date": today,
        "trending_found": len(repos),
        "qualified": len(qualified),
        "csv": str(csv_path),
        "brief": str(brief_path),
        "intake_cards": str(intake_path),
    }


def _guess_category(text: str) -> str:
    if any(k in text for k in ["crawl", "scrape", "parser", "extract"]):
        return "Crawler"
    if any(k in text for k in ["convert", "markdown", "pdf", "doc"]):
        return "Document to Markdown"
    if any(k in text for k in ["agent", "coding", "codex", "copilot"]):
        return "AI Agent/Coding"
    if any(k in text for k in ["llm", "gateway", "model"]):
        return "LLM Gateway"
    if any(k in text for k in ["rag", "knowledge", "search"]):
        return "RAG/Document Intelligence"
    if "memory" in text:
        return "Memory"
    if any(k in text for k in ["mcp", "tool"]):
        return "Agent SDK"
    return "AI Agent/Coding"


def _score_text(text: str, pattern: str, base: float) -> float:
    import re
    return min(base + len(re.findall(pattern, text)) * 0.5, 5.0)


if __name__ == "__main__":
    result = run_daily(since="daily", count=10)
    print(f"\n✓ Daily run complete: {json.dumps(result, indent=2, ensure_ascii=False)}")
