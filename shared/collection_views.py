"""Collection views — absorbed from Notion databases + Anytype Sets.

Enables multiple view formats over the same data:
- Table view (default)
- Board/Kanban view (grouped by a field)
- Calendar view (by date field)
- Gallery view (card grid)
- List view (compact)

Usage:
    from shared.collection_views import render_view
    view = render_view("kb_cards", view_type="board", group_by="review_status")
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_PROJECT_ROOT))

from shared.storage import select_all  # noqa: E402


def _group_items(items: list[dict], field: str) -> dict[str, list[dict]]:
    """Group items by a field value."""
    groups: dict[str, list[dict]] = {}
    for item in items:
        val = str(item.get(field, "ungrouped"))
        if val not in groups:
            groups[val] = []
        groups[val].append(item)
    return groups


def _render_table(items: list[dict], columns: list[str]) -> dict[str, Any]:
    """Render as a table (Notion table view)."""
    return {
        "view_type": "table",
        "columns": columns,
        "rows": [{col: row.get(col, "") for col in columns} for row in items],
    }


def _render_board(items: list[dict], group_by: str, card_field: str = "title") -> dict[str, Any]:
    """Render as a Kanban board (Notion board view)."""
    groups = _group_items(items, group_by)
    columns_list = []
    for group_name, group_items in sorted(groups.items()):
        columns_list.append(
            {
                "column": group_name,
                "count": len(group_items),
                "cards": [
                    {"id": item.get("id", ""), "title": item.get(card_field, "")[:80]}
                    for item in group_items[:20]
                ],
            }
        )
    return {
        "view_type": "board",
        "group_by": group_by,
        "columns": columns_list,
    }


def _render_calendar(items: list[dict], date_field: str) -> dict[str, Any]:
    """Render as a calendar (Notion calendar view)."""
    by_date: dict[str, list[dict]] = {}
    for item in items:
        date_val = str(item.get(date_field, ""))[:10]  # YYYY-MM-DD
        if date_val:
            if date_val not in by_date:
                by_date[date_val] = []
            by_date[date_val].append(
                {
                    "id": item.get("id", ""),
                    "title": (item.get("title") or item.get("pattern") or "")[:80],
                }
            )

    return {
        "view_type": "calendar",
        "date_field": date_field,
        "dates": [
            {"date": d, "count": len(items), "items": items[:10]}
            for d, items in sorted(by_date.items())
        ],
    }


def _render_gallery(items: list[dict], card_field: str = "title") -> dict[str, Any]:
    """Render as a card gallery (Notion gallery / Capacities card view)."""
    return {
        "view_type": "gallery",
        "cards": [
            {
                "id": item.get("id", ""),
                "title": item.get(card_field, "")[:80],
                "type": item.get("unit_type") or item.get("review_status", ""),
                "preview": (item.get("content") or "")[:200],
            }
            for item in items[:50]
        ],
    }


def _render_list(items: list[dict], compact: bool = True) -> dict[str, Any]:
    """Render as a compact list (Logseq outliner style)."""
    return {
        "view_type": "list",
        "items": [
            {
                "id": item.get("id", ""),
                "text": (item.get("title") or item.get("pattern") or item.get("id", ""))[:120],
                "meta": (item.get("review_status") or item.get("unit_type") or ""),
            }
            for item in items
        ],
    }


def render_view(
    table: str,
    view_type: str = "table",
    group_by: str = "",
    date_field: str = "created_at",
    card_field: str = "title",
    columns: list[str] | None = None,
    limit: int = 100,
    where_field: str = "",
    where_value: str = "",
) -> dict[str, Any]:
    """Render items from a KB table using the specified view format.

    Args:
        table: SQLite table name (kb_cards, kb_documents, etc.).
        view_type: 'table' | 'board' | 'calendar' | 'gallery' | 'list'.
        group_by: field to group by (for board view).
        date_field: date field (for calendar view).
        card_field: title field to show on cards.
        columns: list of columns (for table view).
        limit: max items to render.
        where_field: optional filter field.
        where_value: optional filter value.

    Returns:
        Rendered view dict with type, count, and data.
    """
    items = select_all(table, limit=500)
    if where_field and where_value:
        items = [i for i in items if str(i.get(where_field, "")) == where_value]
    items = items[:limit]

    if columns is None:
        if items:
            columns = [k for k in items[0] if not k.endswith("_json")][:8]
        else:
            columns = ["id", "title"]

    if view_type == "board":
        data = _render_board(items, group_by or "review_status", card_field)
    elif view_type == "calendar":
        data = _render_calendar(items, date_field)
    elif view_type == "gallery":
        data = _render_gallery(items, card_field)
    elif view_type == "list":
        data = _render_list(items)
    else:
        data = _render_table(items, columns)

    data["table"] = table
    data["count"] = len(items)
    return data


def aggregate(
    table: str,
    group_by: str,
    aggregate_field: str = "",
    aggregate_func: str = "count",
) -> dict[str, Any]:
    """Aggregate data like Notion rollups.

    Args:
        table: SQLite table.
        group_by: field to group by.
        aggregate_field: field to aggregate on.
        aggregate_func: 'count' | 'sum' | 'avg' | 'min' | 'max'.

    Returns:
        Grouped aggregation results.
    """
    items = select_all(table, limit=500)
    groups = _group_items(items, group_by)

    result = {}
    for group_name, group_items in sorted(groups.items()):
        if aggregate_func == "count":
            val = len(group_items)
        elif aggregate_func == "sum" and aggregate_field:
            val = sum(float(i.get(aggregate_field, 0) or 0) for i in group_items)
        elif aggregate_func == "avg" and aggregate_field:
            vals = [float(i.get(aggregate_field, 0) or 0) for i in group_items]
            val = sum(vals) / len(vals) if vals else 0
        elif aggregate_func == "min" and aggregate_field:
            val = min((float(i.get(aggregate_field, 0) or 0) for i in group_items), default=0)
        elif aggregate_func == "max" and aggregate_field:
            val = max((float(i.get(aggregate_field, 0) or 0) for i in group_items), default=0)
        else:
            val = len(group_items)
        result[group_name] = {"count": len(group_items), "value": val}

    return {
        "table": table,
        "group_by": group_by,
        "aggregate_func": aggregate_func,
        "groups": result,
    }
