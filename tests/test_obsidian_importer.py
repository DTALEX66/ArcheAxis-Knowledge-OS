"""Tests for shared.obsidian_importer (vault scanner + frontmatter + import)."""

from __future__ import annotations

import tempfile
from pathlib import Path

from shared.backlinks import index_document_links, parse_links
from shared.obsidian_importer import (
    FRONTMATTER_MAP,
    VAULT_FOLDER_MAP,
    _parse_frontmatter,
    import_file,
    import_vault,
    scan_vault,
)


class _FakeFile:
    def __init__(self, path_str: str, size: int = 100):
        self._p = Path(path_str)
        self._size = size
        self._rel = path_str.split("vault/", 1)[-1]

    @property
    def parts(self) -> tuple[str, ...]:
        return Path(self._rel).parts

    @property
    def stem(self) -> str:
        return self._p.stem

    def relative_to(self, root) -> _FakeFile:
        return self

    def __str__(self) -> str:
        return self._rel

    @property
    def name(self) -> str:
        return self._p.name

    def exists(self) -> bool:
        return True

    def stat(self):
        class _S:
            st_size = self._size

        return _S()


def test_vault_folder_map_shape() -> None:
    assert VAULT_FOLDER_MAP["02_课程库"]["asset_type"] == "document"
    assert VAULT_FOLDER_MAP["03_知识卡片"]["asset_type"] == "card"
    assert VAULT_FOLDER_MAP["50_领域知识"]["asset_type"] == "machine_knowledge"


def test_frontmatter_map_shape() -> None:
    assert FRONTMATTER_MAP["title"] == "title"
    assert FRONTMATTER_MAP["course"] == "source_topic"


def test_parse_links_classifies_embed_once_without_duplicate_wikilink() -> None:
    links = parse_links("See [[目标笔记|目标]] and ![[附件.png]].")

    assert [(item["target"], item["link_type"], item["is_embed"]) for item in links] == [
        ("目标笔记", "wikilink", False),
        ("附件.png", "embed", True),
    ]


def test_parse_links_preserves_alias_and_heading_anchor() -> None:
    links = parse_links("[[目标笔记#结论|显示文本]]")

    assert links == [
        {
            "target": "目标笔记#结论",
            "alias": "显示文本",
            "is_embed": False,
            "link_type": "wikilink",
        }
    ]


def test_index_document_links_persists_relationship_facts(monkeypatch) -> None:
    rows = []
    replaced = []
    monkeypatch.setattr(
        "shared.storage.insert",
        lambda table, row: rows.append((table, row)),
    )
    monkeypatch.setattr(
        "shared.storage.replace_links_for_source",
        lambda source_id: replaced.append(source_id),
    )

    count = index_document_links(
        "doc-1",
        "See [[目标笔记|目标]] and ![[附件.png]]. Also [源](同目录.md).",
    )

    assert count == 3
    assert [row["link_type"] for _table, row in rows] == [
        "wikilink",
        "embed",
        "md_link",
    ]
    assert rows[1][1]["is_embed"] == 1
    assert replaced == ["doc-1"]


def test_parse_frontmatter_no_frontmatter() -> None:
    fm, body = _parse_frontmatter("Just plain text.\n")
    assert fm == {}
    assert body == "Just plain text.\n"


def test_parse_frontmatter_simple() -> None:
    text = "---\ntitle: My Note\ntype: card\ncourse: Math\n---\nBody text here.\n"
    fm, body = _parse_frontmatter(text)
    assert fm["title"] == "My Note"
    assert fm["type"] == "card"
    assert fm["course"] == "Math"
    assert body == "Body text here.\n"


def test_parse_frontmatter_list_tags() -> None:
    text = '---\ntags: [alpha, beta, "gamma"]\n---\nBody.\n'
    fm, _body = _parse_frontmatter(text)
    assert fm["tags"] == ["alpha", "beta", "gamma"]


def test_parse_frontmatter_quoted_values() -> None:
    text = '---\ntitle: "Quoted Title"\n---\nBody.\n'
    fm, _body = _parse_frontmatter(text)
    assert fm["title"] == "Quoted Title"


def test_scan_vault_classifies_folders(monkeypatch) -> None:
    files = [
        "02_课程库/数学/calculus.md",
        "03_知识卡片/algebra.md",
        "50_领域知识/domain.md",
        "80_索引数据库/index.md",
        "top-level.md",
        "90_模板/template.md",
        "93_导入报告/report.md",
    ]

    def fake_rglob(self, pat):
        return iter([_FakeFile("C:/vault/" + f) for f in files])

    monkeypatch.setattr(Path, "rglob", fake_rglob)
    monkeypatch.setattr(Path, "exists", lambda self: True)
    inventory = scan_vault("C:/vault")
    assert inventory["total_files"] == 5  # 模板/报告 skipped
    assert len(inventory["courses"]) == 1
    assert inventory["courses"][0]["course"] == "数学"
    assert len(inventory["cards"]) == 1
    assert len(inventory["domain_knowledge"]) == 1
    assert len(inventory["indexes"]) == 1
    assert len(inventory["other"]) == 1


def test_scan_vault_missing_dir() -> None:
    result = scan_vault("/nonexistent/vault")
    assert result.get("error", "").startswith("vault not found")


def test_import_file_dry_run() -> None:
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        note = Path(d) / "02_课程库" / "数学" / "note.md"
        note.parent.mkdir(parents=True)
        note.write_text("---\ntitle: Calculus Basics\n---\nContent here.\n", encoding="utf-8")
        result = import_file(d, "02_课程库/数学/note.md", dry_run=True)
        assert result["status"] == "dry_run"
        assert result["asset_type"] == "document"
        assert result["title"] == "Calculus Basics"
        assert result["body_length"] > 0
        assert "kb_id" not in result


def test_import_file_not_found() -> None:
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        result = import_file(d, "missing/note.md", dry_run=True)
        assert result.get("error") == "file not found"


def test_import_file_card_import(monkeypatch) -> None:
    import tempfile

    inserted = {}

    def fake_insert(table, row):
        inserted[table] = row

    monkeypatch.setattr("shared.storage.insert", fake_insert)
    monkeypatch.setattr("shared.storage.fts5_sync", lambda *a, **k: None)

    with tempfile.TemporaryDirectory() as d:
        note = Path(d) / "03_知识卡片" / "card.md"
        note.parent.mkdir(parents=True)
        note.write_text("---\ntitle: My Card\n---\nCard content.\n", encoding="utf-8")
        result = import_file(d, "03_知识卡片/card.md", dry_run=False)
        assert result["status"] == "imported"
        assert result["asset_type"] == "card"
        assert result["kb_id"].startswith("card_")
        assert inserted["kb_cards"]["title"] == "My Card"
        assert "obsidian-card" in inserted["kb_cards"]["tags"]


def test_import_file_indexes_wikilinks_embeds_and_relative_links(monkeypatch) -> None:
    import tempfile

    inserted = {}
    indexed = {}

    def fake_insert(table, row):
        inserted[table] = row

    def fake_index(doc_id, content):
        indexed["doc_id"] = doc_id
        indexed["content"] = content
        return 3

    monkeypatch.setattr("shared.storage.insert", fake_insert)
    monkeypatch.setattr("shared.storage.fts5_sync", lambda *a, **k: None)
    monkeypatch.setattr("shared.obsidian_importer.index_document_links", fake_index)

    with tempfile.TemporaryDirectory() as d:
        note = Path(d) / "02_课程库" / "数学" / "linked.md"
        note.parent.mkdir(parents=True)
        body = "See [[目标笔记|目标]] and ![[附件.png]]. Also [源](同目录.md)."
        note.write_text(body, encoding="utf-8")

        result = import_file(d, "02_课程库/数学/linked.md", dry_run=False)

    assert result["status"] == "imported"
    assert result["links_indexed"] == 3
    assert indexed["doc_id"] == result["kb_id"]
    assert indexed["content"] == body
    assert inserted["kb_documents"]["content"] == body


def test_import_file_indexes_frontmatter_wikilinks(monkeypatch) -> None:
    import tempfile

    rows = []
    monkeypatch.setattr("shared.storage.insert", lambda table, row: rows.append((table, row)))
    monkeypatch.setattr("shared.storage.fts5_sync", lambda *a, **k: None)

    with tempfile.TemporaryDirectory() as d:
        note = Path(d) / "note.md"
        note.write_text("---\nrelated: [[Other note]]\n---\nBody.\n", encoding="utf-8")
        result = import_file(d, "note.md", dry_run=False)

    links = [row for table, row in rows if table == "kb_links"]
    assert result["links_indexed"] == 1
    assert links[0]["target_id"] == "Other note"


def test_import_file_uses_stable_id_for_repeat_imports(monkeypatch) -> None:
    inserted = []
    monkeypatch.setattr("shared.storage.insert", lambda table, row: inserted.append((table, row)))
    monkeypatch.setattr("shared.storage.fts5_sync", lambda *a, **k: None)

    with tempfile.TemporaryDirectory() as d:
        note = Path(d) / "note.md"
        note.write_text("# Stable\n", encoding="utf-8")
        first = import_file(d, "note.md", dry_run=False)
        second = import_file(d, "note.md", dry_run=False)

    assert first["kb_id"] == second["kb_id"]
    link_rows = [row for table, row in inserted if table == "kb_links"]
    assert len(link_rows) == 0


def test_import_vault_dry_run(monkeypatch) -> None:
    files = [
        "03_知识卡片/a.md",
        "02_课程库/Math/b.md",
        "top.md",
    ]

    def fake_rglob(self, pat):
        return iter([_FakeFile("C:/vault/" + f) for f in files])

    monkeypatch.setattr(Path, "rglob", fake_rglob)
    monkeypatch.setattr(Path, "exists", lambda self: True)
    # import_file reads real files — stub it for the dry-run batch path
    monkeypatch.setattr(
        "shared.obsidian_importer.import_file",
        lambda vr, rp, dry_run=True: {"path": rp, "status": "dry_run", "asset_type": "card", "dry_run": True},
    )
    report = import_vault("C:/vault", dry_run=True)
    assert report["summary"]["total_scanned"] == 3
    assert report["summary"]["imported"] == 0
    assert len(report["items"]) >= 2
