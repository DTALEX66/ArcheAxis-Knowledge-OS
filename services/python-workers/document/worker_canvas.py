#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ArcheAxis vNext document worker: JSON Canvas projection (F12).

JSON Canvas (https://jsoncanvas.org) projection that NEVER executes files
or follows links. Text nodes are projected in document order with char
anchors; every edge is preserved verbatim (never flattened away); file/link
nodes surface as references only. Invalid canvases are rejected.

Provenance: behaviour distilled from legacy shared/json_canvas validation
and app/ingestion/multi_format.py `_via_canvas` semantics.

Usage:
    python worker_canvas.py <input.canvas>
Output: {"engine","engine_version","text","structure","edges","references","loss_receipt"}
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ENGINE = "python-worker-canvas"
ENGINE_VERSION = "0.1.0"

ALLOWED_NODE_TYPES = {"text", "file", "link", "group"}


class CanvasError(ValueError):
    pass


def _validate(payload: dict) -> None:
    if not isinstance(payload, dict):
        raise CanvasError("canvas root must be an object")
    if "nodes" not in payload:
        raise CanvasError("canvas requires a nodes array")
    nodes = payload["nodes"]
    if not isinstance(nodes, list):
        raise CanvasError("canvas nodes must be an array")
    seen: set[str] = set()
    for node in nodes:
        if not isinstance(node, dict):
            raise CanvasError("canvas node must be an object")
        node_id = node.get("id")
        if not isinstance(node_id, str) or not node_id:
            raise CanvasError("canvas node requires a non-empty string id")
        if node_id in seen:
            raise CanvasError(f"duplicate canvas node id: {node_id}")
        seen.add(node_id)
        node_type = node.get("type", "text")
        if node_type not in ALLOWED_NODE_TYPES:
            raise CanvasError(f"unsupported canvas node type: {node_type}")
    edges = payload.get("edges", [])
    if not isinstance(edges, list):
        raise CanvasError("canvas edges must be an array")
    for edge in edges:
        if not isinstance(edge, dict):
            raise CanvasError("canvas edge must be an object")
        if edge.get("fromNode") not in seen or edge.get("toNode") not in seen:
            raise CanvasError("canvas edge references an unknown node")


def extract(path: str) -> dict:
    try:
        payload = json.loads(Path(path).read_bytes().decode("utf-8-sig"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise CanvasError(f"invalid JSON Canvas file: {exc}") from exc
    _validate(payload)

    nodes = payload.get("nodes", [])
    edges = payload.get("edges", [])
    text_nodes = [n for n in nodes if n.get("type", "text") == "text"]

    segments = [str(node.get("text", "")) for node in text_nodes]
    projection = "\n".join(segments)

    char_anchors: list[dict] = []
    offset = 0
    for node, segment in zip(text_nodes, segments, strict=True):
        char_anchors.append(
            {
                "kind": "text_node",
                "path": [str(node.get("id", ""))],
                "char_start": offset,
                "char_end": offset + len(segment),
                "node_id": str(node.get("id", "")),
            }
        )
        # Each non-final text node is followed by exactly one separator newline.
        offset += len(segment) + 1

    references = [
        {
            "kind": node.get("type"),
            "id": str(node.get("id", "")),
            "label": node.get("label") or node.get("text") or node.get("url") or "",
            "url": node.get("url") or node.get("file") or "",
        }
        for node in nodes
        if node.get("type") in {"file", "link"}
    ]

    return {
        "engine": ENGINE,
        "engine_version": ENGINE_VERSION,
        "text": projection,
        "structure": char_anchors,
        "edges": edges,
        "references": references,
        "loss_receipt": {
            "engine": ENGINE,
            "engine_version": ENGINE_VERSION,
            "params": {"projection": "text-node order, per-node anchors"},
            "loss_note": (
                "geometry/colors/ports not projected; file/link content never read; "
                "all edges preserved verbatim"
            ),
        },
    }


def main() -> int:
    if len(sys.argv) != 2:
        print(json.dumps({"error": "usage: worker_canvas.py <input.canvas>"}))
        return 2
    try:
        out = extract(sys.argv[1])
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps(out, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
