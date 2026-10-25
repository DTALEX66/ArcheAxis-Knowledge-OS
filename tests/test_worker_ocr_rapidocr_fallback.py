"""F04: a machine without Tesseract still OCRs through the packaged RapidOCR fallback.

Tesseract remains the default when it is usable. When it is absent, `auto` must use
RapidOCR for the languages its PP-OCRv4 models actually serve, and must refuse other
languages by name instead of silently reading them with the wrong model.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
WORKER = REPO / "services" / "python-workers" / "vision" / "worker_ocr.py"


def _load():
    spec = importlib.util.spec_from_file_location("worker_ocr_rapidocr", WORKER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


worker = _load()
rapidocr = pytest.importorskip("rapidocr_onnxruntime", reason="RapidOCR fallback engine missing")
PIL_Image = pytest.importorskip("PIL.Image", reason="PIL required to build samples")
PIL_ImageDraw = pytest.importorskip("PIL.ImageDraw", reason="PIL required to build samples")
PIL_ImageFont = pytest.importorskip("PIL.ImageFont", reason="PIL required to build samples")


def _render(path: Path, line: str) -> None:
    image = PIL_Image.new("RGB", (520, 120), "white")
    draw = PIL_ImageDraw.Draw(image)
    draw.text((20, 40), line, fill="black", font=PIL_ImageFont.load_default(size=32))
    image.save(path)


def _without_tesseract(monkeypatch) -> None:
    def unavailable() -> str:
        raise RuntimeError("tesseract binary not found")

    monkeypatch.setattr(worker, "_tesseract", unavailable)


def test_auto_uses_rapidocr_when_tesseract_is_absent(tmp_path: Path, monkeypatch) -> None:
    _without_tesseract(monkeypatch)
    sample = tmp_path / "screenshot.png"
    _render(sample, "ArcheAxis 6371 km")

    result = worker.extract(sample, "eng", engine="auto")
    params = result["loss_receipt"]["params"]

    assert params["engine"] == "rapidocr"
    assert params["engine_version"], "the fallback engine identity must be recorded"
    assert params["fallback_reason"], "the absent Tesseract engine must be named"
    assert "6371" in result["text"], result["text"]
    assert params["reading_order"]["applied"] is False
    assert result["loss_receipt"]["coverage"] == 1.0
    assert result["loss_receipt"]["covered"] == result["loss_receipt"]["total"] > 0
    assert any("rapidocr fallback" in loss for loss in result["loss_receipt"]["losses"])


def test_explicit_rapidocr_runs_even_when_tesseract_is_present(tmp_path: Path, monkeypatch) -> None:
    sample = tmp_path / "screenshot.png"
    _render(sample, "ArcheAxis 6371 km")

    result = worker.extract(sample, "eng", engine="rapidocr")
    assert result["loss_receipt"]["params"]["engine"] == "rapidocr"
    assert result["loss_receipt"]["params"]["fallback_reason"] is None


def test_rapidocr_refuses_a_language_its_models_do_not_serve(tmp_path: Path, monkeypatch) -> None:
    _without_tesseract(monkeypatch)
    sample = tmp_path / "screenshot.png"
    _render(sample, "ArcheAxis 6371 km")

    with pytest.raises(RuntimeError, match="rapidocr cannot serve language 'deu'"):
        worker.extract(sample, "deu", engine="rapidocr")


def test_probe_keeps_tesseract_capability_but_reports_the_fallback(monkeypatch) -> None:
    _without_tesseract(monkeypatch)

    result = worker.probe("eng")
    assert result["capability"] is False, "the declared Tesseract engine is still absent"
    assert result["capability_any"] is True
    assert result["fallback"]["available"] is True
    assert result["fallback"]["supports_requested_language"] is True
