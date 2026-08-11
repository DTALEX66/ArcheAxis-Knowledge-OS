"""Tests for shared.knowledge_gardener (orphans, connections, gaps, evergreen)."""

from __future__ import annotations

from shared.knowledge_gardener import (
    detect_gaps,
    find_orphans,
    score_evergreen,
    suggest_connections,
)


def test_find_orphans_detects_unlinked(monkeypatch) -> None:
    docs = [{"id": "d1", "title": "Linked doc"}, {"id": "d2", "title": "Orphan doc"}]
    cards = [{"card_id": "c1", "title": "Card"}]
    links = [{"source_id": "d1", "target_id": "c1"}]

    def fake_select_all(table, limit):
        return {"kb_documents": docs, "kb_cards": cards, "kb_links": links}[table]

    monkeypatch.setattr("shared.knowledge_gardener.select_all", fake_select_all)
    orphans = find_orphans()
    ids = [o["id"] for o in orphans]
    assert "d2" in ids
    assert "d1" not in ids  # has outgoing link
    assert "c1" not in ids  # has incoming link
    assert orphans[0]["link_count"] == 0


def test_find_orphans_limit(monkeypatch) -> None:
    docs = [{"id": f"d{i}", "title": f"Doc {i}"} for i in range(5)]
    monkeypatch.setattr(
        "shared.knowledge_gardener.select_all",
        lambda table, limit: {"kb_documents": docs, "kb_cards": [], "kb_links": []}[table],
    )
    assert len(find_orphans(limit=2)) == 2


def test_suggest_connections_keyword_overlap(monkeypatch) -> None:
    source = {"id": "d1", "title": "Machine Learning", "content": "neural networks training models data"}
    docs = [
        source,
        {"id": "d2", "title": "Deep Learning", "content": "neural networks training"},
        {"id": "d3", "title": "Cooking", "content": "recipes ingredients kitchen"},
    ]

    def fake_select_one(table, sid):
        return source if sid == "d1" else None

    monkeypatch.setattr("shared.knowledge_gardener.select_one", fake_select_one)
    monkeypatch.setattr(
        "shared.knowledge_gardener.select_all",
        lambda table, limit: {"kb_documents": docs, "kb_cards": []}[table],
    )
    sugg = suggest_connections("d1", top_k=5)
    ids = [s["id"] for s in sugg]
    assert "d2" in ids  # shares keywords
    assert "d3" not in ids  # no overlap
    assert sugg[0]["overlap"] >= 1


def test_suggest_connections_missing_source(monkeypatch) -> None:
    monkeypatch.setattr("shared.knowledge_gardener.select_one", lambda table, sid: None)
    assert suggest_connections("ghost") == []


def test_detect_gaps_thin_tags(monkeypatch) -> None:
    cards = [
        {"card_id": "c1", "tags": ["python", "ml"]},
        {"card_id": "c2", "tags": ["python", "ml"]},
        {"card_id": "c3", "tags": ["python"]},
        {"card_id": "c4", "tags": ["rust"]},  # thin: 1 item
    ]
    monkeypatch.setattr(
        "shared.knowledge_gardener.select_all",
        lambda table, limit: {"kb_cards": cards, "kb_documents": []}[table],
    )
    result = detect_gaps()
    assert result["total_cards"] == 4
    # 'ml' (2 chars) is filtered by len(tag) > 2
    assert result["total_tags"] == 2
    thin = [g for g in result["gaps"] if g["status"] == "thin"]
    assert any(g["topic"] == "rust" for g in thin)
    assert any("rust" in r for r in result["recommendations"])


def test_detect_gaps_string_tags(monkeypatch) -> None:
    cards = [{"card_id": "c1", "tags": "python, ml, data"}]
    monkeypatch.setattr(
        "shared.knowledge_gardener.select_all",
        lambda table, limit: {"kb_cards": cards, "kb_documents": []}[table],
    )
    result = detect_gaps()
    assert result["total_tags"] == 2  # 'ml' filtered by len(tag) > 2


def test_score_evergreen_not_found(monkeypatch) -> None:
    monkeypatch.setattr("shared.knowledge_gardener.select_one", lambda table, sid: None)
    assert score_evergreen("ghost") == {"error": "not found"}


def test_score_evergreen_rich_note(monkeypatch) -> None:
    doc = {"id": "d1", "title": "Evergreen Note", "content": "Atomic focused content."}
    monkeypatch.setattr("shared.knowledge_gardener.select_one", lambda table, sid: doc)
    monkeypatch.setattr(
        "shared.knowledge_gardener.compute_backlinks",
        lambda doc_id: [{"id": "x1"}, {"id": "x2"}, {"id": "x3"}, {"id": "x4"}, {"id": "x5"}],
    )
    monkeypatch.setattr(
        "knowledge_base.reviews.get_review_history",
        lambda doc_id, limit=20: [{"quality": 5}, {"quality": 4}, {"quality": 5}],
    )
    monkeypatch.setattr("shared.auto_tagger.detect_atomicity", lambda content: {"is_atomic": True})
    result = score_evergreen("d1")
    assert result["level"] == "evergreen"
    assert result["evergreen_score"] >= 70
    assert result["breakdown"]["atomicity"] == 30
    assert result["link_count"] == 5
    assert result["review_count"] == 3


def test_score_evergreen_seedling(monkeypatch) -> None:
    doc = {"id": "d1", "title": "Draft", "content": "Notes"}
    monkeypatch.setattr("shared.knowledge_gardener.select_one", lambda table, sid: doc)
    monkeypatch.setattr("shared.knowledge_gardener.compute_backlinks", lambda doc_id: [])
    monkeypatch.setattr("knowledge_base.reviews.get_review_history", lambda doc_id, limit=20: [])
    monkeypatch.setattr("shared.auto_tagger.detect_atomicity", lambda content: {"is_atomic": False})
    result = score_evergreen("d1")
    assert result["level"] == "seedling"
    assert result["evergreen_score"] <= 40
