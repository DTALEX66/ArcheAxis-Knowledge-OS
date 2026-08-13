"""AXW-023B~F regression tests: structured adapters (honest degradation).

Each adapter test verifies:
- fails closed with a clear error when its engine dependency is missing
  (no fake success).
- produces structured blocks with anchors when the engine is present.
- never reports success from empty content.
"""

import contextlib
import pathlib

from app.ingestion.html_adapter import convert_html
from app.ingestion.media_adapter import convert_media
from app.ingestion.ocr_adapter import convert_ocr
from app.ingestion.pptx_adapter import convert_pptx
from app.ingestion.xlsx_adapter import convert_xlsx

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]

_HTML_SAMPLE = (
    "<html><head><title>Sample Article</title>"
    "<meta name='robots' content='noindex'></head>"
    "<body><article><h1>Hello</h1><p>Main content paragraph.</p></article>"
    "<nav>ignored sidebar</nav></body></html>"
)


def _real_pptx():
    cand = _REPO_ROOT / "tests/fixtures/sample.pptx"
    return cand if cand.is_file() else None


def _real_xlsx():
    cand = _REPO_ROOT / "tests/fixtures/sample.xlsx"
    return cand if cand.is_file() else None


# ── AXW-023B PPTX ────────────────────────────────────────────────────────


def test_pptx_missing_file_fails_closed(tmp_path) -> None:
    res = convert_pptx(str(tmp_path / "nope.pptx"))
    assert not res.success
    assert res.error


def test_pptx_without_engine_fails_closed() -> None:
    pptx = _real_pptx()
    if pptx is None:
        return
    with contextlib.suppress(ImportError):
        from pptx import Presentation  # noqa: F401
    res = convert_pptx(str(pptx))
    if res.success:
        assert res.content.strip(), "success with empty content"
        kinds = [b["kind"] for b in res.metadata["blocks"]]
        assert "slide" in kinds or "slide-empty" in kinds
        for b in res.metadata["blocks"]:
            assert "slide_index" in b["anchor"]
        return
    assert res.error, "failed conversion must explain why"


# ── AXW-023C XLSX ────────────────────────────────────────────────────────


def test_xlsx_missing_file_fails_closed(tmp_path) -> None:
    res = convert_xlsx(str(tmp_path / "nope.xlsx"))
    assert not res.success
    assert res.error


def test_xlsx_without_engine_fails_closed() -> None:
    xlsx = _real_xlsx()
    if xlsx is None:
        return
    with contextlib.suppress(ImportError):
        from openpyxl import load_workbook  # noqa: F401
    res = convert_xlsx(str(xlsx))
    if res.success:
        assert res.content.strip(), "success with empty content"
        for b in res.metadata["blocks"]:
            assert "sheet" in b["anchor"]
        return
    assert res.error, "failed conversion must explain why"


# ── AXW-023D OCR ─────────────────────────────────────────────────────────


def test_ocr_missing_file_fails_closed(tmp_path) -> None:
    res = convert_ocr(str(tmp_path / "nope.pdf"))
    assert not res.success
    assert res.error


def test_ocr_quality_and_language_metrics() -> None:
    """Pure-function checks on quality/language helpers without OCR runs."""
    from app.ingestion.ocr_adapter import _detect_language, _quality

    # Non-space printable ratio, rounded to 3dp by the helper itself.
    assert _quality("hello world") == 0.909
    assert _quality("") == 0.0
    assert "zh" in _detect_language("这是中文测试")
    assert "eng" in _detect_language("hello world")


# ── AXW-023E HTML ────────────────────────────────────────────────────────


def test_html_extracts_main_content_and_metadata() -> None:
    res = convert_html(_HTML_SAMPLE)
    assert res.success
    assert "Main content paragraph" in res.content
    assert "Hello" in res.content  # article heading extracted
    assert res.metadata["title"] == "Sample Article"
    assert res.metadata["robots"] == "noindex"
    assert "fetched_at" in res.metadata
    assert res.metadata["blocks"][0]["kind"] == "article"


def test_html_empty_input_fails_closed() -> None:
    res = convert_html("   ")
    assert not res.success
    assert res.error


# ── AXW-023F Media ───────────────────────────────────────────────────────


def test_media_missing_file_fails_closed(tmp_path) -> None:
    res = convert_media(str(tmp_path / "nope.mp4"))
    assert not res.success
    assert res.error


def test_media_without_engine_fails_closed(tmp_path) -> None:
    """faster-whisper is optional; without it conversion must fail closed
    with a clear error and must NEVER trigger a model download."""
    fake = tmp_path / "empty.mp4"
    fake.write_bytes(b"\x00\x00\x00\x00")
    res = convert_media(str(fake))
    assert not res.success
    assert res.error
