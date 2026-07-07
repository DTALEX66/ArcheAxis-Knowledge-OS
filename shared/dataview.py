"""Dataview-style query engine — lightweight DSL for filtering KB assets.

Absorbs Obsidian Dataview's core capability: query your knowledge like a database.
Simple query syntax:
    FROM <table> WHERE <field>=<value> [AND ...] SORT <field> [ASC|DESC] [LIMIT N]

Also supports:
    LIST <field> FROM ...
    TABLE <field1>, <field2> FROM ...

Usage:
    from shared.dataview import query
    results = query("FROM kb_cards WHERE review_status='draft' SORT created_at DESC LIMIT 10")
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_PROJECT_ROOT))

from shared.storage import select_all  # noqa: E402

# ── Query parser ────────────────────────────────────────

_QUERY_RE = re.compile(
    r"^\s*(?:LIST\s+(?P<list_field>\w+)\s+)?"
    r"FROM\s+(?P<table>\w+)"
    r"(?:\s+WHERE\s+(?P<where>.+?))?"
    r"(?:\s+SORT\s+(?P<sort>\w+)(?:\s+(?P<order>ASC|DESC))?)?"
    r"(?:\s+LIMIT\s+(?P<limit>\d+))?"
    r"\s*$",
    re.IGNORECASE,
)


def _parse_condition(cond: str) -> dict[str, Any]:
    """Parse a single WHERE condition like 'field=value' or 'field!=value'."""
    cond = cond.strip()
    for op in ("!=", ">=", "<=", "=", ">", "<", "~", "!~"):
        if op in cond:
            key, _, val = cond.partition(op)
            return {"field": key.strip(), "op": op, "value": val.strip().strip("'\"")}
    return {"field": cond, "op": "exists", "value": ""}


def _parse_where(where_clause: str) -> list[dict[str, Any]]:
    """Parse WHERE clause into list of conditions."""
    if not where_clause or not where_clause.strip():
        return []
    # Split on AND (case-insensitive)
    parts = re.split(r"\s+AND\s+", where_clause, flags=re.IGNORECASE)
    return [_parse_condition(p) for p in parts]


def _match_record(record: dict[str, Any], conditions: list[dict[str, Any]]) -> bool:
    """Check if a record satisfies all conditions."""
    for cond in conditions:
        field = cond["field"]
        op = cond["op"]
        val = cond["value"]
        rec_val = record.get(field)
        if isinstance(rec_val, list):
            rec_val = ",".join(str(v) for v in rec_val)

        if op == "exists":
            if not rec_val:
                return False
        elif op == "=":
            if str(rec_val).lower() != val.lower():
                return False
        elif op == "!=":
            if str(rec_val).lower() == val.lower():
                return False
        elif op == "~":
            if val.lower() not in str(rec_val).lower():
                return False
        elif op == "!~":
            if val.lower() in str(rec_val).lower():
                return False
        elif op in (">", ">=", "<", "<="):
            try:
                rv = float(rec_val) if rec_val else 0
                cv = float(val)
                if op == ">" and not (rv > cv):
                    return False
                if op == ">=" and not (rv >= cv):
                    return False
                if op == "<" and not (rv < cv):
                    return False
                if op == "<=" and not (rv <= cv):
                    return False
            except (ValueError, TypeError):
                return False

    return True


# ── Public API ──────────────────────────────────────────


def query(query_str: str) -> dict[str, Any]:
    """Execute a Dataview-style query against the KB.

    Examples:
        FROM kb_cards WHERE review_status='draft' SORT created_at DESC LIMIT 10
        LIST title FROM kb_documents WHERE source='obsidian'
        FROM kb_reviews WHERE quality>=4 SORT created_at DESC
        FROM kb_cards WHERE tags~='test' AND review_status='mastered' LIMIT 5

    Returns:
        {query, count, items, parsed}
    """
    match = _QUERY_RE.match(query_str)
    if not match:
        return {"error": "invalid query syntax", "query": query_str}

    table = match.group("table")
    where_clause = match.group("where")
    sort_field = match.group("sort")
    sort_order = (match.group("order") or "ASC").upper()
    limit_val = int(match.group("limit")) if match.group("limit") else 100
    list_field = match.group("list_field")

    conditions = _parse_where(where_clause)

    # Fetch from DB
    rows = select_all(table, limit=500, order="created_at DESC")

    # Filter
    matched = [r for r in rows if _match_record(r, conditions)]

    # Sort
    if sort_field:
        reverse = sort_order == "DESC"
        matched.sort(
            key=lambda r: str(r.get(sort_field, "")),
            reverse=reverse,
        )

    # Limit
    matched = matched[:limit_val]

    # LIST mode: project specific field
    if list_field:
        matched = [{list_field: r.get(list_field)} for r in matched]

    return {
        "query": query_str,
        "table": table,
        "count": len(matched),
        "items": matched,
        "parsed": {
            "table": table,
            "conditions": conditions,
            "sort": sort_field,
            "order": sort_order,
            "limit": limit_val,
            "list_field": list_field,
        },
    }


def query_graph(center_id: str = "", depth: int = 2) -> dict[str, Any]:
    """Source: obsidian-graph — return graph data around a center node.

    If center_id is empty, returns full link graph.
    """
    from shared.backlinks import compute_graph

    graph = compute_graph(limit=300)

    if not center_id:
        return graph

    # BFS from center_id
    neighbors: set[str] = {center_id}
    for _ in range(depth):
        frontier = set()
        for edge in graph["edges"]:
            if edge["source"] in neighbors:
                frontier.add(edge["target"])
            if edge["target"] in neighbors:
                frontier.add(edge["source"])
        neighbors.update(frontier)

    filtered_nodes = [n for n in graph["nodes"] if n["id"] in neighbors]
    filtered_edges = [
        e for e in graph["edges"] if e["source"] in neighbors and e["target"] in neighbors
    ]

    return {
        "center": center_id,
        "depth": depth,
        "nodes": filtered_nodes,
        "edges": filtered_edges,
    }
