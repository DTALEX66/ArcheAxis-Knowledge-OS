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
import json
import sqlite3
import zipfile
from pathlib import Path
from typing import Any


# Anki stores a note's fields joined by the unit separator, and its scheduling columns are
# integers in its own vocabulary. They are read here as the source's facts, never re-authored.
UNIT_SEPARATOR = "\x1f"
CARD_TYPES = {0: "new", 1: "learning", 2: "review", 3: "relearning"}
CARD_QUEUES = {0: "new", 1: "learning", 2: "review", 3: "day_learning", 4: "preview", -1: "suspended", -2: "buried", -3: "user_buried"}


def parse_apkg(path: str | Path) -> list[dict[str, Any]]:
    """Read an Anki package into units, keeping the source's scheduling the source's.

    The scheduling numbers are the collection's own record of how Anki scheduled each card. They
    travel as `source_schedule` under `scheduling_origin: "imported_from_source"`, because this
    function graded nothing: no card here was answered by a person and none was judged by a model.
    Importing must not launder a source's numbers into a review this workspace never performed,
    and a card that has never been answered carries no interval rather than an interval of zero.
    """
    path = Path(path)
    try:
        with zipfile.ZipFile(path) as container:
            if "collection.anki2" not in set(container.namelist()):
                raise AdapterError("package carries no collection.anki2")
            raw = container.read("collection.anki2")
    except zipfile.BadZipFile as error:
        raise AdapterError(f"unreadable package: {error}") from error

    connection = sqlite3.connect(":memory:")
    try:
        connection.deserialize(raw)
        note_types = _note_type_names(connection)
        cards: dict[int, list[dict[str, Any]]] = {}
        for row in connection.execute(
            "SELECT id, nid, ord, type, queue, due, ivl, factor, reps, lapses FROM cards"
        ):
            card_id, note_id, ordinal, type_, queue, due, ivl, factor, reps, lapses = row
            answered = reps > 0
            cards.setdefault(note_id, []).append({
                "card_id": card_id,
                "template_ordinal": ordinal,
                "state": CARD_TYPES.get(type_, f"unknown({type_})"),
                "queue": CARD_QUEUES.get(queue, f"unknown({queue})"),
                # Absent, not zero: an unanswered card has no interval and no ease to report.
                "interval_days": ivl if answered else None,
                "due": due,
                "ease_per_mille": factor if answered else None,
                "reviews": reps,
                "lapses": lapses,
            })
        units: list[dict[str, Any]] = []
        for note_id, mid, flds, tags in connection.execute(
            "SELECT id, mid, flds, tags FROM notes"
        ):
            units.append({
                "note_id": note_id,
                "note_type": note_types.get(mid, f"unknown({mid})"),
                "fields": flds.split(UNIT_SEPARATOR),
                "tags": [tag for tag in str(tags).split() if tag],
                "cards": cards.get(note_id, []),
                "scheduling_origin": "imported_from_source",
                "authority_effect": "candidate_or_measurement_only",
            })
        return units
    finally:
        connection.close()


def _note_type_names(connection: sqlite3.Connection) -> dict[int, str]:
    """Anki keeps its note types as JSON in col.models, keyed by a stringified id."""
    try:
        row = connection.execute("SELECT models FROM col").fetchone()
        models = json.loads(row[0]) if row else {}
    except (sqlite3.Error, ValueError, TypeError):
        return {}
    names: dict[int, str] = {}
    for key, model in models.items():
        try:
            names[int(key)] = str(model.get("name", key))
        except (TypeError, ValueError):
            continue
    return names

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
    for item in items:
        item_type = str(item.get("itemType", "")).strip()
        title = str(item.get("title", "")).strip()
        if not title:
            continue
        creators = []
        for creator in item.get("creators", []):
            first = str(creator.get("firstName", "")).strip()
            last = str(creator.get("lastName", "")).strip()
            name = f"{first} {last}".strip()
            if name:
                creators.append(name)
        units.append({
            "title": title,
            "item_type": item_type,
            "creators": creators,
            "year": str(item.get("date", ""))[:4] if item.get("date") else None,
            "doi": item.get("DOI"),
            "url": item.get("url"),
            "abstract_note": item.get("abstractNote"),
        })
    return units
