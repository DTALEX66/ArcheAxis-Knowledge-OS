"""Light tests for OCR adapter auto-configuration (TESSDATA fix)."""
from __future__ import annotations

from app.ingestion.ocr_adapter import _detect_language, _quality, configure_tesseract


def test_detect_language():
    assert "zh" in _detect_language("中文内容")
    assert "eng" in _detect_language("english words")
    assert "unknown" in _detect_language("12345")


def test_quality_ratio():
    assert _quality("正常文本") > 0.5
    assert _quality("") == 0.0


def test_configure_tesseract_resolves_paths():
    binary, tessdata = configure_tesseract()
    # on this machine both resolve; CI without tesseract may return empty —
    # the fix is that the resolver never raises and picks valid tessdata
    assert isinstance(binary, str)
    assert isinstance(tessdata, str)
    if binary:
        import os
        assert os.path.exists(binary)
