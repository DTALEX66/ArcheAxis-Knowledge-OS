"""Memory as files — absorbed from ReMe (agentscope-ai).

Memory is not a black box: layered memories and reasoning principles are
exported to human-editable markdown files, and can be re-imported after the
human (or another agent) edits them (report §3.7). Files are the interchange
format; the SQLite stores stay authoritative for query-time recall.

Format per entry:

    ## [<created_at>] <layer> | tags: <a>,<b> | importance: <0..1>
    <content>
    ---

export_markdown(db, out_dir)   → memory/01-working.md … 05-principles.md
import_markdown(db, in_dir)    → parse files back into the layered store
"""

from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.memory.memory_layers import MemoryLayer, _connect as _layers_connect

_ENTRY_HEADER = re.compile(
    r"^## \[([^\]]+)\] (L[1-4]_\w+) \| tags: ([^|]*) \| importance: ([0-9.]+)$"
)
_SEPARATOR = "---"


class MemoryFilesError(ValueError):
    """Raised when memory-file export/import is invalid."""


@dataclass(frozen=True)
class ExportedEntry:
    created_at: str
    layer: str
    tags: tuple[str, ...]
    importance: float
    content: str


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _entries(db: str | Path) -> list[ExportedEntry]:
    conn = _layers_connect(db)
    try:
        rows = conn.execute("SELECT * FROM layered_memory ORDER BY created_at").fetchall()
    finally:
        conn.close()
    entries = []
    for row in rows:
        entries.append(ExportedEntry(
            created_at=row["created_at"], layer=row["layer"],
            tags=tuple(json.loads(row["tags_json"])),
            importance=row["importance"], content=row["content"],
        ))
    return entries


def _principles(db: str | Path) -> list[dict[str, Any]]:
    conn = sqlite3.connect(Path(db))
    conn.row_factory = sqlite3.Row
    conn.executescript(
        "CREATE TABLE IF NOT EXISTS reasoning_principles (principle_id TEXT PRIMARY KEY, "
        "statement TEXT NOT NULL, category TEXT NOT NULL, source_trajectory_ids_json TEXT NOT NULL, "
        "confidence REAL NOT NULL DEFAULT 0.5, usage_count INTEGER NOT NULL DEFAULT 0, "
        "last_applied TEXT, status TEXT NOT NULL DEFAULT 'candidate', created_at TEXT NOT NULL);"
    )
    try:
        rows = conn.execute("SELECT * FROM reasoning_principles ORDER BY created_at").fetchall()
    finally:
        conn.close()
    return [dict(r) for r in rows]


def export_markdown(db: str | Path, out_dir: str | Path) -> dict[str, int]:
    """Export layered memory + principles to markdown files (human-editable)."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    counts: dict[str, int] = {}

    by_layer: dict[str, list[ExportedEntry]] = {}
    for entry in _entries(db):
        by_layer.setdefault(entry.layer, []).append(entry)
    for layer in MemoryLayer:
        entries = by_layer.get(layer.value, [])
        lines = [f"# Memory layer {layer.value}", ""]
        for e in entries:
            lines.append(f"## [{e.created_at}] {e.layer} | tags: {','.join(e.tags)} | importance: {e.importance}")
            lines.append(e.content)
            lines.append(_SEPARATOR)
        (out / f"{layer.value}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        counts[layer.value] = len(entries)

    principles = _principles(db)
    plines = ["# Reasoning principles", ""]
    for p in principles:
        plines.append(f"## [{p['created_at']}] {p['category']} | confidence: {p['confidence']} | status: {p['status']}")
        plines.append(p["statement"])
        plines.append(_SEPARATOR)
    (out / "principles.md").write_text("\n".join(plines) + "\n", encoding="utf-8")
    counts["principles"] = len(principles)
    return counts


def _parse_file(path: Path) -> list[ExportedEntry]:
    text = path.read_text(encoding="utf-8")
    entries: list[ExportedEntry] = []
    current: dict[str, Any] | None = None
    content_lines: list[str] = []
    for line in text.splitlines():
        header = _ENTRY_HEADER.match(line)
        if header:
            if current is not None:
                entries.append(ExportedEntry(**current, content="\n".join(content_lines).strip()))
            current = {
                "created_at": header.group(1), "layer": header.group(2),
                "tags": tuple(t.strip() for t in header.group(3).split(",") if t.strip()),
                "importance": float(header.group(4)),
            }
            content_lines = []
            continue
        if line.strip() == _SEPARATOR and current is not None:
            entries.append(ExportedEntry(**current, content="\n".join(content_lines).strip()))
            current = None
            content_lines = []
            continue
        if current is not None:
            content_lines.append(line)
    if current is not None:
        entries.append(ExportedEntry(**current, content="\n".join(content_lines).strip()))
    return entries


def import_markdown(db: str | Path, in_dir: str | Path) -> dict[str, int]:
    """Parse exported markdown files back into the layered memory store."""
    folder = Path(in_dir)
    if not folder.is_dir():
        raise MemoryFilesError(f"not a directory: {folder}")
    counts: dict[str, int] = {}
    conn = _layers_connect(db)
    try:
        for path in sorted(folder.glob("L*_*.md")):
            layer_name = path.stem
            entries = _parse_file(path)
            for e in entries:
                if e.layer != layer_name:
                    continue
                conn.execute(
                    "INSERT OR IGNORE INTO layered_memory "
                    "(memory_id, layer, content, tags_json, importance, created_at) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (f"mem_{abs(hash((e.content, e.layer))) % 10**12:012d}", e.layer,
                     e.content, _json(list(e.tags)), e.importance, e.created_at),
                )
            counts[layer_name] = len(entries)
    finally:
        conn.commit()
        conn.close()
    return counts
