"""MFX-010 regression tests: honest image/media conversion capability.

Verifies that an image or media file is never reported as a content-success
from metadata alone. Real OCR (Tesseract) must run for an image to count as
converted; without it the conversion must fail closed with a clear error
instead of returning Pillow/FFprobe metadata text.
"""

import importlib
import pathlib
from types import ModuleType

import pytest

_IMG_FIXTURES_DIR = pathlib.Path(__file__).resolve().parents[0]


def _fresh_module() -> ModuleType:
    """Reload multi_format so patched host tooling is picked up."""
    mod = importlib.import_module("app.ingestion.multi_format")
    return importlib.reload(mod)


@pytest.fixture
def no_tesseract(monkeypatch: pytest.MonkeyPatch) -> None:
    """Simulate Tesseract + pytesseract being unavailable."""
    mod = _fresh_module()
    monkeypatch.setattr(mod, "_ENGINES", dict(mod._ENGINES))
    # Force the image chain's OCR engine to report unavailable by patching
    # the shared availability probes it calls.
    import shared.adapter_fixtures as af
    monkeypatch.setattr(af, "_tesseract_available", lambda: False)
    monkeypatch.setattr(af, "_pytesseract_importable", lambda: False)


def test_image_without_ocr_is_not_content_success(tmp_path, no_tesseract) -> None:
    """An image with no OCR engine must fail closed, not return metadata."""
    from PIL import Image
    img = tmp_path / "blank.png"
    Image.new("RGB", (10, 10), color="white").save(str(img))

    mod = _fresh_module()
    fmt = mod.detect_format(img)
    assert fmt == "image"

    with pytest.raises(RuntimeError) as exc:
        mod.convert_file(str(img))
    msg = str(exc.value)
    assert "No engine could convert" in msg
    # Must mention OCR is required — never silently success from metadata.
    assert "Tesseract" in msg or "OCR" in msg


def test_image_engine_chain_has_no_metadata_only_first(tmp_path) -> None:
    """Image chain must lead with a real content engine, not Pillow metadata."""
    mod = _fresh_module()
    chain = mod._ENGINES["image"]
    engines = [name for name, _ in chain]
    # Pillow metadata must not be a content-success source in the image chain.
    assert "pillow" not in engines, f"pillow metadata leaked into image chain: {engines}"
    # A real OCR engine should be present (or a clear degraded fallback).
    assert any("pytesseract" in e or "ocr" in e for e in engines), engines


def test_empty_content_is_not_success(monkeypatch, tmp_path) -> None:
    """A success result with empty content must not be returned as converted."""
    import shared.adapter_contract as contract
    from app.ingestion import multi_format

    # Force every engine to return success with empty content.
    def _empty_ok(_p):
        return contract.AdapterResult(success=True, content="   ", engine="stub")

    monkeypatch.setattr(multi_format, "_ENGINES", {"txt": [("stub", _empty_ok)]})
    src = tmp_path / "a.txt"
    src.write_text("x", encoding="utf-8")
    with pytest.raises(RuntimeError):
        multi_format.convert_file(str(src))
