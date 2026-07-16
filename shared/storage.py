"""Shared SQLite storage for IR + KB APIs — extends Cognitive-OS database."""

from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import uuid4

from shared.config import config, resolve_runtime_path


def _resolve_database_path() -> Path:
    return resolve_runtime_path(str(config.get("database.path", "data/cognitive_os.sqlite")))


DB_PATH = _resolve_database_path()

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
    context_id TEXT NOT NULL DEFAULT '',
    goal TEXT NOT NULL,
    steps_json TEXT NOT NULL DEFAULT '[]',
    allowed_tools_json TEXT NOT NULL DEFAULT '[]',
    blocked_tools_json TEXT NOT NULL DEFAULT '[]',
    constraints_json TEXT NOT NULL DEFAULT '[]',
    success_criteria_json TEXT NOT NULL DEFAULT '[]',
    risk_level TEXT NOT NULL DEFAULT 'low',
    requires_review INTEGER NOT NULL DEFAULT 1 CHECK(requires_review IN (0, 1)),
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

-- Canvas/whiteboard (Heptabase-absorbed)
CREATE TABLE IF NOT EXISTS canvases (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS canvas_nodes (
    id TEXT PRIMARY KEY,
    canvas_id TEXT NOT NULL,
    object_id TEXT NOT NULL,
    object_type TEXT NOT NULL DEFAULT 'card',
    x REAL NOT NULL DEFAULT 0,
    y REAL NOT NULL DEFAULT 0,
    width REAL NOT NULL DEFAULT 300,
    height REAL NOT NULL DEFAULT 200,
    color TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS canvas_edges (
    id TEXT PRIMARY KEY,
    canvas_id TEXT NOT NULL,
    source_node_id TEXT NOT NULL,
    target_node_id TEXT NOT NULL,
    label TEXT NOT NULL DEFAULT '',
    color TEXT NOT NULL DEFAULT '#888'
);

-- Evidence tracking (adapted from Obsidian-Assistance v6)
CREATE TABLE IF NOT EXISTS kb_evidence (
    id TEXT PRIMARY KEY,
    doc_id TEXT NOT NULL,
    source_type TEXT NOT NULL DEFAULT 'manual',
    source_path TEXT NOT NULL DEFAULT '',
    confidence TEXT NOT NULL DEFAULT 'medium',
    status TEXT NOT NULL DEFAULT 'pending',
    caption TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


def _conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(str(DB_PATH))
    c.execute("PRAGMA journal_mode=WAL")
    c.row_factory = sqlite3.Row
    return c


def init():
    from shared import migration

    if DB_PATH.is_file():
        migration.migrate(db_path=DB_PATH, backup_dir=migration.BACKUP_DIR)

    c = _conn()
    c.executescript(IR_KB_TABLES)
    c.executescript(IR_KB_TABLES_EXT)
    c.commit()
    c.close()

    migration.migrate(db_path=DB_PATH, backup_dir=migration.BACKUP_DIR)


# ── Generic helpers ──

_SQL_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_SQL_ORDER = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)(?:\s+(ASC|DESC))?$", re.IGNORECASE)
PUBLIC_KB_TABLES = frozenset(
    {
        "kb_documents",
        "kb_cards",
        "kb_reviews",
        "kb_mistakes",
        "kb_taskpacks",
        "kb_context_packs",
        "machine_knowledge_units",
    }
)
_FTS_SOURCE_SPECS = {
    "kb_documents": (
        "kb_documents_fts",
        "CREATE VIRTUAL TABLE {candidate} USING fts5("
        "id UNINDEXED, title, content, source, tokenize='porter unicode61')",
    ),
    "kb_cards": (
        "kb_cards_fts",
        "CREATE VIRTUAL TABLE {candidate} USING fts5("
        "id UNINDEXED, title, content, tags, tokenize='porter unicode61')",
    ),
}


@dataclass(frozen=True)
class FtsIndexCandidate:
    """A validated, inactive FTS5 index produced from canonical KB rows."""

    source_table: str
    active_table: str
    table_name: str
    db_path: str
    object_ids: tuple[str, ...]
    count: int

    def verify(self) -> bool:
        """Verify candidate cardinality and IDs without touching the active index."""
        try:
            with sqlite3.connect(self.db_path) as connection:
                actual_ids = tuple(
                    str(row[0])
                    for row in connection.execute(
                        f'SELECT id FROM "{self.table_name}" ORDER BY rowid'
                    ).fetchall()
                )
        except (OSError, sqlite3.Error) as exc:
            raise RuntimeError("FTS candidate verification failed") from exc
        if (
            len(actual_ids) != self.count
            or len(set(actual_ids)) != len(actual_ids)
            or set(actual_ids) != set(self.object_ids)
        ):
            raise RuntimeError("FTS candidate verification failed")
        return True

    def discard(self) -> None:
        """Drop this inactive candidate; the active index is never touched."""
        with sqlite3.connect(self.db_path) as connection:
            connection.execute(f'DROP TABLE IF EXISTS "{self.table_name}"')
            connection.commit()


def validate_public_table(table: str) -> str:
    """Authorize a table for user-facing query/view APIs."""
    if table not in PUBLIC_KB_TABLES:
        raise ValueError(f"table is not available to public query APIs: {table}")
    return table


def _validated_table(connection: sqlite3.Connection, table: str) -> str:
    if not _SQL_IDENTIFIER.fullmatch(table):
        raise ValueError(f"invalid SQL identifier: {table!r}")
    row = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE (type='table' OR type='view') AND name=?",
        (table,),
    ).fetchone()
    if not row:
        raise ValueError(f"unknown storage table: {table}")
    return table


def _validated_order(connection: sqlite3.Connection, table: str, order: str) -> str:
    match = _SQL_ORDER.fullmatch(order.strip())
    if not match:
        raise ValueError(f"invalid SQL order: {order!r}")
    column, direction = match.groups()
    columns = {row[1] for row in connection.execute(f'PRAGMA table_info("{table}")')}
    if column not in columns:
        raise ValueError(f"unknown order column for {table}: {column}")
    return f'"{column}" {direction.upper() if direction else "ASC"}'


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
    try:
        table = _validated_table(c, table)
        cols = {r[1] for r in c.execute(f'PRAGMA table_info("{table}")').fetchall()}
        mapped = {}
        if (
            table == "kb_taskpacks"
            and "task_id" in data
            and "id" in data
            and data["task_id"] != data["id"]
        ):
            raise ValueError("kb_taskpacks task_id and id must match")
        for key, value in data.items():
            if table == "kb_taskpacks" and key == "task_id":
                key = "id"
            column = f"{key}_json" if isinstance(value, (list, dict)) else key
            if column in cols:
                mapped[column] = _json_dump(value) if isinstance(value, (list, dict)) else value
        if not mapped:
            return
        keys = list(mapped)
        placeholders = ",".join("?" for _ in keys)
        quoted_keys = ",".join(f'"{key}"' for key in keys)
        c.execute(
            f'INSERT OR REPLACE INTO "{table}" ({quoted_keys}) VALUES ({placeholders})',
            list(mapped.values()),
        )
        c.commit()
    finally:
        c.close()


def select_all(table: str, limit: int = 100, order: str = "created_at DESC") -> list[dict]:
    c = _conn()
    try:
        table = _validated_table(c, table)
        order = _validated_order(c, table, order)
        rows = c.execute(
            f'SELECT * FROM "{table}" ORDER BY {order} LIMIT ?',
            (limit,),
        ).fetchall()
        return [_row_dict(row) for row in rows]
    finally:
        c.close()


def select_one(table: str, id_val: str) -> dict | None:
    c = _conn()
    try:
        table = _validated_table(c, table)
        row = c.execute(f'SELECT * FROM "{table}" WHERE id=?', (id_val,)).fetchone()
        return _row_dict(row) if row else None
    finally:
        c.close()


def count(table: str) -> int:
    c = _conn()
    try:
        table = _validated_table(c, table)
        return int(c.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0])
    finally:
        c.close()


# ── FTS5 search ─────────────────────────────────────────


def build_fts_candidate(source_table: str) -> FtsIndexCandidate:
    """Build an inactive FTS5 candidate from canonical KB rows.

    The active FTS table is never written, renamed, or dropped.  Candidate
    creation is cleaned up on failure; switching and rollback are separate
    migration operations.
    """
    spec = _FTS_SOURCE_SPECS.get(source_table)
    if spec is None:
        raise ValueError(f"unsupported FTS source table: {source_table}")
    active_table, create_sql = spec
    connection = _conn()
    candidate_table = f"{active_table}__candidate_{uuid4().hex}"
    quoted_candidate = f'"{candidate_table}"'
    try:
        _validated_table(connection, source_table)
        rows = connection.execute(
            f'SELECT id, title, content FROM "{source_table}" ORDER BY rowid'
        ).fetchall()
        connection.execute(create_sql.format(candidate=quoted_candidate))
        for row in rows:
            connection.execute(
                f'INSERT INTO {quoted_candidate}(id, title, content) VALUES (?, ?, ?)',
                (row["id"], row["title"], row["content"]),
            )
        connection.commit()
    except Exception:
        connection.rollback()
        connection.execute(f'DROP TABLE IF EXISTS {quoted_candidate}')
        connection.commit()
        raise
    finally:
        connection.close()
    object_ids = tuple(str(row["id"]) for row in rows)
    candidate = FtsIndexCandidate(
        source_table=source_table,
        active_table=active_table,
        table_name=candidate_table,
        db_path=str(DB_PATH),
        object_ids=object_ids,
        count=len(object_ids),
    )
    try:
        candidate.verify()
    except Exception:
        candidate.discard()
        raise
    return candidate


def fts5_search(table: str, query: str, top_k: int = 5) -> list[dict]:
    """Full-text search via FTS5 with a LIKE fallback."""
    c = _conn()
    try:
        table = _validated_table(c, table)
        fts_table = _validated_table(c, f"{table}_fts")
        try:
            rows = c.execute(
                f'SELECT rowid, rank FROM "{fts_table}" '
                f'WHERE "{fts_table}" MATCH ? ORDER BY rank LIMIT ?',
                (query, top_k),
            ).fetchall()
            if rows:
                results = []
                for row in rows:
                    base = c.execute(
                        f'SELECT id, title, content FROM "{table}" WHERE rowid=?',
                        (row["rowid"],),
                    ).fetchone()
                    if base:
                        results.append(
                            {
                                "id": base["id"],
                                "title": base["title"],
                                "snippet": base["content"][:200] if base["content"] else "",
                                "rank": row["rank"],
                            }
                        )
                return results
        except sqlite3.OperationalError:
            pass

        terms = query.strip().split()
        if not terms:
            return []
        clauses = " OR ".join("content LIKE ?" for _ in terms)
        params = [f"%{term}%" for term in terms]
        rows = c.execute(
            f'SELECT id, title, content FROM "{table}" WHERE {clauses} '
            'ORDER BY created_at DESC LIMIT ?',
            (*params, top_k),
        ).fetchall()
        return [
            {
                "id": row["id"],
                "title": row["title"],
                "snippet": row["content"][:200],
                "rank": 999,
            }
            for row in rows
        ]
    finally:
        c.close()


def fts5_sync(table: str, data: dict) -> None:
    """Sync a record to its FTS5 index. Call after INSERT/UPDATE on kb_documents or kb_cards."""
    c = _conn()
    try:
        table = _validated_table(c, table)
        fts_table = _validated_table(c, f"{table}_fts")
        row = c.execute(f'SELECT rowid FROM "{table}" WHERE id=?', (data["id"],)).fetchone()
        if row:
            c.execute(f'DELETE FROM "{fts_table}" WHERE rowid=?', (row["rowid"],))
            # Re-insert with current content
            cols = []
            vals = []
            for k in ("id", "title", "content"):
                if k in data:
                    cols.append(k)
                    vals.append(data[k])
            if cols:
                placeholders = ",".join("?" for _ in vals)
                quoted_columns = ",".join(f'"{column}"' for column in cols)
                c.execute(
                    f'INSERT INTO "{fts_table}"({quoted_columns}) VALUES ({placeholders})',
                    vals,
                )
        c.commit()
    except sqlite3.OperationalError:
        pass  # FTS table not yet created — non-fatal
    finally:
        c.close()


# Auto-init
init()
