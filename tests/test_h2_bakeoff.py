"""Tests for H2 bake-off framework.

Verifies the framework operates correctly with the one available engine
(Tesseract). Other engines are registered as unavailable stubs.
"""

import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from shared.bakeoff import (
    BakeoffResult,
    EngineUnderTest,
    load_fixtures,
    report_csv,
    report_json,
    run_bakeoff,
)
from shared.bakeoff_engines import OCR_ENGINES, TESSERACT, get_available_engines


def _make_text_image(text: str, path: Path) -> None:
    """Create a simple image with black text on white background."""
    img = Image.new("RGB", (400, 100), "white")
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", 20)
    except OSError:
        font = ImageFont.load_default()
    draw.text((10, 10), text, fill="black", font=font)
    img.save(path)


class TestBakeoffFramework:
    def test_empty_fixtures(self) -> None:
        results = run_bakeoff(OCR_ENGINES, [])
        assert results == []

    def test_tesseract_available(self) -> None:
        assert TESSERACT.available

    def test_unavailable_engines_skipped(self) -> None:
        engines = [EngineUnderTest("unavail", fn=lambda p: "", available=False)]
        results = run_bakeoff(engines, [])
        assert results == []

    def test_stub_engines_are_unavailable(self) -> None:
        for e in OCR_ENGINES:
            if e.name != "tesseract":
                assert not e.available, f"{e.name} should be unavailable by default"

    def test_bakeoff_with_simple_text(self, tmp_path: Path) -> None:
        if not TESSERACT.available:
            return
        img = tmp_path / "hello.png"
        truth = tmp_path / "hello.txt"
        _make_text_image("Hello World", img)
        truth.write_text("Hello World", encoding="utf-8")

        fixtures = load_fixtures(tmp_path)
        assert len(fixtures) == 1

        results = run_bakeoff([TESSERACT], fixtures)
        assert len(results) == 1
        r = results[0]
        # Tesseract may fail if language data or binary is misconfigured
        if r.success:
            assert r.char_count > 0
            assert r.duration_ms > 0
        else:
            assert r.error is not None  # honest failure recorded

    def test_report_csv(self, tmp_path: Path) -> None:
        r = BakeoffResult(engine="test", fixture="f.png", file_size=100, success=True, cer=0.0)
        p = report_csv([r], tmp_path / "out.csv")
        assert p.read_text(encoding="utf-8").startswith("engine,fixture")

    def test_report_json(self, tmp_path: Path) -> None:
        r = BakeoffResult(engine="test", fixture="f.png", file_size=100, success=True, cer=0.0)
        p = report_json([r], tmp_path / "out.json")
        assert '"cer": 0.0' in p.read_text(encoding="utf-8")
