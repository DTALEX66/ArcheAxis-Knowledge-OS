"""GitHub trending repos collector — GitHub Search API (no auth for public)."""
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional
import json
import urllib.request
import urllib.error


@dataclass
class TrendingRepo:
    repo: str          # "owner/name"
    description: str = ""
    stars: int = 0
    stars_today: int = 0
    language: str = ""
    url: str = ""
    topics: list = field(default_factory=list)
    updated_at: str = ""


# AI/ML topics to filter for
_AI_TOPICS = {
    "ai", "machine-learning", "deep-learning", "llm", "rag",
    "agent", "nlp", "transformer", "gpt", "langchain", "openai",
    "ollama", "embedding", "vector-database", "prompt-engineering",
    "mcp", "coding-agent", "code-generation", "claude", "deepseek",
}

_AI_KEYWORDS = [
    "ai", "llm", "agent", "rag", "gpt", "langchain", "openai",
    "ollama", "vector", "embedding", "prompt", "chatbot",
    "deepseek", "claude", "mcp", "codex", "copilot",
]


def _search_github(query: str, per_page: int = 10) -> list[dict]:
    """Search GitHub repos via REST API. No auth = 10 req/min."""
    url = (
        f"https://api.github.com/search/repositories"
        f"?q={urllib.request.quote(query)}"
        f"&sort=stars&order=desc&per_page={per_page}"
    )
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github.v3+json")
    req.add_header("User-Agent", "Cognitive-Loop-OS/0.2")

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("items", [])
    except urllib.error.HTTPError as e:
        if e.code == 403:
            print(f"GitHub API rate limited: {e}")
        return []
    except Exception as e:
        print(f"GitHub API error: {e}")
        return []


def collect_trending(
    language: Optional[str] = None,
    since: str = "weekly",
    per_page: int = 10,
) -> list[TrendingRepo]:
    """Collect trending AI repos from GitHub.

    Args:
        language: filter by language (None = all)
        since: "daily" or "weekly"
        per_page: max repos to return (capped at 30)
    """
    per_page = min(per_page, 30)  # GitHub API max

    # Date filter
    days = 1 if since == "daily" else 7
    date_cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")

    # Build query: AI-related repos created/updated recently
    ai_query = " OR ".join(_AI_KEYWORDS)
    query = f"({ai_query}) created:>={date_cutoff}"
    if language:
        query += f" language:{language}"

    items = _search_github(query, per_page=per_page)

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
        )
        # Approximate stars_today from total (rough estimate)
        days_since = 1 if since == "daily" else 7
        repo.stars_today = max(1, repo.stars // max(days_since * 2, 1))
        results.append(repo)

    return results


def collect_trending_fallback(count: int = 10) -> list[TrendingRepo]:
    """Fallback: search recent AI repos without date filter (broader)."""
    ai_query = " OR ".join(_AI_KEYWORDS[:5])  # fewer keywords for broader results
    query = f"({ai_query})"
    items = _search_github(query, per_page=count)
    return [
        TrendingRepo(
            repo=item.get("full_name", ""),
            description=(item.get("description") or "")[:200],
            stars=item.get("stargazers_count", 0),
            language=item.get("language") or "",
            url=item.get("html_url", ""),
            topics=item.get("topics", []),
            updated_at=item.get("updated_at", ""),
        )
        for item in items
    ]


# ── Quick test ──
if __name__ == "__main__":
    print("Fetching trending AI repos (weekly)...")
    repos = collect_trending(since="weekly", per_page=5)
    if not repos:
        print("No results from trending, trying fallback...")
        repos = collect_trending_fallback(5)

    for i, r in enumerate(repos, 1):
        print(f"  {i}. {r.repo} ⭐{r.stars} ({r.language}) - {r.description[:80]}")
    print(f"\nTotal: {len(repos)} repos found")
