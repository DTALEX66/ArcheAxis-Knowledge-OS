"""GitHub trending repos collector — multi-category parallel search with dedup.

Enhancement P2-2: supports multiple topic categories, result deduplication,
and auto-detection of already-registered projects in the open-source registry.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field


@dataclass
class TrendingRepo:
    repo: str  # "owner/name"
    description: str = ""
    stars: int = 0
    stars_today: int = 0
    language: str = ""
    url: str = ""
    topics: list = field(default_factory=list)
    updated_at: str = ""
    category: str = ""  # which category query found it
    already_registered: bool = False  # already in open-source registry


# Multi-category search config — each category has its own keywords
CATEGORIES = {
    "ai-ml": [
        "ai",
        "llm",
        "agent",
        "rag",
        "gpt",
        "langchain",
        "openai",
        "ollama",
        "vector",
        "embedding",
        "prompt",
        "chatbot",
        "deepseek",
        "claude",
        "mcp",
        "codex",
        "copilot",
        "transformer",
        "machine-learning",
        "deep-learning",
        "nlp",
    ],
    "dev-tools": [
        "cli",
        "devtools",
        "developer-tools",
        "git",
        "vscode",
        "terminal",
        "shell",
        "workflow",
        "automation",
        "ci-cd",
        "docker",
        "kubernetes",
        "terraform",
    ],
    "knowledge-mgmt": [
        "knowledge-base",
        "obsidian",
        "note-taking",
        "markdown",
        "second-brain",
        "pkm",
        "zettelkasten",
        "wiki",
        "documentation",
        "mindmap",
        "graph",
        "knowledge-graph",
    ],
    "data-eng": [
        "etl",
        "pipeline",
        "data-engineering",
        "spark",
        "airflow",
        "dbt",
        "data-quality",
        "data-lake",
        "sql",
        "postgres",
    ],
    "security": [
        "security",
        "vulnerability",
        "saST",
        "pentest",
        "cve",
        "owasp",
        "auth",
        "oauth",
        "rbac",
        "zero-trust",
    ],
}

# Flattened keywords for the fallback/generic search
_ALL_KEYWORDS: list[str] = []
for _kw_list in CATEGORIES.values():
    _ALL_KEYWORDS.extend(_kw_list)
_ALL_KEYWORDS = sorted(set(_ALL_KEYWORDS))


def _search_github(query: str, per_page: int = 10) -> list[dict]:
    """Reject the retired direct GitHub search path."""
    del query, per_page
    raise RuntimeError("legacy GitHub search is disabled; use the canonical ResearchPackage API")


def _load_registry_repos() -> set[str]:
    """Load already-registered repo names from the open-source registry."""
    try:
        from pathlib import Path

        registry_path = (
            Path(__file__).resolve().parents[3]
            / "shared-contracts"
            / "registries"
            / "open_source_project_registry.json"
        )
        if registry_path.exists():
            data = json.loads(registry_path.read_text(encoding="utf-8"))
            return {p.get("name", "") for p in data.get("projects", [])}
    except Exception:
        pass
    return set()


def collect_trending(
    language: str | None = None,
    since: str = "weekly",
    per_page: int = 10,
) -> list[TrendingRepo]:
    """Reject the retired ungoverned external collection path."""
    del language, since, per_page
    raise RuntimeError(
        "legacy GitHub trending collection is disabled; use the canonical ResearchPackage API"
    )


def collect_by_category(
    categories: list[str] | None = None,
    since: str = "weekly",
    per_category: int = 5,
) -> list[TrendingRepo]:
    """Reject the retired ungoverned external collection path."""
    del categories, since, per_category
    raise RuntimeError(
        "legacy GitHub trending collection is disabled; use the canonical ResearchPackage API"
    )


def collect_trending_fallback(count: int = 10) -> list[TrendingRepo]:
    """Reject the retired ungoverned external collection path."""
    del count
    raise RuntimeError(
        "legacy GitHub trending collection is disabled; use the canonical ResearchPackage API"
    )


def _parse_items(items: list[dict], since: str, category: str) -> list[TrendingRepo]:
    """Parse raw GitHub API items into TrendingRepo objects."""
    results = []
    for item in items:
        repo = TrendingRepo(
            repo=item.get("full_name", ""),
            description=(item.get("description") or "")[:200],
            stars=item.get("stargazers_count", 0),
            language=item.get("language") or "",
            url=item.get("html_url", ""),
            topics=item.get("topics", []),
            updated_at=item.get("updated_at", ""),
            category=category,
        )
        days = 1 if since == "daily" else 7
        repo.stars_today = max(1, repo.stars // max(days * 2, 1))
        results.append(repo)
    return results


if __name__ == "__main__":
    raise SystemExit(
        "legacy GitHub trending collection is disabled; use the canonical ResearchPackage API"
    )
