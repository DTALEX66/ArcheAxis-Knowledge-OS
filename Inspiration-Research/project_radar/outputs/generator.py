"""Daily brief + GitHub AI project screening table generator.

Produces two outputs:
  - daily_brief.json: 5-section brief (gold/design/tech/ai/github)
  - github_ai_projects.csv: screening table with scores
"""
import csv
import json
import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

_IR_DIR = Path(__file__).resolve().parents[2]  # Inspiration-Research/
_PROJECT_ROOT = _IR_DIR.parent  # Cognitive-Loop-OS/
sys.path.insert(0, str(_PROJECT_ROOT))
sys.path.insert(0, str(_IR_DIR))

from project_radar.scoring.scorer import ProjectScores, score_project
from shared.config import resolve_runtime_path

OUTPUT_DIR = resolve_runtime_path("data/reports")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class BriefItem:
    title: str
    summary: str
    impact: str = "watch"
    source: str = ""


@dataclass
class DailyBrief:
    brief_id: str = ""
    date: str = ""
    sections: dict = field(default_factory=lambda: {
        "gold": [], "design": [], "technology": [], "ai": [],
    })
    github_ai_projects: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "brief_id": self.brief_id,
            "date": self.date,
            "sections": {
                k: [{"title": i.title, "summary": i.summary, "impact": i.impact}
                    for i in v]
                for k, v in self.sections.items()
            },
            "github_ai_projects": self.github_ai_projects,
        }


@dataclass
class ProjectScreeningEntry:
    repo: str
    category: str
    summary: str
    absorption_mode: str
    recommended_target: str
    risk_level: str
    scores: ProjectScores
    next_action: str = "review"


def build_daily_brief(
    gold_items: list[BriefItem] = None,
    design_items: list[BriefItem] = None,
    tech_items: list[BriefItem] = None,
    ai_items: list[BriefItem] = None,
) -> DailyBrief:
    today = date.today().isoformat()
    brief = DailyBrief(brief_id=f"brief_{today}", date=today)
    if gold_items:
        brief.sections["gold"] = gold_items
    if design_items:
        brief.sections["design"] = design_items
    if tech_items:
        brief.sections["technology"] = tech_items
    if ai_items:
        brief.sections["ai"] = ai_items
    return brief


def screen_project(
    repo: str,
    category: str,
    summary: str = "",
    token_saving: float = 0,
    efficiency_gain: float = 0,
    local_first: float = 0,
    system_fit: float = 0,
    risk_penalty: float = 0,
    risk_level: str = "low",
    absorption_mode: str = "reference",
    recommended_target: str = "IR",
) -> ProjectScreeningEntry:
    scores = score_project(
        token_saving=token_saving, efficiency_gain=efficiency_gain,
        local_first=local_first, system_fit=system_fit,
        risk_penalty=risk_penalty, risk_level=risk_level,
    )
    next_action = "generate_intake_card" if scores.qualifies else "review"
    return ProjectScreeningEntry(
        repo=repo, category=category, summary=summary,
        absorption_mode=absorption_mode,
        recommended_target=recommended_target,
        risk_level=risk_level, scores=scores, next_action=next_action,
    )


def export_screening_csv(entries: list[ProjectScreeningEntry],
                         output_path: str | None = None) -> Path:
    if output_path is None:
        today = date.today().isoformat()
        output_path = str(OUTPUT_DIR / f"github_ai_project_screening_{today}.csv")

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "repo", "category", "summary", "absorption_mode",
            "recommended_target", "risk_level",
            "token_saving", "efficiency_gain", "local_first",
            "system_fit", "risk_penalty", "total", "qualifies",
            "next_action",
        ])
        for e in entries:
            writer.writerow([
                e.repo, e.category, e.summary, e.absorption_mode,
                e.recommended_target, e.risk_level,
                e.scores.token_saving, e.scores.efficiency_gain,
                e.scores.local_first, e.scores.system_fit,
                e.scores.risk_penalty, e.scores.total,
                "yes" if e.scores.qualifies else "no",
                e.next_action,
            ])
    return path


# ── Quick self-test ──
if __name__ == "__main__":
    # Build a sample daily brief
    brief = build_daily_brief(
        gold_items=[BriefItem("Gold price up", "Fed signals rate cut", "watch")],
        design_items=[BriefItem("AI design tools", "New Figma AI features", "monitor")],
        tech_items=[BriefItem("OpenAI DevDay", "New API features announced", "follow")],
        ai_items=[BriefItem("Crawl4AI v1.0", "Major release for web-to-Markdown", "evaluate")],
    )
    print(json.dumps(brief.to_dict(), ensure_ascii=False, indent=2))

    # Screen some projects
    entries = [
        screen_project("unclecode/crawl4ai", "Crawler",
                       "Web to LLM-ready Markdown", token_saving=4.0,
                       efficiency_gain=4.5, local_first=4.0,
                       system_fit=4.0, absorption_mode="adapter",
                       recommended_target="IR"),
        screen_project("microsoft/markitdown", "Converter",
                       "Multi-format to Markdown", token_saving=4.5,
                       efficiency_gain=4.0, local_first=4.5,
                       system_fit=4.0, absorption_mode="adapter",
                       recommended_target="IR/KB"),
    ]
    path = export_screening_csv(entries)
    print(f"\nCSV exported: {path}")
