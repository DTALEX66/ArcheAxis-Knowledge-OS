"""Shared SQLite storage for IR + KB APIs — extends Cognitive-OS database."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = _PROJECT_ROOT / "data" / "cognitive_os.sqlite"

IR_KB_TABLES = """
CREATE TABLE IF NOT EXISTS ir_research_notes (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'manual',
    tags_json TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS ir_intake_cards (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    why TEXT NOT NULL,
    what_to_absorb_json TEXT NOT NULL DEFAULT '[]',
    what_not_to_absorb_json TEXT NOT NULL DEFAULT '[]',
    source_ids_json TEXT NOT NULL DEFAULT '[]',
    risk_level TEXT NOT NULL DEFAULT 'low',
    target_repo TEXT NOT NULL DEFAULT 'Knowledge-Base',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS ir_contracts (
    id TEXT PRIMARY KEY,
    goal TEXT NOT NULL,
    deliverables_json TEXT NOT NULL DEFAULT '[]',
    acceptance_criteria_json TEXT NOT NULL DEFAULT '[]',
    blocked_actions_json TEXT NOT NULL DEFAULT '[]',
    risk_level TEXT NOT NULL DEFAULT 'low',
    target_repo TEXT NOT NULL DEFAULT 'Cognitive-OS',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS ir_daily_briefs (
    id TEXT PRIMARY KEY,
    date TEXT NOT NULL,
    sections_json TEXT NOT NULL DEFAULT '{}',
    github_projects_json TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS kb_documents (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'unknown',
    tags_json TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS kb_cards (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    source_ids_json TEXT NOT NULL DEFAULT '[]',
    tags_json TEXT NOT NULL DEFAULT '[]',
    review_status TEXT NOT NULL DEFAULT 'draft',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS kb_context_packs (
    id TEXT PRIMARY KEY,
    goal TEXT NOT NULL,
    sources_json TEXT NOT NULL DEFAULT '[]',
    evidence_json TEXT NOT NULL DEFAULT '[]',
    constraints_json TEXT NOT NULL DEFAULT '[]',
    token_budget INTEGER NOT NULL DEFAULT 4000,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS kb_taskpacks (
    id TEXT PRIMARY KEY,
    goal TEXT NOT NULL,
    steps_json TEXT NOT NULL DEFAULT '[]',
    allowed_tools_json TEXT NOT NULL DEFAULT '[]',
    blocked_tools_json TEXT NOT NULL DEFAULT '[]',
    constraints_json TEXT NOT NULL DEFAULT '[]',
    success_criteria_json TEXT NOT NULL DEFAULT '[]',
    risk_level TEXT NOT NULL DEFAULT 'low',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


def _conn() -> sqlite3.Connection:
    c = sqlite3.connect(str(DB_PATH))
    c.execute("PRAGMA journal_mode=WAL")
    c.row_factory = sqlite3.Row
    return c


def init():
    c = _conn()
    c.executescript(IR_KB_TABLES)
    c.commit()
    c.close()


# ── Generic helpers ──

def _json_load(s: str | None) -> Any:
    if not s:
        return s
    try:
        return json.loads(s)
    except (json.JSONDecodeError, TypeError):
        return s


def _json_dump(v: Any) -> str:
    return json.dumps(v, ensure_ascii=False)


def _row_dict(row: sqlite3.Row) -> dict:
    d = dict(row)
    for k in list(d):
        if k.endswith("_json"):
            base = k[:-5]
            d[base] = _json_load(d[k])
            del d[k]
    return d


def insert(table: str, data: dict) -> None:
    c = _conn()
    # Get actual table columns
    cols = {r[1] for r in c.execute(f"PRAGMA table_info({table})").fetchall()}
    # Auto-map list/dict fields to _json column names
    mapped = {}
    for k, v in data.items():
        col = f"{k}_json" if isinstance(v, (list, dict)) else k
        if col in cols:
            mapped[col] = _json_dump(v) if isinstance(v, (list, dict)) else v
    if not mapped:
        c.close(); return
    keys = list(mapped)
    placeholders = ",".join(["?" for _ in keys])
    values = list(mapped.values())
    c.execute(f"INSERT OR REPLACE INTO {table} ({','.join(keys)}) VALUES ({placeholders})", values)
    c.commit()
    c.close()


def select_all(table: str, limit: int = 100, order: str = "created_at DESC") -> list[dict]:
    c = _conn()
    rows = c.execute(f"SELECT * FROM {table} ORDER BY {order} LIMIT ?", (limit,)).fetchall()
    c.close()
    return [_row_dict(r) for r in rows]


def select_one(table: str, id_val: str) -> dict | None:
    c = _conn()
    row = c.execute(f"SELECT * FROM {table} WHERE id=?", (id_val,)).fetchone()
    c.close()
    return _row_dict(row) if row else None


def count(table: str) -> int:
    c = _conn()
    n = c.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    c.close()
    return n


# Auto-init
init()
