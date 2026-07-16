"""SQLite database layer for Cognitive-OS — replaces JSONL flat files."""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from shared.config import config, resolve_runtime_path
from shared.research_boundary import unreviewed_research_references

DB_PATH = resolve_runtime_path(str(config.get("database.path", "data/cognitive_os.sqlite")))
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

SCHEMA = """
CREATE TABLE IF NOT EXISTS core_objects (
    id TEXT PRIMARY KEY,
    object_type TEXT NOT NULL DEFAULT 'document',
    content TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'unknown',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    attention_score REAL NOT NULL DEFAULT 0.0,
    route TEXT
);

CREATE TABLE IF NOT EXISTS routes (
    id TEXT PRIMARY KEY,
    object_id TEXT NOT NULL REFERENCES core_objects(id),
    route TEXT NOT NULL CHECK(route IN ('KB','IR','TASK','DROP','REVIEW')),
    score REAL NOT NULL,
    reasons_json TEXT NOT NULL DEFAULT '[]',
    risk_level TEXT NOT NULL DEFAULT 'low' CHECK(risk_level IN ('low','medium','high')),
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS memory_records (
    id TEXT PRIMARY KEY,
    object_id TEXT NOT NULL REFERENCES core_objects(id),
    content TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'unknown',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS taskpacks (
    id TEXT PRIMARY KEY,
    goal TEXT NOT NULL,
    steps_json TEXT NOT NULL DEFAULT '[]',
    constraints_json TEXT NOT NULL DEFAULT '[]',
    tools_json TEXT NOT NULL DEFAULT '[]',
    risk_level TEXT NOT NULL DEFAULT 'low',
    success_criteria_json TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS execution_traces (
    id TEXT PRIMARY KEY,
    task_id TEXT,
    events_json TEXT NOT NULL DEFAULT '[]',
    result_json TEXT NOT NULL DEFAULT '{}',
    success INTEGER,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS eval_results (
    id TEXT PRIMARY KEY,
    trace_id TEXT NOT NULL REFERENCES execution_traces(id),
    success INTEGER NOT NULL,
    score REAL NOT NULL,
    failure_reason TEXT NOT NULL DEFAULT '',
    improvement TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS machine_lessons (
    id TEXT PRIMARY KEY,
    pattern TEXT NOT NULL,
    lesson_type TEXT NOT NULL CHECK(lesson_type IN ('success','failure','anti_pattern','constraint')),
    future_constraint TEXT NOT NULL DEFAULT '',
    evidence_trace_id TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tool_calls (
    id TEXT PRIMARY KEY,
    trace_id TEXT NOT NULL REFERENCES execution_traces(id),
    tool_name TEXT NOT NULL,
    params_json TEXT NOT NULL DEFAULT '{}',
    result_json TEXT NOT NULL DEFAULT '{}',
    risk_level TEXT NOT NULL DEFAULT 'low',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS permission_decisions (
    id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    risk_level TEXT NOT NULL,
    allowed_tools_json TEXT NOT NULL DEFAULT '[]',
    blocked_tools_json TEXT NOT NULL DEFAULT '[]',
    requires_human_review INTEGER NOT NULL DEFAULT 0,
    reason TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_core_objects_route ON core_objects(route);
CREATE INDEX IF NOT EXISTS idx_core_objects_created ON core_objects(created_at);
CREATE INDEX IF NOT EXISTS idx_routes_object ON routes(object_id);
CREATE INDEX IF NOT EXISTS idx_memory_object ON memory_records(object_id);
CREATE INDEX IF NOT EXISTS idx_traces_task ON execution_traces(task_id);
CREATE INDEX IF NOT EXISTS idx_eval_trace ON eval_results(trace_id);
CREATE INDEX IF NOT EXISTS idx_lessons_type ON machine_lessons(lesson_type);
CREATE INDEX IF NOT EXISTS idx_tool_calls_trace ON tool_calls(trace_id);
CREATE INDEX IF NOT EXISTS idx_permission_task ON permission_decisions(task_id);
"""


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create tables and indexes if they don't exist."""
    conn = _get_conn()
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()


# ── CoreObject ──────────────────────────────────────────


def _reject_unreviewed_object_source(obj: dict[str, Any]) -> None:
    if unreviewed_research_references([obj.get("source", "")]):
        raise ValueError(
            "candidate or external core-memory sources require server-owned Phase 5 review provenance"
        )


def save_core_object(obj: dict[str, Any]) -> None:
    _reject_unreviewed_object_source(obj)
    conn = _get_conn()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO core_objects VALUES (?,?,?,?,?,?,?,?)",
            (
                obj["id"],
                obj.get("object_type", "document"),
                obj["content"],
                obj.get("source", "unknown"),
                json.dumps(obj.get("metadata", {})),
                obj["created_at"],
                obj.get("attention_score", 0.0),
                obj.get("route"),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def list_core_objects(route: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
    conn = _get_conn()
    try:
        if route:
            rows = conn.execute(
                "SELECT * FROM core_objects WHERE route=? ORDER BY created_at DESC LIMIT ?",
                (route, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM core_objects ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [_row_to_dict(r) for r in rows]
    finally:
        conn.close()


def search_core_objects(query: str, top_k: int = 5) -> list[dict[str, Any]]:
    """Simple LIKE-based search; replace with FTS5 later."""
    conn = _get_conn()
    try:
        terms = query.strip().split()
        if not terms:
            return []
        clauses = " OR ".join(["content LIKE ?" for _ in terms])
        params = [f"%{t}%" for t in terms]
        rows = conn.execute(
            f"SELECT * FROM core_objects WHERE {clauses} ORDER BY created_at DESC LIMIT ?",
            (*params, top_k),
        ).fetchall()
        return [_row_to_dict(r) for r in rows]
    finally:
        conn.close()


# ── Route ───────────────────────────────────────────────


def save_route(route_data: dict[str, Any]) -> None:
    conn = _get_conn()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO routes VALUES (?,?,?,?,?,?,?)",
            (
                route_data.get("id", f"route_{route_data['object_id']}"),
                route_data["object_id"],
                route_data["route"],
                route_data["score"],
                json.dumps(route_data.get("reasons", [])),
                route_data.get("risk_level", "low"),
                route_data.get("created_at", ""),
            ),
        )
        conn.commit()
    finally:
        conn.close()


# ── Memory ──────────────────────────────────────────────


def save_memory_record(obj: dict[str, Any]) -> None:
    _reject_unreviewed_object_source(obj)
    conn = _get_conn()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO memory_records VALUES (?,?,?,?,?,?)",
            (
                obj["id"],
                obj["id"],
                obj["content"],
                obj.get("source", "unknown"),
                json.dumps(obj.get("metadata", {})),
                obj["created_at"],
            ),
        )
        conn.commit()
    finally:
        conn.close()


def list_memory_records(limit: int = 100) -> list[dict[str, Any]]:
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM memory_records ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [_row_to_dict(r) for r in rows]
    finally:
        conn.close()


# ── TaskPack ────────────────────────────────────────────


def save_taskpack(task: dict[str, Any]) -> None:
    conn = _get_conn()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO taskpacks VALUES (?,?,?,?,?,?,?,?)",
            (
                task["id"],
                task["goal"],
                json.dumps(task.get("steps", [])),
                json.dumps(task.get("constraints", [])),
                json.dumps(task.get("tools", [])),
                task.get("risk_level", "low"),
                json.dumps(task.get("success_criteria", [])),
                task.get("created_at", ""),
            ),
        )
        conn.commit()
    finally:
        conn.close()


# ── ExecutionTrace ─────────────────────────────────────


def save_trace(trace: dict[str, Any]) -> None:
    conn = _get_conn()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO execution_traces VALUES (?,?,?,?,?,?)",
            (
                trace["id"],
                trace.get("task_id"),
                json.dumps(trace.get("events", [])),
                json.dumps(trace.get("result", {})),
                1 if trace.get("success") else (0 if trace.get("success") is False else None),
                trace["created_at"],
            ),
        )
        conn.commit()
    finally:
        conn.close()


def list_traces_db(limit: int = 100) -> list[dict[str, Any]]:
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM execution_traces ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [_row_to_dict(r) for r in rows]
    finally:
        conn.close()


# ── EvalResult ─────────────────────────────────────────


def save_eval(eval_data: dict[str, Any]) -> None:
    conn = _get_conn()
    try:
        eval_id = eval_data.get("id", f"eval_{eval_data.get('trace_id', 'unknown')}")
        conn.execute(
            "INSERT OR REPLACE INTO eval_results VALUES (?,?,?,?,?,?,?)",
            (
                eval_id,
                eval_data.get("trace_id", ""),
                1 if eval_data.get("success") else 0,
                eval_data.get("score", 0.0),
                eval_data.get("failure_reason", ""),
                eval_data.get("improvement", ""),
                eval_data.get("created_at", ""),
            ),
        )
        conn.commit()
    finally:
        conn.close()


# ── MachineLesson ──────────────────────────────────────


def save_lesson_db(lesson: dict[str, Any]) -> None:
    conn = _get_conn()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO machine_lessons VALUES (?,?,?,?,?,?)",
            (
                lesson["id"],
                lesson["pattern"],
                lesson["lesson_type"],
                lesson.get("future_constraint", ""),
                lesson.get("evidence_trace_id"),
                lesson["created_at"],
            ),
        )
        conn.commit()
    finally:
        conn.close()


def list_lessons_db(limit: int = 100) -> list[dict[str, Any]]:
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM machine_lessons ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [_row_to_dict(r) for r in rows]
    finally:
        conn.close()


# ── ToolCall ───────────────────────────────────────────


def save_tool_call(call_data: dict[str, Any]) -> None:
    conn = _get_conn()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO tool_calls VALUES (?,?,?,?,?,?,?)",
            (
                call_data["id"],
                call_data["trace_id"],
                call_data["tool_name"],
                json.dumps(call_data.get("params", {})),
                json.dumps(call_data.get("result", {})),
                call_data.get("risk_level", "low"),
                call_data.get("created_at", ""),
            ),
        )
        conn.commit()
    finally:
        conn.close()


# ── PermissionDecision ─────────────────────────────────


def save_permission(perm: dict[str, Any]) -> None:
    conn = _get_conn()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO permission_decisions VALUES (?,?,?,?,?,?,?,?)",
            (
                perm["id"],
                perm["task_id"],
                perm["risk_level"],
                json.dumps(perm.get("allowed_tools", [])),
                json.dumps(perm.get("blocked_tools", [])),
                1 if perm.get("requires_human_review") else 0,
                perm.get("reason", ""),
                perm.get("created_at", ""),
            ),
        )
        conn.commit()
    finally:
        conn.close()


# ── Helpers ────────────────────────────────────────────


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    d = dict(row)
    # Convert JSON fields back to Python objects
    for key in list(d.keys()):
        if key.endswith("_json"):
            try:
                d[key[:-5]] = json.loads(d[key]) if d[key] else {}
            except (json.JSONDecodeError, TypeError):
                d[key[:-5]] = d[key]
            del d[key]
    # Convert only valid SQLite integer booleans; preserve corrupt values so
    # contract adapters can reject them instead of silently upgrading truth.
    for bool_key in ("success", "requires_human_review"):
        if bool_key in d and type(d[bool_key]) is int and d[bool_key] in (0, 1):
            d[bool_key] = bool(d[bool_key])
    return d


# Auto-initialize on import
init_db()
