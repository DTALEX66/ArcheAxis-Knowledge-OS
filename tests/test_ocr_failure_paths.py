"""OCR must fail closed.

A missing engine, a stale or wrong executable, unsupported media and an
empty/whitespace result are all failures. None of them may be reported as a
successful conversion, because "the OCR produced nothing" rounded up to success
is exactly the silent-empty-content case this project refuses elsewhere.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from app.ingestion import ocr_adapter, rapid_ocr_adapter


def _png(path: Path) -> Path:
    from PIL import Image

    Image.new("RGB", (24, 24), "white").save(path)
    return path


def _isolate_executable_lookup(monkeypatch, *, tesseract_cmd: str) -> None:
    """Remove every other candidate so only the supplied path can be found."""
    monkeypatch.setenv("TESSERACT_CMD", tesseract_cmd)
    monkeypatch.setenv("PATH", "")
    for name in ("OS_EXTERNAL_CONFIG", "ARCHEAXIS_EXTERNAL_ROOT", "TESSDATA_PREFIX"):
        monkeypatch.delenv(name, raising=False)


# ------------------------------------------------------- missing executable


def test_missing_tesseract_executable_fails_closed(tmp_path, monkeypatch):
    pytest.importorskip("pytesseract")
    import pytesseract

    image = _png(tmp_path / "page.png")
    monkeypatch.setattr(
        pytesseract.pytesseract, "tesseract_cmd", str(tmp_path / "absent-tesseract")
    )

    result = ocr_adapter.convert_ocr(image)

    assert result.success is False, "an absent OCR engine must not convert anything"
    assert result.content == ""
    assert result.error


# -------------------------------------------------------------- stale shim


def test_a_stale_or_wrong_tesseract_shim_is_not_accepted(tmp_path, monkeypatch):
    stale = tmp_path / "tesseract-stale"
    stale.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
    _isolate_executable_lookup(monkeypatch, tesseract_cmd=str(stale))
    assert ocr_adapter._resolve_tesseract() == "", (
        "a file that exists but is not a runnable tesseract must be skipped"
    )

    _isolate_executable_lookup(monkeypatch, tesseract_cmd=sys.executable)
    assert ocr_adapter._resolve_tesseract() == "", (
        "a runnable program that does not identify itself as tesseract must be skipped"
    )


# --------------------------------------------------------- unsupported media


def test_a_file_the_ocr_engine_cannot_open_fails_closed(tmp_path):
    pytest.importorskip("fitz")
    unsupported = tmp_path / "unsupported.png"
    unsupported.write_bytes(bytes(range(256)) * 8)

    result = ocr_adapter.convert_ocr(unsupported)

    assert result.success is False
    assert result.content == ""
    assert result.error


# ---------------------------------------------------------------- bad result


def test_a_whitespace_only_ocr_result_is_not_a_success(tmp_path, monkeypatch):
    pytest.importorskip("pytesseract")
    import pytesseract

    image = _png(tmp_path / "blank.png")
    monkeypatch.setattr(pytesseract, "image_to_string", lambda *args, **kwargs: "   \n\t ")

    result = ocr_adapter.convert_ocr(image)

    assert result.success is False, "blank OCR text is empty content, not a conversion"
    assert result.content == ""
    assert result.error


def test_real_ocr_text_still_converts(tmp_path, monkeypatch):
    """Positive control: the fail-closed check must not reject real text."""
    pytest.importorskip("pytesseract")
    pytest.importorskip("fitz")
    import pytesseract

    image = _png(tmp_path / "text.png")
    monkeypatch.setattr(pytesseract, "image_to_string", lambda *args, **kwargs: "  记忆宫殿  ")

    result = ocr_adapter.convert_ocr(image)

    assert result.success is True
    assert "记忆宫殿" in result.content


# ------------------------------------------------- rapid OCR (image adapter)


def test_rapid_ocr_missing_file_fails_closed(tmp_path):
    result = rapid_ocr_adapter.convert_image_rapid(tmp_path / "absent.png")

    assert result["success"] is False
    assert result["text"] == ""
    assert result["error"] == "file not found"


def test_rapid_ocr_empty_and_whitespace_results_are_not_success(tmp_path, monkeypatch):
    image = _png(tmp_path / "blank.png")

    class _EmptyEngine:
        def __call__(self, _path):
            return None, None

    monkeypatch.setattr(rapid_ocr_adapter, "_engine", _EmptyEngine())
    result = rapid_ocr_adapter.convert_image_rapid(image)
    assert result["success"] is False
    assert result["text"] == ""

    class _WhitespaceEngine:
        def __call__(self, _path):
            return [[None, "   ", 0.9]], None

    monkeypatch.setattr(rapid_ocr_adapter, "_engine", _WhitespaceEngine())
    result = rapid_ocr_adapter.convert_image_rapid(image)
    assert result["success"] is False, "whitespace-only OCR text is not a successful conversion"


def test_rapid_ocr_engine_failure_is_not_a_success(tmp_path, monkeypatch):
    image = _png(tmp_path / "page.png")

    class _FailingEngine:
        def __call__(self, _path):
            raise RuntimeError("unsupported media")

    monkeypatch.setattr(rapid_ocr_adapter, "_engine", _FailingEngine())
    result = rapid_ocr_adapter.convert_image_rapid(image)

    assert result["success"] is False
    assert "unsupported media" in result["error"]
