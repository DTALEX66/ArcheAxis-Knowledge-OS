"""JSON Canvas format validator (ADS-003).

Adopts the JSON Canvas spec (MIT, obsidianmd/jsoncanvas v1.0)
as the project's canonical canvas format. No library dependency.

Unknown fields are preserved on read; non-standard fields are never emitted.
"""

from __future__ import annotations

import uuid
from typing import Any

__all__ = ["validate_json_canvas", "CanvasError", "make_node_id", "make_edge_id"]


class CanvasError(ValueError):
    """Structured JSON Canvas validation error."""


_VALID_TYPES = frozenset({"text", "file", "link", "group"})
_VALID_SIDES = frozenset({"top", "right", "bottom", "left"})
_VALID_ENDS = frozenset({"none", "arrow"})
_COLOR_PRESETS = frozenset({"1", "2", "3", "4", "5", "6"})
_BACKGROUND_STYLES = frozenset({"cover", "ratio", "repeat"})


def validate_json_canvas(data: dict[str, Any]) -> dict[str, Any]:
    """Validate a JSON Canvas document. Returns normalized dict or raises CanvasError.

    Unknown fields are preserved so callers can roundtrip safely.
    """
    if not isinstance(data, dict):
        raise CanvasError(f"top-level must be object, got {type(data).__name__}")

    nodes = data.get("nodes")
    edges = data.get("edges")

    if nodes is not None:
        if not isinstance(nodes, list):
            raise CanvasError(f"'nodes' must be array, got {type(nodes).__name__}")
        seen_ids: set[str] = set()
        for i, n in enumerate(nodes):
            _validate_node(n, i, seen_ids)

    if edges is not None:
        if not isinstance(edges, list):
            raise CanvasError(f"'edges' must be array, got {type(edges).__name__}")
        seen_edge_ids: set[str] = set()
        for i, e in enumerate(edges):
            _validate_edge(e, i, seen_edge_ids)

    return data


def _validate_node(n: Any, idx: int, seen: set[str]) -> None:
    if not isinstance(n, dict):
        raise CanvasError(f"nodes[{idx}] must be object, got {type(n).__name__}")
    nid = n.get("id")
    if not isinstance(nid, str) or not nid:
        raise CanvasError(f"nodes[{idx}] missing or empty 'id'")
    if nid in seen:
        raise CanvasError(f"nodes[{idx}] duplicate id '{nid}'")
    seen.add(nid)

    ntype = n.get("type")
    if ntype not in _VALID_TYPES:
        raise CanvasError(f"nodes[{idx}] invalid type '{ntype}'")

    for axis in ("x", "y", "width", "height"):
        v = n.get(axis)
        if not isinstance(v, int):
            raise CanvasError(f"nodes[{idx}] '{axis}' must be integer, got {type(v).__name__}")

    if n.get("width", 0) < 1 or n.get("height", 0) < 1:
        raise CanvasError(f"nodes[{idx}] width and height must be >= 1")

    color = n.get("color")
    if color is not None and not _is_valid_color(color):
        raise CanvasError(f"nodes[{idx}] invalid color '{color}'")

    if ntype == "file" and not isinstance(n.get("file"), str):
        raise CanvasError(f"nodes[{idx}] type=file requires 'file' string")
    if ntype == "link" and not isinstance(n.get("url"), str):
        raise CanvasError(f"nodes[{idx}] type=link requires 'url' string")

    bg = n.get("backgroundStyle")
    if bg is not None and bg not in _BACKGROUND_STYLES:
        raise CanvasError(f"nodes[{idx}] invalid backgroundStyle '{bg}'")


def _validate_edge(e: Any, idx: int, seen: set[str]) -> None:
    if not isinstance(e, dict):
        raise CanvasError(f"edges[{idx}] must be object, got {type(e).__name__}")
    eid = e.get("id")
    if not isinstance(eid, str) or not eid:
        raise CanvasError(f"edges[{idx}] missing or empty 'id'")
    if eid in seen:
        raise CanvasError(f"edges[{idx}] duplicate id '{eid}'")
    seen.add(eid)

    for field in ("fromNode", "toNode"):
        if not isinstance(e.get(field), str):
            raise CanvasError(f"edges[{idx}] missing '{field}'")

    for field in ("fromSide", "toSide"):
        if e.get(field) not in _VALID_SIDES:
            raise CanvasError(f"edges[{idx}] invalid '{field}'")

    for field in ("fromEnd", "toEnd"):
        if e.get(field) not in _VALID_ENDS:
            raise CanvasError(f"edges[{idx}] invalid '{field}'")


def _is_valid_color(c: str) -> bool:
    if c in _COLOR_PRESETS:
        return True
    if c.startswith("#") and len(c) == 7:
        try:
            int(c[1:], 16)
            return True
        except ValueError:
            pass
    return False


def make_node_id() -> str:
    """Generate an opaque node id."""
    return f"n_{uuid.uuid4().hex[:12]}"


def make_edge_id() -> str:
    """Generate an opaque edge id."""
    return f"e_{uuid.uuid4().hex[:12]}"
