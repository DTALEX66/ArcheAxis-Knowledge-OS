"""Crawl4AI adapter — web page → LLM-ready Markdown.

Fallback chain: Crawl4AI → Trafilatura → requests.
"""
from dataclasses import dataclass, field

@dataclass
class CrawledPage:
    url: str = ""
    title: str = ""
    content: str = ""
    markdown: str = ""
    metadata: dict = field(default_factory=dict)
    links: list = field(default_factory=list)
    errors: list = field(default_factory=list)

def crawl_url(url: str) -> CrawledPage:
    """Phase 1 stub; Phase 2: integrate crawl4ai."""
    return CrawledPage(url=url, title="[stub]",
        content=f"[not crawled: {url}]",
        errors=["Crawl4AI not yet integrated"])
