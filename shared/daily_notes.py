"""Daily notes engine — time-based knowledge capture and timeline.

Absorbs Obsidian's daily notes + Logseq's journal: auto-create
daily pages, link notes to dates, and provide a timeline view.

Usage:
    from shared.daily_notes import get_or_create_daily, timeline
    note = get_or_create_daily()  # today's note
    entries = timeline(days=7)    # last week's entries
"""

from __future__ import annotations

import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_PROJECT_ROOT))

from shared.storage import insert, select_all, select_one  # noqa: E402


def get_daily(day: str = "") -> dict[str, Any] | None:
    """Read a daily note without creating or mutating storage."""
    return select_one("daily_notes", day or date.today().isoformat())


def get_or_create_daily(day: str = "") -> dict[str, Any]:
    """Get or create the daily note for a given day.

    Args:
        day: ISO date string (YYYY-MM-DD). Default: today.

    Returns:
        The daily note dict.
    """
    if not day:
        day = date.today().isoformat()

    existing = get_daily(day)
    if existing:
        return existing

    now = datetime.now(timezone.utc).isoformat()
    note = {
        "id": day,
        "date": day,
        "content": f"# {day}\n\n",
        "tags": ["daily-note"],
        "created_at": now,
        "updated_at": now,
    }
    insert("daily_notes", note)
    return note


def append_to_daily(content: str, day: str = "", heading: str = "") -> dict[str, Any]:
    """Append content to a daily note.

    Args:
        content: text to append.
        day: target day (default: today).
        heading: optional ## heading to add before content.

    Returns:
        The updated note.
    """
    note = get_or_create_daily(day)

    now = datetime.now(timezone.utc).isoformat()
    entry = f"\n\n{now[:19]} "
    if heading:
        entry += f"## {heading}\n\n"
    entry += content

    note["content"] = (note.get("content", "") + entry).strip()
    note["updated_at"] = now
    insert("daily_notes", note)
    return note


def timeline(days: int = 7, tag: str = "") -> list[dict[str, Any]]:
    """Return daily notes for the last N days, newest first.

    Args:
        days: number of days back.
        tag: optional filter by tag.

    Returns:
        List of daily note dicts with date, content preview.
    """
    rows = select_all("daily_notes", limit=500, order="date DESC")
    cutoff = (date.today() - timedelta(days=days - 1)).isoformat()
    result = []
    for r in rows:
        if r.get("date", "") >= cutoff:
            result.append(
                {
                    "date": r.get("date"),
                    "preview": (r.get("content", "") or "")[:300],
                    "tag_count": len(r.get("tags", [])),
                }
            )
    return result


def link_to_daily(doc_id: str, day: str = "", context: str = "") -> dict[str, Any]:
    """Create a link entry connecting a document to a daily note.

    Equivalent to adding a [[link]] to today's note.
    """
    from shared.backlinks import index_document_links

    note = get_or_create_daily(day)
    link_text = f"[[{doc_id}]]"
    if context:
        link_text += f" — {context}"
    note["content"] = (note.get("content", "") + f"\n- {link_text}").strip()
    note["updated_at"] = datetime.now(timezone.utc).isoformat()
    insert("daily_notes", note)

    # Also index the link for backlinks
    index_document_links(note["id"], note["content"])

    return note
