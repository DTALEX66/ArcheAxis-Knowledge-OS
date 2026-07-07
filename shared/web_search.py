"""Real web search + content extraction — replaces stubs.

Combines DuckDuckGo (no API key) search with trafilatura content extraction.
Falls back to requests + BeautifulSoup for content scraping.

Usage:
    from shared.web_search import search_web, extract_content
    results = search_web("graph rag tutorial", limit=5)
    article = extract_content("https://example.com/article")
"""

from __future__ import annotations

import sys
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_PROJECT_ROOT))


# ── DuckDuckGo search (no API key) ─────────────────────


def _ddg_html_search(query: str, limit: int = 10) -> list[dict[str, Any]]:
    """Search DuckDuckGo via HTML (lite version, no JS)."""
    url = f"https://lite.duckduckgo.com/lite/?q={urllib.parse.quote(query)}"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Cognitive-Loop-OS/0.3 WebSearch",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="replace")
    except Exception:
        return []

    # Parse DuckDuckGo Lite results
    import re

    results = []
    # Match result rows: link + description
    pattern = re.compile(
        r'<a[^>]*href="([^"]+)"[^>]*class="result-link"[^>]*>(.*?)</a>.*?'
        r'<td class="result-snippet">(.*?)</td>',
        re.DOTALL,
    )
    matches = pattern.findall(html)

    for href, title_raw, snippet in matches[:limit]:
        # Clean HTML tags from title
        title = re.sub(r"<[^>]+>", "", title_raw).strip()
        desc = re.sub(r"<[^>]+>", "", snippet).strip()
        if href and title:
            results.append(
                {
                    "title": title,
                    "url": href,
                    "description": desc[:300],
                }
            )

    return results


# ── Public API ──────────────────────────────────────────


def search_web(query: str, limit: int = 5) -> dict[str, Any]:
    """Search the web and return structured results.

    Args:
        query: search query string.
        limit: max results.

    Returns:
        {query, count, results: [{title, url, description}]}.
    """
    results = _ddg_html_search(query, limit=limit)
    return {
        "query": query,
        "count": len(results),
        "results": results,
    }


def extract_content(url: str, max_chars: int = 10000) -> dict[str, Any]:
    """Extract clean text content from a URL.

    Tries trafilatura first, falls back to requests + BeautifulSoup.

    Args:
        url: page URL.
        max_chars: max characters to return.

    Returns:
        {url, title, content, char_count, engine}.
    """
    # Try trafilatura first
    try:
        import trafilatura

        downloaded = trafilatura.fetch_url(url)
        if downloaded:
            result = trafilatura.extract(
                downloaded, include_links=False, include_images=False, include_tables=False
            )
            if result:
                return {
                    "url": url,
                    "title": "",
                    "content": result[:max_chars],
                    "char_count": len(result),
                    "engine": "trafilatura",
                }
    except Exception:
        pass

    # Fallback: requests + BeautifulSoup
    try:
        import requests
        from bs4 import BeautifulSoup

        resp = requests.get(
            url,
            timeout=15,
            headers={
                "User-Agent": "Cognitive-Loop-OS/0.3 ContentExtractor",
            },
        )
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # Remove script, style, nav, footer
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()

        title = soup.title.string if soup.title else ""
        text = soup.get_text(separator="\n", strip=True)
        # Clean up whitespace
        import re

        text = re.sub(r"\n{3,}", "\n\n", text)

        return {
            "url": url,
            "title": title,
            "content": text[:max_chars],
            "char_count": len(text),
            "engine": "requests+bs4",
        }
    except Exception as e:
        return {"url": url, "error": str(e)}


def search_and_extract(
    query: str,
    search_limit: int = 3,
    extract_limit: int = 2,
) -> dict[str, Any]:
    """Search + extract: search, then fetch full content of top results.

    Returns:
        {query, search_results, extracted: [{url, title, content}]}.
    """
    search = search_web(query, limit=search_limit)
    extracted = []
    for r in search["results"][:extract_limit]:
        content = extract_content(r["url"])
        extracted.append(content)

    return {
        "query": query,
        "search_results": search["results"],
        "extracted": extracted,
    }
