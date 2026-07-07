"""Mermaid diagram generator — adapted from Obsidian-Assistance v4.

Generates Mermaid.js diagrams from KB data: flowcharts, class diagrams,
knowledge graphs, review timelines.

Adapted from: scripts/v4/generate_mermaid_graph.py
"""

from __future__ import annotations

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_PROJECT_ROOT))


def flowchart(title: str, steps: list[dict[str, str]]) -> str:
    """Generate a Mermaid flowchart from steps.

    Args:
        title: diagram title.
        steps: [{id, label, next_id}, ...].

    Returns:
        Mermaid flowchart markdown string.
    """
    lines = ["```mermaid", "flowchart TD", f"  title[{title}]"]
    for s in steps:
        sid = s.get("id", "?")
        label = s.get("label", sid)
        nxt = s.get("next_id", "")
        lines.append(f"  {sid}[{label}]")
        if nxt:
            lines.append(f"  {sid} --> {nxt}")
    lines.append("```")
    return "\n".join(lines)


def knowledge_graph_mermaid(
    center_id: str = "",
    max_nodes: int = 20,
) -> str:
    """Generate a Mermaid graph from KB links.

    Args:
        center_id: central node to focus on.
        max_nodes: max nodes in the graph.

    Returns:
        Mermaid graph markdown.
    """
    from shared.backlinks import compute_graph

    graph = compute_graph(limit=max_nodes)
    nodes = {n["id"]: n for n in graph["nodes"]}
    edges = graph["edges"]

    lines = ["```mermaid", "graph LR"]

    for nid, node in list(nodes.items())[:max_nodes]:
        title = node.get("title", nid)[:40].replace('"', "'")
        shape = "([{title}])" if node.get("type") == "card" else "[{title}]"
        lines.append(f"  {_safe_id(nid)}{shape.format(title=title)}")

    for edge in edges[: max_nodes * 2]:
        s = _safe_id(edge["source"])
        t = _safe_id(edge["target"])
        label = edge.get("link_type", "")[:10]
        lines.append(f"  {s} -->|{label}| {t}")

    lines.append("```")
    return "\n".join(lines)


def review_timeline_mermaid(card_id: str) -> str:
    """Generate a review timeline diagram for a card.

    Returns Mermaid gantt chart of review history.
    """
    from reviews import get_review_history

    reviews = get_review_history(card_id, limit=20)
    if not reviews:
        return "```mermaid\ngantt\n  title No reviews yet\n```"

    lines = [
        "```mermaid",
        "gantt",
        "  title Review Timeline",
        "  dateFormat YYYY-MM-DD",
        "  axisFormat %m/%d",
    ]

    for r in reviews[:15]:
        date_str = (r.get("created_at", "") or "")[:10]
        q = r.get("quality", 0)
        section = "Good Reviews" if q >= 3 else "Needs Work"
        lines.append(f"  {section} : {date_str}, 1d")

    lines.append("```")
    return "\n".join(lines)


def _safe_id(nid: str) -> str:
    """Make a safe Mermaid node ID."""
    return "n" + "".join(c if c.isalnum() else "_" for c in nid)[:20]
