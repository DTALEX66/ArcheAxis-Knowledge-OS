"""Web search tool — delegates to shared/web_search (real implementation)."""
from shared.web_search import search_web as _search, extract_content as _extract


def web_search(query: str):
    return _search(query, limit=5)


def crawl(url: str):
    """Replaces stub: now extracts real content."""
    return _extract(url)
