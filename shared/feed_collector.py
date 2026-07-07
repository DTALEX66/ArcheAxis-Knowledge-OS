"""RSS/Atom feed collector — multi-source knowledge discovery.

Absorbs: feedparser + blogwatcher patterns.
Collects articles from RSS/Atom feeds, extracts content, and
feeds into the IR pipeline for intake evaluation.

Usage:
    from shared.feed_collector import collect_feeds, discover_feeds
    items = collect_feeds(["https://example.com/feed.xml"], max_items=10)
"""

from __future__ import annotations

import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_PROJECT_ROOT))


# ── Built-in feed discovery ─────────────────────────────


BUILTIN_FEEDS: dict[str, list[str]] = {
    "ai-ml": [
        "https://arxiv.org/rss/cs.AI",
        "https://arxiv.org/rss/cs.CL",
        "https://arxiv.org/rss/cs.LG",
        "https://huggingface.co/blog/feed.xml",
    ],
    "dev-tools": [
        "https://github.blog/feed/",
        "https://devblogs.microsoft.com/python/feed/",
    ],
    "knowledge-mgmt": [
        "https://forum.obsidian.md/feed/blog.rss",
    ],
    "open-source": [
        "https://github.com/trending/python?since=weekly.atom",
    ],
}


# ── Parser (zero-dependency XML) ────────────────────────


def _parse_rss(xml_bytes: bytes) -> list[dict[str, Any]]:
    """Parse RSS 2.0 XML into items."""
    root = ET.fromstring(xml_bytes)
    items = []
    for item in root.iter("item"):
        entry: dict[str, Any] = {
            "title": "",
            "link": "",
            "description": "",
            "published": "",
            "source_feed": "",
        }
        for child in item:
            tag = child.tag.lower()
            if tag == "title":
                entry["title"] = (child.text or "").strip()
            elif tag == "link":
                entry["link"] = (child.text or "").strip()
            elif tag in ("description", "summary"):
                entry["description"] = (child.text or "")[:500]
            elif tag in ("pubdate", "published", "updated"):
                entry["published"] = (child.text or "").strip()
        if entry["title"] or entry["link"]:
            items.append(entry)
    return items


def _parse_atom(xml_bytes: bytes) -> list[dict[str, Any]]:
    """Parse Atom XML into items."""
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    root = ET.fromstring(xml_bytes)
    items = []
    for entry in root.findall("atom:entry", ns):
        title_el = entry.find("atom:title", ns)
        link_el = entry.find("atom:link", ns)
        summary_el = entry.find("atom:summary", ns)
        updated_el = entry.find("atom:updated", ns)

        link = ""
        if link_el is not None:
            link = link_el.get("href", "")

        items.append(
            {
                "title": (title_el.text or "").strip() if title_el is not None else "",
                "link": link,
                "description": ((summary_el.text or "")[:500] if summary_el is not None else ""),
                "published": (updated_el.text or "").strip() if updated_el is not None else "",
                "source_feed": "",
            }
        )
    return items


def _fetch_url(url: str, timeout: int = 15) -> bytes | None:
    """Fetch a URL, return bytes or None."""
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Cognitive-Loop-OS/0.3 Feed Collector",
                "Accept": "application/rss+xml, application/atom+xml, application/xml",
            },
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read()
    except Exception:
        return None


# ── Public API ──────────────────────────────────────────


def collect_feeds(
    urls: list[str],
    max_items: int = 20,
) -> list[dict[str, Any]]:
    """Collect articles from RSS/Atom feeds.

    Args:
        urls: list of feed URLs.
        max_items: max total items to return.

    Returns:
        List of items with title, link, description, published, source_feed.
    """
    results: list[dict[str, Any]] = []
    seen: set[str] = set()

    for url in urls:
        if len(results) >= max_items:
            break
        data = _fetch_url(url)
        if not data:
            continue

        # Try RSS, then Atom
        items = _parse_rss(data)
        if not items:
            items = _parse_atom(data)

        for item in items:
            key = item["link"] or item["title"]
            if key in seen:
                continue
            seen.add(key)
            item["source_feed"] = url
            results.append(item)
            if len(results) >= max_items:
                break

    return results


def discover_feeds(categories: list[str] | None = None) -> dict[str, list[str]]:
    """Return built-in feed URLs by category."""
    if categories is None:
        return BUILTIN_FEEDS
    return {c: BUILTIN_FEEDS.get(c, []) for c in categories}


def collect_and_ingest(
    urls: list[str],
    max_items: int = 10,
) -> dict[str, Any]:
    """Collect feeds and ingest into IR as research notes.

    Returns:
        {collected, ingested, items}.
    """
    import uuid

    from shared.storage import insert

    items = collect_feeds(urls, max_items=max_items)
    now = datetime.now(timezone.utc).isoformat()

    ingested = 0
    for item in items:
        note_id = f"rn_{uuid.uuid4().hex[:12]}"
        insert(
            "ir_research_notes",
            {
                "id": note_id,
                "title": item.get("title", "Untitled")[:200],
                "content": item.get("description", "")[:2000],
                "source": item.get("source_feed", "rss"),
                "tags": ["rss-feed"],
                "created_at": now,
            },
        )
        ingested += 1

    return {"collected": len(items), "ingested": ingested, "items": items}
