"""Tests for shared.diversity_audit (content modality diversity scoring)."""

from __future__ import annotations

from shared.diversity_audit import analyze_diversity, diversity_radar


def _doc(doc_id: str, content: str, title: str = "Doc") -> dict:
    return {"id": doc_id, "title": title, "content": content}


def test_text_only_scores_baseline(monkeypatch) -> None:
    monkeypatch.setattr("shared.storage.select_one", lambda table, sid: _doc("d1", "Just plain text here."))
    result = analyze_diversity("d1")
    assert result["status"] == "text_only"
    assert result["diversity_score"] == 10
    assert result["distinct_modalities"] == 0
    assert result["suggestions"]


def test_basic_diversity_two_modalities(monkeypatch) -> None:
    content = "## Heading\nSome text.\n\n| col | col2 |\n| --- | --- |\n"
    monkeypatch.setattr("shared.storage.select_one", lambda table, sid: _doc("d2", content))
    result = analyze_diversity("d2")
    assert result["status"] == "basic"
    assert result["diversity_score"] == 40
    assert result["distinct_modalities"] >= 2
    assert "tables" in result["modalities"]


def test_good_diversity_four_modalities(monkeypatch) -> None:
    content = "\n".join(
        [
            "## Heading",
            "Text with ![image](x.png)",
            "| a | b |",
            "| --- | --- |",
            "```mermaid",
            "graph TD; A-->B",
            "```",
            "- [ ] task item",
            "> [!note] Callout",
        ]
    )
    monkeypatch.setattr("shared.storage.select_one", lambda table, sid: _doc("d3", content))
    result = analyze_diversity("d3")
    # fixture 含 heading/tables/mermaid/tasks/images/callouts → 6 模态
    assert result["status"] == "rich"
    assert result["diversity_score"] == 100
    assert result["distinct_modalities"] >= 4
    assert "mermaid" in result["modalities"]
    assert "callouts" in result["modalities"]


def test_rich_diversity_six_modalities(monkeypatch) -> None:
    content = "\n".join(
        [
            "## Heading",
            "Text ![img](a.png)",
            "| a | b |",
            "| --- | --- |",
            "```mermaid\ngraph TD; A-->B\n```",
            "```python\nprint(1)\n```",
            "- [x] done task",
            "> [!tip] Tip callout",
            "$$e=mc^2$$",
        ]
    )
    monkeypatch.setattr("shared.storage.select_one", lambda table, sid: _doc("d4", content))
    result = analyze_diversity("d4")
    assert result["status"] == "rich"
    assert result["diversity_score"] == 100
    assert result["distinct_modalities"] >= 6


def test_missing_document_returns_error(monkeypatch) -> None:
    monkeypatch.setattr("shared.storage.select_one", lambda table, sid: None)
    result = analyze_diversity("missing")
    assert result == {"error": "not found"}


def test_cards_fallback(monkeypatch) -> None:
    calls = []

    def fake_select_one(table, sid):
        calls.append(table)
        if table == "kb_documents":
            return None
        return {"id": "c1", "title": "Card", "content": "## H\nText.\n"}

    monkeypatch.setattr("shared.storage.select_one", fake_select_one)
    result = analyze_diversity("c1")
    assert "error" not in result
    assert calls == ["kb_documents", "kb_cards"]


def test_diversity_radar_sorted(monkeypatch) -> None:
    rich = {"id": "r", "title": "Rich", "content": "## H\n![i](x.png)\n| a |\n| --- |\n```mermaid\nA\n```\n```py\nx()\n```\n- [ ] t\n> [!a] c\n$$x$$\n"}
    basic = {"id": "b", "title": "Basic", "content": "## H\nText with ![i](x.png)\n| a |\n| --- |\n"}
    docs = [rich, basic]

    # select_all 是模块级绑定（文件顶 from shared.storage import select_all），
    # 必须 patch shared.diversity_audit.select_all 而非 shared.storage.select_all。
    monkeypatch.setattr("shared.diversity_audit.select_all", lambda table, limit: docs if table == "kb_documents" else [])
    monkeypatch.setattr("shared.storage.select_one", lambda table, sid: next(d for d in docs if d["id"] == sid))

    radar = diversity_radar(limit=10)
    assert len(radar) == 2
    assert radar[0]["doc_id"] == "r"
    assert radar[0]["diversity_score"] >= radar[1]["diversity_score"]
