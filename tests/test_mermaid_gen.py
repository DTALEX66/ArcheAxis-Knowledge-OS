"""Tests for shared.mermaid_gen (Mermaid diagram generators)."""

from __future__ import annotations

from shared.mermaid_gen import _safe_id, flowchart, knowledge_graph_mermaid, review_timeline_mermaid


def test_flowchart_basic_structure() -> None:
    steps = [
        {"id": "a", "label": "Start", "next_id": "b"},
        {"id": "b", "label": "End"},
    ]
    out = flowchart("Flow", steps)
    assert out.startswith("```mermaid\nflowchart TD")
    assert "title[Flow]" in out
    assert "a[Start]" in out
    assert "a --> b" in out
    assert "b[End]" in out
    assert out.endswith("```")


def test_flowchart_missing_fields() -> None:
    out = flowchart("F", [{"id": "x"}])
    assert "x[x]" in out  # label falls back to id
    assert "x -->" not in out  # no next_id → no edge


def test_knowledge_graph_mermaid(monkeypatch) -> None:
    graph = {
        "nodes": [
            {"id": "doc1", "title": "Doc One", "type": "document"},
            {"id": "card1", "title": "Card", "type": "card"},
        ],
        "edges": [{"source": "doc1", "target": "card1", "link_type": "references"}],
    }
    monkeypatch.setattr("shared.backlinks.compute_graph", lambda limit: graph)
    out = knowledge_graph_mermaid(max_nodes=10)
    assert "graph LR" in out
    assert "Doc One" in out
    # cards use rounded shape (([...]))
    assert "ncard1([Card])" in out
    assert "references" in out


def test_knowledge_graph_safe_ids() -> None:
    graph = {
        "nodes": [{"id": "my doc 1!", "title": "T", "type": "document"}],
        "edges": [],
    }

    import shared.backlinks as bl
    import shared.mermaid_gen as mg
    bl.compute_graph = lambda limit: graph
    out = mg.knowledge_graph_mermaid(max_nodes=5)
    assert "nmy_doc_1_" in out  # non-alnum replaced with _


def test_review_timeline_no_reviews(monkeypatch) -> None:
    monkeypatch.setattr("knowledge_base.reviews.get_review_history", lambda cid, limit: [])
    out = review_timeline_mermaid("card1")
    assert "gantt" in out
    assert "No reviews yet" in out


def test_review_timeline_with_reviews(monkeypatch) -> None:
    reviews = [
        {"created_at": "2026-08-01T10:00:00", "quality": 5},
        {"created_at": "2026-08-05T10:00:00", "quality": 1},
    ]
    monkeypatch.setattr("knowledge_base.reviews.get_review_history", lambda cid, limit: reviews)
    out = review_timeline_mermaid("card1")
    assert "gantt" in out
    assert "Good Reviews" in out  # quality 5
    assert "Needs Work" in out  # quality 1
    assert "2026-08-01" in out


def test_review_timeline_truncates() -> None:
    reviews = [{"created_at": f"2026-08-{i:02d}T00:00:00", "quality": 3} for i in range(1, 25)]
    import knowledge_base.reviews as kbr
    import shared.mermaid_gen as mg
    kbr.get_review_history = lambda cid, limit: reviews
    out = mg.review_timeline_mermaid("card1")
    # only first 15 rendered
    assert "2026-08-01" in out
    assert "2026-08-20" not in out


def test_safe_id() -> None:
    assert _safe_id("hello") == "nhello"
    assert _safe_id("my doc!") == "nmy_doc_"
    assert _safe_id("x" * 50)[:20] == "n" + "x" * 19  # capped
