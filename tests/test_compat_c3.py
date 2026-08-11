from __future__ import annotations

import json
from pathlib import Path

import pytest

from shared.compat.c3 import analyze_canvas, analyze_markdown, canvas_semantic_diff


def test_markdown_c3_extracts_links_tags_tasks_embeds_and_missing_targets(tmp_path: Path) -> None:
    (tmp_path / "notes").mkdir()
    (tmp_path / "assets").mkdir()
    (tmp_path / "notes" / "target.md").write_text("# target", encoding="utf-8")
    (tmp_path / "assets" / "ok.png").write_bytes(b"png")
    note = tmp_path / "notes" / "source.md"
    note.write_text(
        "---\ntags: [alpha]\naliases: [Source]\n---\n"
        "# Heading\n"
        "#alpha #project/test\n"
        "- [ ] finish [[target|Target]]\n"
        "- [x] read [guide](target.md)\n"
        "![[../assets/ok.png]] ![missing](../assets/no.pdf)\n"
        "[[missing-note]]\n",
        encoding="utf-8",
    )

    report = analyze_markdown(note, vault_root=tmp_path)

    assert report.tags == ["alpha", "project/test"]
    assert report.tasks == ["finish [[target|Target]]", "read [guide](target.md)"]
    assert {link.target for link in report.links} == {"target", "target.md", "missing-note"}
    assert report.embeds == ["../assets/ok.png", "../assets/no.pdf"]
    assert report.missing_links == ["missing-note"]
    assert report.missing_attachments == ["../assets/no.pdf"]


def test_markdown_c3_does_not_treat_heading_as_tag(tmp_path: Path) -> None:
    note = tmp_path / "note.md"
    note.write_text("# Heading\nBody #real-tag\n", encoding="utf-8")
    assert analyze_markdown(note, vault_root=tmp_path).tags == ["real-tag"]


def _canvas(nodes: list[dict], edges: list[dict]) -> str:
    return json.dumps({"nodes": nodes, "edges": edges})


def test_canvas_c3_validates_schema_and_edge_endpoints(tmp_path: Path) -> None:
    canvas = tmp_path / "board.canvas"
    canvas.write_text(
        _canvas(
            [{"id": "a", "type": "text", "x": 0, "y": 0, "width": 100, "height": 80, "text": "A"}],
            [],
        ),
        encoding="utf-8",
    )
    report = analyze_canvas(canvas)
    assert report.valid is True
    assert report.node_ids == ["a"]

    canvas.write_text(_canvas([{"id": "a", "type": "text"}], [{"id": "e", "fromNode": "a", "toNode": "missing"}]), encoding="utf-8")
    invalid = analyze_canvas(canvas)
    assert invalid.valid is False
    assert "edge e references missing node missing" in invalid.errors


def test_canvas_c3_rejects_duplicate_ids_and_invalid_json(tmp_path: Path) -> None:
    canvas = tmp_path / "bad.canvas"
    canvas.write_text(_canvas([{"id": "a", "type": "text"}, {"id": "a", "type": "text"}], []), encoding="utf-8")
    assert analyze_canvas(canvas).valid is False
    canvas.write_text("not json", encoding="utf-8")
    assert analyze_canvas(canvas).errors == ["invalid JSON"]


def test_canvas_semantic_diff_is_order_independent() -> None:
    before = {"nodes": [{"id": "a", "type": "text", "text": "A"}], "edges": []}
    after = {"edges": [], "nodes": [{"id": "a", "type": "text", "text": "B"}, {"id": "b", "type": "text", "text": "B"}]}
    diff = canvas_semantic_diff(before, after)
    assert diff == {"added_nodes": ["b"], "removed_nodes": [], "changed_nodes": ["a"], "added_edges": [], "removed_edges": [], "changed_edges": []}


def test_markdown_c3_rejects_path_escape(tmp_path: Path) -> None:
    outside = tmp_path.parent / "outside-c3.md"
    outside.write_text("outside", encoding="utf-8")
    note = tmp_path / "note.md"
    note.write_text("[bad](../outside-c3.md)", encoding="utf-8")
    with pytest.raises(ValueError, match="escapes vault root"):
        analyze_markdown(note, vault_root=tmp_path)
