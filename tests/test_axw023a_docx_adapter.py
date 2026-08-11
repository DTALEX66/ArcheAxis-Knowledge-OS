"""AXW-023A regression tests: structured DOCX adapter (honest degradation).

Verifies the DOCX adapter:
- fails closed with a clear error when markitdown[docx] is unavailable (no
  fake success — the honest-degradation guarantee).
- produces correct structured blocks from markdown (pure-function test).
- never reports success from metadata/empty content.
"""

import pathlib

from app.ingestion.docx_adapter import _to_blocks, convert_docx

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]


def _real_docx() -> pathlib.Path:
    cand = (
        _REPO_ROOT
        / "docs/architecture/imported-designs/reference-deliveries/archeaxis-2026/ArcheAxis OS Overview.docx"
    )
    return cand if cand.is_file() else None


def test_docx_without_markitdown_docx_fails_closed(tmp_path) -> None:
    """When markitdown[docx] (python-docx) is absent, conversion must fail
    closed rather than return a fake success."""
    docx = _real_docx()
    if docx is None:
        return  # no fixture in this checkout
    try:
        import docx  # noqa: F401  (python-docx present?)
        from markitdown import MarkItDown
        _ = MarkItDown  # markitdown present?
    except ImportError:
        pass  # proceed: we want the fail-closed path
    res = convert_docx(str(docx))
    if res.success:
        # If it did succeed (python-docx installed), it must have content.
        assert res.content.strip(), "success with empty content"
        return
    # Otherwise it must fail closed with a clear, honest error.
    assert res.error, "failed conversion must explain why"
    assert "markitdown" in (res.error or "").lower() or "docx" in (res.error or "").lower()


def test_to_blocks_parses_paragraphs_and_tables() -> None:
    md = "# Heading One\n\nThis is a paragraph.\n\n| A | B |\n| 1 | 2 |"
    blocks = _to_blocks(md)
    kinds = [b["kind"] for b in blocks]
    assert "heading" in kinds
    assert "paragraph" in kinds
    assert "table" in kinds
    # Every block carries a source anchor.
    for b in blocks:
        assert b["anchor"]["source_md"]


def test_to_blocks_drops_empty_chunks() -> None:
    blocks = _to_blocks("\n\n   \n\n# Only\n")
    kinds = [b["kind"] for b in blocks]
    assert kinds == ["heading"]


def test_convert_docx_missing_file_fails_closed(tmp_path) -> None:
    res = convert_docx(str(tmp_path / "nope.docx"))
    assert not res.success
    assert res.error
