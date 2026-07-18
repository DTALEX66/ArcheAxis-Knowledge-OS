"""Batch scoring: score all 50 registry projects → CSV export.

Heuristic scoring based on category + absorption_mode.
"""

from pathlib import Path

from inspiration_research.project_radar.scoring.scorer import score_project

_PROJECT_ROOT = Path(__file__).resolve().parents[1]

REGISTRY_PATH = (
    _PROJECT_ROOT / "inspiration_research" / "resources" / "open_source_project_registry.json"
)


# ── Heuristic scoring by category ──

CATEGORY_SCORES = {
    "Crawler": (4.0, 4.5, 4.0, 4.0, 0.0),
    "Converter": (4.5, 4.0, 4.5, 4.0, 0.0),
    "LLM Gateway": (4.0, 4.5, 3.5, 4.5, 0.0),
    "Observability": (3.0, 4.0, 3.0, 4.0, 0.0),
    "Evaluation": (3.5, 4.0, 3.0, 4.0, 0.0),
    "Memory": (3.0, 3.5, 3.0, 4.0, 0.5),
    "Vector DB": (3.0, 3.5, 3.0, 3.5, 0.0),
    "Graph DB": (2.5, 3.0, 2.5, 3.0, 0.5),
    "AI Agent/Coding": (3.5, 4.5, 3.0, 4.0, 0.5),
    "Multi-Agent": (2.5, 3.5, 2.0, 3.0, 1.0),
    "Browser Agent": (2.0, 3.0, 2.0, 3.0, 1.5),
    "RAG/AI Platform": (3.0, 3.5, 2.5, 3.0, 0.5),
    "LLM Framework": (3.5, 4.0, 2.5, 3.5, 0.5),
    "Agent SDK": (3.5, 4.0, 3.0, 4.0, 0.5),
    "Agent State Machine": (3.0, 3.5, 2.5, 3.5, 0.5),
    "Agent/Orchestration": (3.0, 3.5, 2.5, 3.5, 0.5),
    "AI Frontend SDK": (2.5, 3.0, 2.0, 2.5, 0.0),
    "LLM UI": (2.0, 2.5, 1.5, 2.0, 0.0),
    "Personal AI/Search": (2.5, 3.0, 2.5, 3.0, 0.0),
    "Second Brain/RAG": (2.5, 3.0, 2.5, 3.0, 0.0),
    "Private RAG": (2.5, 3.0, 2.5, 3.0, 0.0),
    "Research Agent": (3.5, 4.0, 3.0, 4.0, 0.0),
    "Local Code AI": (3.5, 3.5, 4.0, 3.5, 0.0),
    "CLI Agent": (3.0, 3.5, 3.0, 3.5, 0.0),
    "AI App Builder": (2.5, 3.5, 2.0, 2.5, 0.5),
    "Browser Automation": (2.5, 3.0, 2.5, 3.0, 1.0),
    "Crawler Framework": (3.5, 4.0, 3.5, 3.5, 0.0),
    "Web Text Extraction": (3.5, 4.0, 3.5, 3.5, 0.0),
    "Document Parsing": (4.0, 4.0, 4.0, 4.0, 0.0),
    "PDF Parsing": (4.0, 4.0, 4.0, 4.0, 0.0),
    "PDF to Markdown": (4.0, 4.0, 4.5, 4.0, 0.0),
    "PDF to LLM": (4.0, 4.0, 4.0, 4.0, 0.0),
    "Document to Markdown": (4.5, 4.0, 4.5, 4.5, 0.0),
    "Article Extraction": (3.5, 3.5, 3.5, 3.5, 0.0),
    "Temporal Knowledge Graph": (2.5, 3.0, 2.5, 3.0, 0.5),
    "Knowledge Base/RAG": (2.5, 3.0, 2.5, 3.0, 0.0),
    "RAG/Document Intelligence": (3.0, 3.5, 2.5, 3.5, 0.0),
    "RAG/Workflow": (3.0, 3.5, 2.5, 3.0, 0.5),
    "Coding/Framework": (3.5, 4.0, 3.0, 3.5, 0.0),
    "Document to IM": (4.0, 4.0, 4.0, 4.0, 0.0),
}

ABSORPTION_BONUS = {
    "Adapter": 0.5,
    "优先Adapter": 0.5,
    "Adapter/参考": 0.3,
    "候选Adapter": 0.4,
    "Adapter候选": 0.4,
    "参考/Adapter": 0.3,
    "参考/候选Adapter": 0.2,
    "只参考": -0.2,
    "参考": 0.0,
    "候选": 0.1,
    "后置参考": -0.3,
    "后置Adapter": -0.1,
    "谨慎后置": -0.5,
    "工具候选": 0.2,
    "只参考/后置": -0.3,
    "只收集/不自动执行": -0.5,
    "后置/参考": -0.3,
    "插件筛选": 0.1,
    "替代参考": 0.0,
    "直接可用": 0.5,
}

RISK_PENALTY = {
    "standard_review": 0.0,
    "must_review_before_use": 1.0,
}


def category_key(raw: str) -> str:
    """Normalize category to match scoring table."""
    # Handle combined categories like "RAG / AI App Platform"
    for key in CATEGORY_SCORES:
        if key.lower() in raw.lower():
            return key
    return raw


def score_registry_entry(entry: dict) -> dict:
    cat = category_key(entry.get("category", ""))
    base = CATEGORY_SCORES.get(cat, (2.0, 2.0, 2.0, 2.0, 0.5))

    abs_mode = entry.get("absorption_mode", "参考")
    bonus = ABSORPTION_BONUS.get(abs_mode, 0.0)

    risk_policy = entry.get("risk_policy", "standard_review")
    risk_pen = RISK_PENALTY.get(risk_policy, 0.0)

    token_saving, efficiency_gain, local_first, system_fit, base_penalty = base
    total_penalty = base_penalty + risk_pen + (-bonus if bonus < 0 else 0)
    system_fit = min(system_fit + bonus, 5.0)

    result = score_project(
        token_saving=token_saving,
        efficiency_gain=efficiency_gain,
        local_first=local_first,
        system_fit=system_fit,
        risk_penalty=total_penalty,
        risk_level="high" if risk_policy == "must_review_before_use" else "low",
    )

    return {
        "repo": entry["name"],
        "category": entry["category"],
        "absorption_mode": entry["absorption_mode"],
        "recommended_target": entry["recommended_target"],
        "summary": entry.get("note", ""),
        "scores": {
            "token_saving": result.token_saving,
            "efficiency_gain": result.efficiency_gain,
            "local_first": result.local_first,
            "system_fit": result.system_fit,
            "risk_penalty": result.risk_penalty,
            "total": result.total,
        },
        "qualifies": result.qualifies,
        "risk_level": "high" if risk_policy == "must_review_before_use" else "low",
        "next_action": "generate_intake_card" if result.qualifies else "review",
    }


def main():
    raise RuntimeError(
        "legacy screening export is disabled until server-owned Phase 5 review provenance exists"
    )


if __name__ == "__main__":
    main()
