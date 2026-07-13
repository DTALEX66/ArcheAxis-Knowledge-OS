"""Batch scoring: score all 50 registry projects → CSV export.

Heuristic scoring based on category + absorption_mode.
"""
import json
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_PROJECT_ROOT))
sys.path.insert(0, str(_PROJECT_ROOT / "Inspiration-Research"))

from project_radar.outputs.generator import export_screening_csv, screen_project  # noqa: E402
from project_radar.scoring.scorer import score_project  # noqa: E402

from shared.config import resolve_runtime_path  # noqa: E402

REGISTRY_PATH = _PROJECT_ROOT / "shared-contracts" / "registries" / "open_source_project_registry.json"


# ── Heuristic scoring by category ──

CATEGORY_SCORES = {
    "Crawler":           (4.0, 4.5, 4.0, 4.0, 0.0),
    "Converter":         (4.5, 4.0, 4.5, 4.0, 0.0),
    "LLM Gateway":       (4.0, 4.5, 3.5, 4.5, 0.0),
    "Observability":     (3.0, 4.0, 3.0, 4.0, 0.0),
    "Evaluation":        (3.5, 4.0, 3.0, 4.0, 0.0),
    "Memory":            (3.0, 3.5, 3.0, 4.0, 0.5),
    "Vector DB":         (3.0, 3.5, 3.0, 3.5, 0.0),
    "Graph DB":          (2.5, 3.0, 2.5, 3.0, 0.5),
    "AI Agent/Coding":   (3.5, 4.5, 3.0, 4.0, 0.5),
    "Multi-Agent":       (2.5, 3.5, 2.0, 3.0, 1.0),
    "Browser Agent":     (2.0, 3.0, 2.0, 3.0, 1.5),
    "RAG/AI Platform":   (3.0, 3.5, 2.5, 3.0, 0.5),
    "LLM Framework":     (3.5, 4.0, 2.5, 3.5, 0.5),
    "Agent SDK":         (3.5, 4.0, 3.0, 4.0, 0.5),
    "Agent State Machine":(3.0, 3.5, 2.5, 3.5, 0.5),
    "Agent/Orchestration":(3.0, 3.5, 2.5, 3.5, 0.5),
    "AI Frontend SDK":   (2.5, 3.0, 2.0, 2.5, 0.0),
    "LLM UI":            (2.0, 2.5, 1.5, 2.0, 0.0),
    "Personal AI/Search":(2.5, 3.0, 2.5, 3.0, 0.0),
    "Second Brain/RAG":  (2.5, 3.0, 2.5, 3.0, 0.0),
    "Private RAG":       (2.5, 3.0, 2.5, 3.0, 0.0),
    "Research Agent":    (3.5, 4.0, 3.0, 4.0, 0.0),
    "Local Code AI":     (3.5, 3.5, 4.0, 3.5, 0.0),
    "CLI Agent":         (3.0, 3.5, 3.0, 3.5, 0.0),
    "AI App Builder":    (2.5, 3.5, 2.0, 2.5, 0.5),
    "Browser Automation":(2.5, 3.0, 2.5, 3.0, 1.0),
    "Crawler Framework": (3.5, 4.0, 3.5, 3.5, 0.0),
    "Web Text Extraction":(3.5, 4.0, 3.5, 3.5, 0.0),
    "Document Parsing":  (4.0, 4.0, 4.0, 4.0, 0.0),
    "PDF Parsing":       (4.0, 4.0, 4.0, 4.0, 0.0),
    "PDF to Markdown":   (4.0, 4.0, 4.5, 4.0, 0.0),
    "PDF to LLM":        (4.0, 4.0, 4.0, 4.0, 0.0),
    "Document to Markdown":(4.5, 4.0, 4.5, 4.5, 0.0),
    "Article Extraction":(3.5, 3.5, 3.5, 3.5, 0.0),
    "Temporal Knowledge Graph":(2.5, 3.0, 2.5, 3.0, 0.5),
    "Knowledge Base/RAG":(2.5, 3.0, 2.5, 3.0, 0.0),
    "RAG/Document Intelligence":(3.0, 3.5, 2.5, 3.5, 0.0),
    "RAG/Workflow":      (3.0, 3.5, 2.5, 3.0, 0.5),
    "Coding/Framework":  (3.5, 4.0, 3.0, 3.5, 0.0),
    "Document to IM":    (4.0, 4.0, 4.0, 4.0, 0.0),
}

ABSORPTION_BONUS = {
    "Adapter": 0.5,
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
    with open(REGISTRY_PATH, encoding="utf-8") as f:
        registry = json.load(f)

    results = [score_registry_entry(e) for e in registry]
    qualified = [r for r in results if r["qualifies"]]

    # Export CSV
    entries = [
        screen_project(
            repo=r["repo"], category=r["category"], summary=r["summary"],
            token_saving=r["scores"]["token_saving"],
            efficiency_gain=r["scores"]["efficiency_gain"],
            local_first=r["scores"]["local_first"],
            system_fit=r["scores"]["system_fit"],
            risk_penalty=r["scores"]["risk_penalty"],
            risk_level=r["risk_level"],
            absorption_mode=r["absorption_mode"],
            recommended_target=r["recommended_target"],
        )
        for r in results
    ]
    csv_path = export_screening_csv(entries)
    print(f"CSV exported: {csv_path}")

    # Print summary
    print("\n=== Batch Scoring Results ===")
    print(f"Total: {len(results)}")
    print(f"Qualified (≥3.5): {len(qualified)}")
    print("Top 10:")

    sorted_results = sorted(results, key=lambda r: r["scores"]["total"], reverse=True)
    for i, r in enumerate(sorted_results[:10], 1):
        flag = "✅" if r["qualifies"] else "❌"
        print(f"  {i:2d}. {flag} {r['repo']:<35s} {r['scores']['total']:5.1f}  {r['category']}")

    print("\nBottom 5:")
    for i, r in enumerate(sorted_results[-5:], 1):
        print(f"  {i}. ❌ {r['repo']:<35s} {r['scores']['total']:5.1f}  {r['category']}")

    # Save JSON results
    output_json = resolve_runtime_path("data/reports/registry_scored.json")
    output_json.parent.mkdir(parents=True, exist_ok=True)
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump({"scored_at": "2026-07-02", "total": len(results),
                    "qualified": len(qualified), "items": sorted_results},
                  f, ensure_ascii=False, indent=2)
    print(f"\nJSON saved: {output_json}")


if __name__ == "__main__":
    main()
