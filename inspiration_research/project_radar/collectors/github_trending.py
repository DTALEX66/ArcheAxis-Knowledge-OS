"""GitHub trending repos collector — multi-category parallel search with dedup.

Enhancement P2-2: supports multiple topic categories, result deduplication,
and auto-detection of already-registered projects in the open-source registry.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

from shared.safe_http import SafeHTTPError, SafeHTTPPolicy, fetch


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
        "ai", "llm", "agent", "rag", "gpt", "langchain", "openai",
        "ollama", "vector", "embedding", "prompt", "chatbot",
        "deepseek", "claude", "mcp", "codex", "copilot", "transformer",
        "machine-learning", "deep-learning", "nlp",
    ],
    "dev-tools": [
        "cli", "devtools", "developer-tools", "git", "vscode",
        "terminal", "shell", "workflow", "automation", "ci-cd",
        "docker", "kubernetes", "terraform",
    ],
    "knowledge-mgmt": [
        "knowledge-base", "obsidian", "note-taking", "markdown",
        "second-brain", "pkm", "zettelkasten", "wiki", "documentation",
        "mindmap", "graph", "knowledge-graph",
    ],
    "data-eng": [
        "etl", "pipeline", "data-engineering", "spark", "airflow",
        "dbt", "data-quality", "data-lake", "sql", "postgres",
    ],
    "security": [
        "security", "vulnerability", "saST", "pentest", "cve",
        "owasp", "auth", "oauth", "rbac", "zero-trust",
    ],
}

# Flattened keywords for the fallback/generic search
_ALL_KEYWORDS: list[str] = []
for _kw_list in CATEGORIES.values():
    _ALL_KEYWORDS.extend(_kw_list)
_ALL_KEYWORDS = sorted(set(_ALL_KEYWORDS))


def _search_github(query: str, per_page: int = 10) -> list[dict]:
    """Search GitHub repos via REST API. No auth = 10 req/min."""
    url = (
        f"https://api.github.com/search/repositories"
        f"?q={quote(query)}"
        f"&sort=stars&order=desc&per_page={per_page}"
    )
    try:
        response = fetch(
            url,
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "Cognitive-Loop-OS/0.3",
            },
            policy=SafeHTTPPolicy(
                timeout=15,
                max_bytes=2_000_000,
                allowed_hosts=("api.github.com",),
                allowed_content_types=("application/json",),
            ),
        )
        data = json.loads(response.body.decode("utf-8"))
        return data.get("items", [])
    except SafeHTTPError as exc:
        if "HTTP status 403" in str(exc):
            print(f"GitHub API rate limited: {exc}")
        return []
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        print(f"GitHub API error: {e}")
        return []


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
    """Collect trending AI repos from GitHub.

    Args:
        language: filter by language (None = all)
        since: "daily" or "weekly"
        per_page: max repos to return (capped at 30)
    """
    per_page = min(per_page, 30)
    days = 1 if since == "daily" else 7
    date_cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")

    ai_query = " OR ".join(_ALL_KEYWORDS[:15])
    query = f"({ai_query}) created:>={date_cutoff}"
    if language:
        query += f" language:{language}"

    items = _search_github(query, per_page=per_page)
    return _parse_items(items, since, "ai-ml")


def collect_by_category(
    categories: list[str] | None = None,
    since: str = "weekly",
    per_category: int = 5,
) -> list[TrendingRepo]:
    """Collect trending repos across multiple topic categories.

    Args:
        categories: list of category keys (default: all). See ``CATEGORIES``.
        since: "daily" or "weekly"
        per_category: max repos per category

    Returns:
        Deduplicated list of TrendingRepo sorted by stars descending.
    """
    if categories is None:
        categories = list(CATEGORIES)

    days = 1 if since == "daily" else 7
    date_cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
    known_repos = _load_registry_repos()

    seen: set[str] = set()
    results: list[TrendingRepo] = []

    for cat in categories:
        keywords = CATEGORIES.get(cat, CATEGORIES["ai-ml"])
        kw_query = " OR ".join(keywords[:8])  # keep query short
        query = f"({kw_query}) created:>={date_cutoff}"

        items = _search_github(query, per_page=per_category)
        for item in items:
            name = item.get("full_name", "")
            if name in seen:
                continue
            seen.add(name)

            repo = TrendingRepo(
                repo=name,
                description=(item.get("description") or "")[:200],
                stars=item.get("stargazers_count", 0),
                language=item.get("language") or "",
                url=item.get("html_url", ""),
                topics=item.get("topics", []),
                updated_at=item.get("updated_at", ""),
                category=cat,
                already_registered=name in known_repos,
            )
            # Approximate stars/day
            days_since = max(1, days * 2)
            repo.stars_today = max(1, repo.stars // days_since)
            results.append(repo)

    results.sort(key=lambda r: r.stars, reverse=True)
    return results[: per_category * len(categories)]


def collect_trending_fallback(count: int = 10) -> list[TrendingRepo]:
    """Fallback: search recent AI repos without date filter (broader)."""
    ai_query = " OR ".join(_ALL_KEYWORDS[:5])
    query = f"({ai_query})"
    items = _search_github(query, per_page=count)
    return _parse_items(items, "weekly", "ai-ml")


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


# ── Quick test ──
if __name__ == "__main__":
    print("Fetching trending repos by category...")
    repos = collect_by_category(categories=["ai-ml", "dev-tools"], per_category=3)
    if not repos:
        print("No results, trying fallback...")
        repos = collect_trending_fallback(5)

    for i, r in enumerate(repos, 1):
        tag = " [REGISTERED]" if r.already_registered else ""
        print(f"  {i}. [{r.category}] {r.repo} ⭐{r.stars} ({r.language}) - {r.description[:80]}{tag}")
    print(f"\nTotal: {len(repos)} repos found")
