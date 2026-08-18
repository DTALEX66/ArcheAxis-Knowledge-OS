"""Tests for the prerequisite-aware path recommender (D3 R3)."""
from __future__ import annotations

import pytest

from app.knowledge.path_recommender import (
    DEFAULT_MASTERY_THRESHOLD,
    RecommenderError,
    recommend_next,
)

GRAPH = {
    "nodes": ["a", "b", "c", "d"],
    "edges": [("a", "b"), ("b", "c"), ("c", "d")],  # a→b→c→d
}


def test_recommends_lowest_mastery_ready_node():
    recs = recommend_next(graph=GRAPH, mastery_map={"a": 0.9, "b": 0.3, "c": 0.4})
    # b (shortfall 0.7) beats c (shortfall 0.6); d deferred (c unmet)
    assert recs[0].node == "b"
    assert recs[0].score > 0.5
    nodes = [r.node for r in recommend_next(graph=GRAPH, mastery_map={"a": 0.9, "b": 0.3, "c": 0.4}, top_k=5)]
    assert "d" not in nodes


def test_defers_unmet_prerequisites():
    recs = recommend_next(graph=GRAPH, mastery_map={"a": 0.2, "b": 0.9, "c": 0.1})
    # c requires b (mastered) and is low → c recommended; d requires c → deferred
    nodes = [r.node for r in recommend_next(graph=GRAPH, mastery_map={"a": 0.2, "b": 0.9, "c": 0.1}, top_k=5)]
    assert "c" in nodes
    assert "d" not in nodes  # prerequisite c not mastered


def test_skips_mastered_nodes():
    recs = recommend_next(graph=GRAPH, mastery_map={"a": 0.9, "b": 0.95, "c": 0.98, "d": 0.9})
    assert recs == []  # everything mastered


def test_forgetting_risk_boosts_score():
    base = recommend_next(graph=GRAPH, mastery_map={"a": 0.9, "b": 0.5}, top_k=1)
    risky = recommend_next(graph=GRAPH, mastery_map={"a": 0.9, "b": 0.5},
                           forgetting_map={"b": 0.9}, top_k=1)
    assert risky[0].score > base[0].score


def test_validation():
    with pytest.raises(RecommenderError):
        recommend_next(graph={"nodes": [], "edges": []}, mastery_map={})
    with pytest.raises(RecommenderError):
        recommend_next(graph=GRAPH, mastery_map={}, top_k=0)
