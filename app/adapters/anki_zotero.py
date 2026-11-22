"""Anki / Zotero adapters — absorbed from ABSORPTION_EXECUTION_MATRIX 包 E.

Local-file bridges (no live HTTP in the default path):
    to_anki_csv(cards)      → CSV text importable by Anki (front, back, tags)
    parse_zotero_json(items) → Zotero library export → knowledge-unit dicts
                              (title / creators / year / DOI / url / notes)

Both are deterministic and offline; the caller decides when to write files.
Zotero items are candidate material — they still need evidence governance
before becoming verified knowledge.
"""

from __future__ import annotations

import csv
import io
import re
from typing import Any


class AdapterError(ValueError):
    """Raised when an adapter receives invalid input."""


def to_anki_csv(cards: list[dict[str, Any]]) -> str:
    """Serialize cards to Anki-importable CSV (front, back, tags)."""
    if not cards:
        raise AdapterError("cards must be non-empty")
    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_ALL, lineterminator="\n")
    for card in cards:
        front = str(card.get("front", "")).strip()
        back = str(card.get("back", "")).strip()
        tags = card.get("tags", [])
        if not front or not back:
            raise AdapterError("each card requires front and back")
        if isinstance(tags, str):
            tags = [tags]
        writer.writerow([front, back, " ".join(str(t) for t in tags)])
    return output.getvalue()


def parse_zotero_json(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Parse a Zotero library export into knowledge-unit dicts."""
    units: list[dict[str, Any]] = []
    for record in items:
        item = record.get("data", record)
        item_type = str(item.get("itemType", "")).strip()
        title = str(item.get("title", "")).strip()
        if not title:
            continue
        creators = []
        for creator in item.get("creators", []):
            first = str(creator.get("firstName", "")).strip()
            last = str(creator.get("lastName", "")).strip()
            name = str(creator.get("name") or f"{first} {last}").strip()
            if name:
                creators.append(name)
        date = record.get("meta", {}).get("parsedDate") or item.get("date") or ""
        year = re.search(r"\b[12]\d{3}\b", str(date))
        units.append({
            "title": title,
            "item_type": item_type,
            "creators": creators,
            "year": year.group() if year else None,
            "doi": item.get("DOI"),
            "url": item.get("url"),
            "abstract_note": item.get("abstractNote"),
        })
    return units
