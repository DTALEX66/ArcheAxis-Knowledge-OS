"""SQLite declarative schema migration for Cognitive-Loop-OS.

Provides a lightweight migration system: versioned SQL scripts stored in
``data/migrations/``, executed in order.  Tracks applied migrations in
a ``schema_migrations`` table.

Usage:
    from shared.migration import migrate
    migrate()  # applies all pending migrations
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS_DIR = _PROJECT_ROOT / "data" / "migrations"
DB_PATH = _PROJECT_ROOT / "data" / "cognitive_os.sqlite"

MIGRATIONS_TABLE = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    applied_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_migrations_table() -> None:
    conn = _get_conn()
    try:
        conn.executescript(MIGRATIONS_TABLE)
        conn.commit()
    finally:
        conn.close()


def _applied_versions() -> set[int]:
    conn = _get_conn()
    try:
        rows = conn.execute("SELECT version FROM schema_migrations").fetchall()
        return {r["version"] for r in rows}
    finally:
        conn.close()


def _discover_migrations() -> list[tuple[int, str, str]]:
    """Discover migration files: 001_name.sql → (version, name, sql)."""
    if not MIGRATIONS_DIR.exists():
        return []

    migrations = []
    for f in sorted(MIGRATIONS_DIR.glob("*.sql")):
        # Parse "001_name.sql" format
        parts = f.stem.split("_", 1)
        if len(parts) == 2 and parts[0].isdigit():
            version = int(parts[0])
            name = parts[1]
            sql = f.read_text(encoding="utf-8")
            migrations.append((version, name, sql))
    return migrations


def migrate() -> list[str]:
    """Apply all pending migrations in order.

    Returns:
        List of migration names that were applied.
    """
    _ensure_migrations_table()
    applied = _applied_versions()
    pending = _discover_migrations()

    applied_names = []
    conn = _get_conn()
    try:
        for version, name, sql in pending:
            if version in applied:
                continue
            conn.executescript(sql)
            conn.execute(
                "INSERT INTO schema_migrations(version, name) VALUES (?, ?)",
                (version, name),
            )
            conn.commit()
            applied_names.append(name)
    finally:
        conn.close()

    return applied_names


def status() -> dict:
    """Return current migration status."""
    _ensure_migrations_table()
    all_migrations = _discover_migrations()
    applied = _applied_versions()

    return {
        "total": len(all_migrations),
        "applied": len(applied),
        "pending": [f"{v:03d}_{n}" for v, n, _ in all_migrations if v not in applied],
        "applied_list": [f"{v:03d}_{n}" for v, n, _ in all_migrations if v in applied],
    }


# ── Seed initial migration ──────────────────────────────


def _seed_initial_migration() -> None:
    """Create the initial migration file for the current schema."""
    MIGRATIONS_DIR.mkdir(parents=True, exist_ok=True)

    initial_path = MIGRATIONS_DIR / "001_initial_schema.sql"
    if not initial_path.exists():
        initial_path.write_text(
            """-- Initial schema (P0-P2 as of 2026-07)
-- Auto-generated from shared/storage.py IR_KB_TABLES + IR_KB_TABLES_EXT

-- IR tables
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

-- KB tables
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

-- FTS5 indexes
CREATE VIRTUAL TABLE IF NOT EXISTS kb_documents_fts USING fts5(
    id UNINDEXED, title, content, source,
    tokenize='porter unicode61'
);

CREATE VIRTUAL TABLE IF NOT EXISTS kb_cards_fts USING fts5(
    id UNINDEXED, title, content, tags,
    tokenize='porter unicode61'
);

-- Review & Mistakes (P2-1)
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
""",
            encoding="utf-8",
        )


_seed_initial_migration()
