"""Community detection & reasoning — absorbed from Microsoft GraphRAG.

Instead of answering from raw vector search, find communities in the
entity/relation graph (greedy modularity via NetworkX), then summarize each
community from its member nodes so reasoning can operate at the community
level (report §3.9). Local and deterministic; LLM summarisation is optional.

    communities(graph)              → list of communities (sets of node ids)
    community_summary(nodes, props) → short text digest per community
    community_index(graph)          → node → community mapping
"""

from __future__ import annotations

from typing import Any

import networkx as nx


class CommunityError(ValueError):
    """Raised when community reasoning receives invalid input."""


def _to_graph(graph: dict[str, Any]) -> nx.Graph:
    nodes = list(graph.get("nodes", []))
    edges = [tuple(e) for e in graph.get("edges", [])]
    if not nodes:
        raise CommunityError("graph requires at least one node")
    node_set = set(nodes)
    for src, tgt in edges:
        if src not in node_set or tgt not in node_set:
            raise CommunityError(f"edge references unknown node: ({src}, {tgt})")
    g = nx.Graph()
    g.add_nodes_from(nodes)
    g.add_edges_from(edges)
    return g


def communities(graph: dict[str, Any]) -> list[set[str]]:
    """Greedy modularity communities (NetworkX, no external dep)."""
    g = _to_graph(graph)
    if len(g) == 0:
        return []
    return sorted((set(c) for c in nx.algorithms.community.greedy_modularity_communities(g)),
                  key=len, reverse=True)


def community_index(graph: dict[str, Any]) -> dict[str, int]:
    """Map every node id to its community index (0-based, largest first)."""
    groups = communities(graph)
    index: dict[str, int] = {}
    for i, group in enumerate(groups):
        for node in group:
            index[node] = i
    return index


def community_summary(graph: dict[str, Any], group: set[str],
                      props: dict[str, dict[str, Any]] | None = None) -> str:
    """A short local digest of one community (titles + types, no LLM)."""
    props = props or {}
    if not group:
        raise CommunityError("community must be non-empty")
    members: list[str] = []
    for node in sorted(group):
        node_props = props.get(node, {})
        label = node_props.get("title") or node
        etype = node_props.get("type", "concept")
        members.append(f"{label}[{etype}]")
    return f"community({len(members)}): " + ", ".join(members[:12])
