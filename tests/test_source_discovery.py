"""Tests for shared.source_discovery (evidence source directory scanning).

NOTE: tests/conftest.py redirects TMP/TEMP/TMPDIR into the hidden
.hermes/... tree, and discover_sources skips any path part starting
with '.', so real temp dirs can't be scanned. Tests monkeypatch
Path.rglob with a fake file tree instead.
"""

from __future__ import annotations

from pathlib import Path

from shared.source_discovery import SOURCE_EXTENSIONS, discover_sources, match_sources_to_cards


class _FakeFile:
    """Minimal Path stand-in with the attributes discover_sources touches."""

    def __init__(self, path_str: str, size: int = 100):
        self._p = Path(path_str)
        self._size = size

    @property
    def parts(self) -> tuple[str, ...]:
        return self._p.parts

    @property
    def suffix(self) -> str:
        return self._p.suffix.lower()

    @property
    def name(self) -> str:
        return self._p.name

    def is_file(self) -> bool:
        return True

    def stat(self):
        class _S:
            st_size = self._size

        return _S()

    def __str__(self) -> str:
        return str(self._p)


def _rglob_fake(root_str: str, files: list[tuple[str, int]]) -> list[_FakeFile]:
    """Build fake rglob results under a non-hidden root."""
    base = Path("C:/tmp_test/source_root")
    return [_FakeFile(str(base / rel), size) for rel, size in files]


def _patch_rglob(monkeypatch, files: list[tuple[str, int]]) -> None:
    monkeypatch.setattr(Path, "rglob", lambda self, pat: iter(_rglob_fake(str(self), files)))
    # discover_sources checks root.exists(); fake it so the scan proceeds
    monkeypatch.setattr(Path, "exists", lambda self: True)


def test_discover_sources_basic(monkeypatch) -> None:
    _patch_rglob(monkeypatch, [("a.pdf", 100), ("b.mp4", 100), ("c.png", 100), ("notes.txt", 100)])
    result = discover_sources("C:/tmp_test/source_root")
    assert result["total_found"] == 3  # txt not in SOURCE_EXTENSIONS
    assert result["by_type"]["pdf"] == 1
    assert result["by_type"]["video"] == 1
    assert result["by_type"]["image"] == 1


def test_discover_sources_skip_dirs(monkeypatch) -> None:
    _patch_rglob(
        monkeypatch,
        [("keep/a.pdf", 100), (".git/b.pdf", 100), ("node_modules/c.pdf", 100), (".obsidian/d.pdf", 100)],
    )
    result = discover_sources("C:/tmp_test/source_root")
    assert result["total_found"] == 1
    assert "keep" in result["files"][0]["path"]


def test_discover_sources_missing_dir() -> None:
    result = discover_sources("/nonexistent/path/xyz")
    assert result.get("error", "").startswith("directory not found")


def test_discover_sources_max_files(monkeypatch) -> None:
    _patch_rglob(monkeypatch, [(f"f{i}.pdf", 100) for i in range(10)])
    result = discover_sources("C:/tmp_test/source_root", max_files=3)
    assert result["total_found"] == 3


def test_discover_sources_size_threshold(monkeypatch) -> None:
    _patch_rglob(monkeypatch, [("big.pdf", 2 * 1024 * 1024), ("small.pdf", 100)])
    result = discover_sources("C:/tmp_test/source_root", size_threshold_mb=1)
    assert result["total_found"] == 1
    assert "small" in result["files"][0]["path"]


def test_source_extensions_known_types() -> None:
    assert SOURCE_EXTENSIONS[".pdf"] == "pdf"
    assert SOURCE_EXTENSIONS[".mp4"] == "video"
    assert SOURCE_EXTENSIONS[".pptx"] == "slides"
    assert SOURCE_EXTENSIONS[".docx"] == "document"
    assert SOURCE_EXTENSIONS[".png"] == "image"
    assert SOURCE_EXTENSIONS[".wav"] == "audio"
    assert SOURCE_EXTENSIONS[".csv"] == "data"


def test_match_sources_to_cards_matches_by_name(monkeypatch) -> None:
    # 文件名与卡片标题共享前 10 字符（fname[:10] in title 或 title[:10] in fname）
    _patch_rglob(monkeypatch, [("machine le.pdf", 100), ("unrelated_video.mp4", 100)])
    cards = [
        {"id": "c1", "card_id": "c1", "title": "Machine Learning Basics"},
        {"id": "c2", "card_id": "c2", "title": "Cooking"},
    ]
    monkeypatch.setattr("shared.storage.select_all", lambda table, limit: cards)
    result = match_sources_to_cards("C:/tmp_test/source_root")
    assert result["matched_count"] == 1
    assert result["unmatched_count"] == 1
    assert result["matched"][0]["card_title"] == "Machine Learning Basics"
    assert result["matched"][0]["confidence"] == "medium"
    unmatched_paths = [u["path"] for u in result["unmatched"]]
    assert any("unrelated_video" in p for p in unmatched_paths)


def test_match_sources_to_cards_no_cards(monkeypatch) -> None:
    _patch_rglob(monkeypatch, [("a.pdf", 100)])
    monkeypatch.setattr("shared.storage.select_all", lambda table, limit: [])
    result = match_sources_to_cards("C:/tmp_test/source_root")
    assert result["matched_count"] == 0
    assert result["unmatched_count"] == 1
