"""Canvas / whiteboard spatial model — absorbed from Heptabase + Obsidian Canvas.

Supports infinite canvas with draggable cards, connections between them,
and persistent layouts.  Cards can be notes, documents, or any KB object
placed on a 2D plane.

Usage:
    from shared.canvas import create_canvas, add_card, get_canvas
    board = create_canvas("Research Board")
    add_card(board["id"], "doc_001", x=100, y=200)
"""

from __future__ import annotations

import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_PROJECT_ROOT))

from shared.storage import DB_PATH, insert, select_all, select_one  # noqa: E402


def create_canvas(name: str, description: str = "") -> dict[str, Any]:
    """Create a new canvas/whiteboard.

    Args:
        name: canvas title.
        description: optional description.

    Returns:
        The canvas dict.
    """
    now = datetime.now(timezone.utc).isoformat()
    canvas_id = f"canvas_{uuid.uuid4().hex[:12]}"

    canvas = {
        "id": canvas_id,
        "name": name,
        "description": description,
        "created_at": now,
        "updated_at": now,
    }
    insert("canvases", canvas)
    return canvas


def add_card(
    canvas_id: str,
    object_id: str,
    object_type: str = "card",
    x: float = 0,
    y: float = 0,
    width: float = 300,
    height: float = 200,
    color: str = "",
) -> dict[str, Any]:
    """Place a KB object as a card on a canvas.

    Args:
        canvas_id: target canvas.
        object_id: the KB object to place (doc_id, card_id, etc.).
        object_type: 'document' | 'card' | 'machine_knowledge' | 'note'.
        x, y: position on the 2D plane.
        width, height: card dimensions.
        color: accent color.

    Returns:
        The card node dict.
    """
    node_id = f"node_{uuid.uuid4().hex[:12]}"
    node = {
        "id": node_id,
        "canvas_id": canvas_id,
        "object_id": object_id,
        "object_type": object_type,
        "x": x,
        "y": y,
        "width": width,
        "height": height,
        "color": color,
    }
    insert("canvas_nodes", node)

    # Update canvas timestamp
    canvas = select_one("canvases", canvas_id)
    if canvas:
        canvas["updated_at"] = datetime.now(timezone.utc).isoformat()
        insert("canvases", canvas)

    return node


def add_connection(
    canvas_id: str,
    source_node_id: str,
    target_node_id: str,
    label: str = "",
    color: str = "#888",
) -> dict[str, Any]:
    """Draw a connection line between two cards on a canvas.

    Returns:
        The edge dict.
    """
    edge_id = f"edge_{uuid.uuid4().hex[:12]}"
    edge = {
        "id": edge_id,
        "canvas_id": canvas_id,
        "source_node_id": source_node_id,
        "target_node_id": target_node_id,
        "label": label,
        "color": color,
    }
    insert("canvas_edges", edge)
    return edge


def get_canvas(canvas_id: str) -> dict[str, Any] | None:
    """Get a canvas with all its cards and connections."""
    canvas = select_one("canvases", canvas_id)
    if not canvas:
        return None

    all_nodes = select_all("canvas_nodes", limit=500)
    all_edges = select_all("canvas_edges", limit=500)

    nodes = [n for n in all_nodes if n.get("canvas_id") == canvas_id]
    edges = [e for e in all_edges if e.get("canvas_id") == canvas_id]

    # Enrich nodes with object titles
    for node in nodes:
        obj = None
        oid = node.get("object_id", "")
        otype = node.get("object_type", "")
        if otype == "card":
            obj = select_one("kb_cards", oid)
        elif otype == "machine_knowledge":
            obj = select_one("machine_knowledge_units", oid)
        else:
            obj = select_one("kb_documents", oid)
        node["title"] = obj.get("title", oid) if obj else oid

    canvas["nodes"] = nodes
    canvas["edges"] = edges
    canvas["node_count"] = len(nodes)
    canvas["edge_count"] = len(edges)
    return canvas


def list_canvases() -> list[dict[str, Any]]:
    """List all canvases."""
    rows = select_all("canvases", limit=100)
    for r in rows:
        nodes = [n for n in select_all("canvas_nodes", limit=500) if n.get("canvas_id") == r["id"]]
        r["node_count"] = len(nodes)
    return rows


def move_card(node_id: str, x: float, y: float) -> dict | None:
    """Update card position on canvas."""
    node = select_one("canvas_nodes", node_id)
    if not node:
        return None
    node["x"] = x
    node["y"] = y
    insert("canvas_nodes", node)
    return node


def delete_canvas(canvas_id: str) -> bool:
    """Delete a canvas and all its contents."""
    import sqlite3

    conn = sqlite3.connect(str(DB_PATH))
    try:
        conn.execute("DELETE FROM canvases WHERE id=?", (canvas_id,))
        conn.execute("DELETE FROM canvas_nodes WHERE canvas_id=?", (canvas_id,))
        conn.execute("DELETE FROM canvas_edges WHERE canvas_id=?", (canvas_id,))
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()
