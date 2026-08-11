"""Tests for H2 bake-off framework.

Verifies the framework operates correctly with the one available engine
(Tesseract). Other engines are registered as unavailable stubs.
"""

import csv
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
from shared.bakeoff_engines import ASR_ENGINES, OCR_ENGINES, TESSERACT, TESSERACT_CHI_SIM


def _make_text_image(text: str, path: Path) -> None:
    """Create a simple image with black text on white background."""
    img = Image.new("RGB", (400, 100), "white")
    draw = ImageDraw.Draw(img)
    font = None
    # CJK-first font order: arial.ttf exists on most systems but renders
    # Chinese as blank boxes, producing empty OCR output.
    for candidate in ("msyh.ttc", "simhei.ttf", "simsun.ttc", "arial.ttf"):
        try:
            font = ImageFont.truetype(candidate, 20)
            break
        except OSError:
            continue
    if font is None:
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
        # Tesseract variants use the system binary; rapidocr activates when
        # rapidocr-onnxruntime is installed (ci-adapters group); faster-whisper
        # activates when faster-whisper is installed. Only the heavy-framework
        # stubs (paddleocr/easyocr/whisper.cpp) stay unavailable by default.
        for e in OCR_ENGINES + ASR_ENGINES:
            if e.name in {"tesseract", "tesseract-chi-sim", "rapidocr", "faster-whisper"}:
                continue
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

    def test_chi_sim_engine_renders_cjk_without_spacing(self, tmp_path: Path) -> None:
        if not TESSERACT_CHI_SIM.available:
            return
        img = tmp_path / "zh.png"
        truth = tmp_path / "zh.txt"
        _make_text_image("机器学习", img)
        truth.write_text("机器学习", encoding="utf-8")

        results = run_bakeoff([TESSERACT_CHI_SIM], load_fixtures(tmp_path))
        assert len(results) == 1
        r = results[0]
        if r.success:
            # The chi_sim model must not insert spaces between CJK glyphs;
            # naive eng+chi_sim interleaving would push CER to ~0.8+.
            assert r.cer is None or r.cer <= 0.5, f"chi_sim CER={r.cer}"

    def test_report_csv(self, tmp_path: Path) -> None:
        r = BakeoffResult(engine="test", fixture="f.png", file_size=100, success=True, cer=0.0)
        p = report_csv([r], tmp_path / "out.csv")
        rows = list(csv.DictReader(p.open(encoding="utf-8")))
        assert len(rows) == 1
        # A perfect CER of 0.0 is falsy but must not be blanked by `or ""`.
        assert rows[0]["cer"] == "0.0", rows[0]

    def test_report_csv_blank_when_no_truth(self, tmp_path: Path) -> None:
        r = BakeoffResult(engine="test", fixture="f.png", file_size=100, success=True)
        p = report_csv([r], tmp_path / "out2.csv")
        rows = list(csv.DictReader(p.open(encoding="utf-8")))
        assert len(rows) == 1
        assert rows[0]["cer"] == ""
        assert p.read_text(encoding="utf-8").startswith("engine,fixture")

    def test_report_json(self, tmp_path: Path) -> None:
        r = BakeoffResult(engine="test", fixture="f.png", file_size=100, success=True, cer=0.0)
        p = report_json([r], tmp_path / "out.json")
        assert '"cer": 0.0' in p.read_text(encoding="utf-8")
