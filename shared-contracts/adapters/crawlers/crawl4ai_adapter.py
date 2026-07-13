"""Crawl adapter — Crawl4AI first, then the shared extraction fallback chain."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse


@dataclass
class CrawledPage:
    url: str = ""
    title: str = ""
    content: str = ""
    markdown: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    links: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def crawl_url(url: str) -> CrawledPage:
    """Fetch one HTTP(S) page and return real extracted Markdown or explicit errors."""
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("url must be an absolute http(s) URL")

    errors: list[str] = []
    try:
        from app.ingestion.multi_format import convert_url

        markdown, engine = convert_url(url)
        if markdown.strip():
            return CrawledPage(
                url=url,
                content=markdown,
                markdown=markdown,
                metadata={"engine": engine, "character_count": len(markdown)},
            )
    except Exception as exc:
        errors.append(f"multi-format: {type(exc).__name__}: {exc}")

    try:
        from shared.web_search import extract_content

        result = extract_content(url)
        content = str(result.get("content", ""))
        if content.strip():
            return CrawledPage(
                url=url,
                title=str(result.get("title", "")),
                content=content,
                markdown=content,
                metadata={
                    "engine": result.get("engine", "shared.web_search"),
                    "character_count": len(content),
                },
                errors=errors,
            )
        errors.append("shared.web_search returned empty content")
    except Exception as exc:
        errors.append(f"shared.web_search: {type(exc).__name__}: {exc}")

    return CrawledPage(url=url, errors=errors)
