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

-- FTS5 full-text indexes for KB search
CREATE VIRTUAL TABLE IF NOT EXISTS kb_documents_fts USING fts5(
    id UNINDEXED,
    title,
    content,
    source,
    tokenize='porter unicode61'
);

CREATE VIRTUAL TABLE IF NOT EXISTS kb_cards_fts USING fts5(
    id UNINDEXED,
    title,
    content,
    tags,
    tokenize='porter unicode61'
);
"""


IR_KB_TABLES_EXT = """
-- P2-1: review + mistake tables for A-line learning loop
CREATE TABLE IF NOT EXISTS kb_reviews (
    id TEXT PRIMARY KEY,
    card_id TEXT NOT NULL,
    quality INTEGER NOT NULL CHECK(quality BETWEEN 0 AND 5),
    interval_days INTEGER NOT NULL DEFAULT 1,
    ease_factor REAL NOT NULL DEFAULT 2.5,
    next_review_at TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS kb_mistakes (
    id TEXT PRIMARY KEY,
    card_id TEXT NOT NULL,
    error_type TEXT NOT NULL DEFAULT 'recall_failure',
    detail TEXT NOT NULL DEFAULT '',
    source_topic TEXT NOT NULL DEFAULT '',
    resolved INTEGER NOT NULL DEFAULT 0,
    resolution_note TEXT NOT NULL DEFAULT '',
    resolved_at TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- P2-3: episodic memory for agent sessions
CREATE TABLE IF NOT EXISTS episodic_memory (
    id TEXT PRIMARY KEY,
    content TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'agent',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    importance REAL NOT NULL DEFAULT 0.5,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE VIRTUAL TABLE IF NOT EXISTS episodic_memory_fts USING fts5(
    id UNINDEXED,
    content,
    source,
    tokenize='porter unicode61'
);

-- Phase 5: machine knowledge + A→B translation
CREATE TABLE IF NOT EXISTS machine_knowledge_units (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    unit_type TEXT NOT NULL DEFAULT 'rule',
    tags_json TEXT NOT NULL DEFAULT '[]',
    confidence REAL NOT NULL DEFAULT 0.5,
    source_type TEXT NOT NULL DEFAULT 'manual',
    source_id TEXT NOT NULL DEFAULT '',
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS a_to_b_candidates (
    id TEXT PRIMARY KEY,
    a_source_type TEXT NOT NULL DEFAULT 'card',
    a_source_id TEXT NOT NULL,
    a_title TEXT NOT NULL DEFAULT '',
    a_content TEXT NOT NULL DEFAULT '',
    a_review_count INTEGER NOT NULL DEFAULT 0,
    a_ease_factor REAL NOT NULL DEFAULT 0.0,
    b_title TEXT NOT NULL DEFAULT '',
    b_content TEXT NOT NULL DEFAULT '',
    b_unit_type TEXT NOT NULL DEFAULT 'rule',
    status TEXT NOT NULL DEFAULT 'pending',
    knowledge_id TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE VIRTUAL TABLE IF NOT EXISTS machine_knowledge_units_fts USING fts5(
    id UNINDEXED,
    title,
    content,
    tokenize='porter unicode61'
);

-- Phase 6: graph entities + relations for NetworkX GraphDB
CREATE TABLE IF NOT EXISTS graph_entities (
    id TEXT PRIMARY KEY,
    entity_type TEXT NOT NULL DEFAULT 'node',
    properties_json TEXT NOT NULL DEFAULT '{}',
    graph_name TEXT NOT NULL DEFAULT 'default',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS graph_relations (
    id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL,
    target_id TEXT NOT NULL,
    relation_type TEXT NOT NULL DEFAULT 'related',
    weight REAL NOT NULL DEFAULT 1.0,
    graph_name TEXT NOT NULL DEFAULT 'default',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Obsidian-absorbed capabilities: links + daily notes
CREATE TABLE IF NOT EXISTS kb_links (
    id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL,
    target_id TEXT NOT NULL,
    link_type TEXT NOT NULL DEFAULT 'wikilink',
    alias TEXT NOT NULL DEFAULT '',
    is_embed INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS daily_notes (
    id TEXT PRIMARY KEY,
    date TEXT NOT NULL,
    content TEXT NOT NULL DEFAULT '',
    tags_json TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
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
    c.executescript(IR_KB_TABLES_EXT)
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
        c.close()
        return
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


# ── FTS5 search ─────────────────────────────────────────


def fts5_search(table: str, query: str, top_k: int = 5) -> list[dict]:
    """Full-text search via FTS5.  Falls back to LIKE if FTS5 table missing.

    Args:
        table: either ``'kb_documents'`` or ``'kb_cards'``.
        query: free-text query string.
        top_k: max results.

    Returns:
        List of dicts with ``id``, ``title``, ``snippet``, ``rank``.
    """
    c = _conn()
    try:
        # Try FTS5 first
        fts_table = f"{table}_fts"
        rows = c.execute(
            f"SELECT rowid, rank FROM {fts_table} WHERE {fts_table} MATCH ? "
            "ORDER BY rank LIMIT ?",
            (query, top_k),
        ).fetchall()
        if rows:
            results = []
            for r in rows:
                # FTS5 rowid = the table's rowid; find the actual row
                base = c.execute(
                    f"SELECT id, title, content FROM {table} WHERE rowid=?",
                    (r["rowid"],),
                ).fetchone()
                if base:
                    snippet = base["content"][:200] if base["content"] else ""
                    results.append({
                        "id": base["id"],
                        "title": base["title"],
                        "snippet": snippet,
                        "rank": r["rank"],
                    })
            return results
    except sqlite3.OperationalError:
        pass  # FTS table missing → fall through to LIKE

    # LIKE fallback
    terms = query.strip().split()
    if not terms:
        return []
    clauses = " OR ".join(["content LIKE ?" for _ in terms])
    params = [f"%{t}%" for t in terms]
    rows = c.execute(
        f"SELECT id, title, content FROM {table} WHERE {clauses} "
        "ORDER BY created_at DESC LIMIT ?",
        (*params, top_k),
    ).fetchall()
    c.close()
    return [
        {"id": r["id"], "title": r["title"], "snippet": r["content"][:200], "rank": 999}
        for r in rows
    ]


def fts5_sync(table: str, data: dict) -> None:
    """Sync a record to its FTS5 index. Call after INSERT/UPDATE on kb_documents or kb_cards."""
    c = _conn()
    try:
        fts_table = f"{table}_fts"
        # Delete old entry if exists (FTS5 uses content-sync via rowid)
        row = c.execute(f"SELECT rowid FROM {table} WHERE id=?", (data["id"],)).fetchone()
        if row:
            c.execute(f"DELETE FROM {fts_table} WHERE rowid=?", (row["rowid"],))
            # Re-insert with current content
            cols = []
            vals = []
            for k in ("id", "title", "content"):
                if k in data:
                    cols.append(k)
                    vals.append(data[k])
            if cols:
                placeholders = ",".join("?" for _ in vals)
                c.execute(
                    f"INSERT INTO {fts_table}({','.join(cols)}) VALUES ({placeholders})",
                    vals,
                )
        c.commit()
    except sqlite3.OperationalError:
        pass  # FTS table not yet created — non-fatal
    finally:
        c.close()


# Auto-init
init()
