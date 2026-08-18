"""Tests for community reasoning (GraphRAG absorption)."""
from __future__ import annotations

import pytest

from app.graph.community import (
    CommunityError,
    communities,
    community_index,
    community_summary,
)


GRAPH = {
    "nodes": ["a", "b", "c", "d", "e", "f"],
    "edges": [
        ("a", "b"), ("b", "c"), ("a", "c"),   # dense cluster 1
        ("d", "e"), ("e", "f"), ("d", "f"),   # dense cluster 2
        ("c", "d"),                            # weak bridge
    ],
}


def test_communities_found():
    groups = communities(GRAPH)
    assert len(groups) >= 2
    assert all(isinstance(g, set) for g in groups)


def test_community_index_covers_all_nodes():
    index = community_index(GRAPH)
    assert set(index) == set(GRAPH["nodes"])
    assert len(set(index.values())) >= 2


def test_community_summary_local():
    groups = communities(GRAPH)
    summary = community_summary(GRAPH, groups[0], props={
        "a": {"title": "Photoshop", "type": "software"},
    })
    assert "Photoshop" in summary
    assert "community" in summary


def test_empty_graph_rejected():
    with pytest.raises(CommunityError):
        communities({"nodes": [], "edges": []})
    with pytest.raises(CommunityError):
        communities({"nodes": ["x"], "edges": [("x", "missing")]})
