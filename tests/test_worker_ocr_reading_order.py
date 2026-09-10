"""R15/F04: the OCR reading order is decided from the word boxes, and it may only reorder.

The image row's gap said it plainly - reading order exists only as line order. The route runs
Tesseract in single-block mode, so a visual row of two columns comes back as one line and the
projection interleaves the columns; that is measured here, not assumed. These tests hold the
model to its two properties: it applies when the word boxes support it, and it can never add or
drop a word.
"""

from __future__ import annotations

import importlib.util
import shutil
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
WORKER = REPO / "services" / "python-workers" / "vision" / "worker_ocr.py"
TESSDATA = REPO / "tools" / "tesseract" / "tessdata"

pytestmark = pytest.mark.skipif(
    shutil.which("tesseract") is None or not (TESSDATA / "eng.traineddata").is_file(),
    reason="tesseract binary or repository eng.traineddata unavailable",
)


def _load():
    spec = importlib.util.spec_from_file_location("worker_ocr_reading_order", WORKER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


worker = _load()


def _two_column_image(path: Path) -> Path:
    from PIL import Image, ImageDraw, ImageFont

    image = Image.new("RGB", (1200, 560), "white")
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default(size=44)
    rows = [("LEFT FIRST", "RIGHT FIRST"), ("LEFT SECOND", "RIGHT SECOND"), ("LEFT THIRD", "RIGHT THIRD")]
    for index, (left, right) in enumerate(rows):
        y = 70 + index * 130
        draw.text((60, y), left, fill="black", font=font)
        draw.text((680, y), right, fill="black", font=font)
    image.save(path)
    return path


def _single_column_image(path: Path) -> Path:
    from PIL import Image, ImageDraw, ImageFont

    image = Image.new("RGB", (700, 460), "white")
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default(size=44)
    for index, text in enumerate(["ALPHA ONE", "ALPHA TWO", "ALPHA THREE"]):
        draw.text((60, 70 + index * 120), text, fill="black", font=font)
    image.save(path)
    return path


def _lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


def _order(out: dict) -> dict:
    return out["loss_receipt"]["params"]["reading_order"]


def test_a_two_column_image_is_recognised_column_by_column(tmp_path):
    out = worker.extract(_two_column_image(tmp_path / "two-column.png"), "eng", TESSDATA)
    assert _lines(out["text"]) == [
        "LEFT FIRST",
        "LEFT SECOND",
        "LEFT THIRD",
        "RIGHT FIRST",
        "RIGHT SECOND",
        "RIGHT THIRD",
    ]


def test_the_engine_would_have_interleaved_the_columns(tmp_path):
    """The premise of the whole model, measured through the engine rather than assumed."""
    import subprocess

    image = _two_column_image(tmp_path / "two-column.png")
    engine = subprocess.run(
        [shutil.which("tesseract"), str(image), "stdout", "-l", "eng", "--psm", "6", "--tessdata-dir", str(TESSDATA)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert _lines(engine.stdout)[1] == "LEFT SECOND RIGHT SECOND", engine.stdout
    out = worker.extract(image, "eng", TESSDATA)
    assert _order(out)["differs_from_engine_order"] is True


def test_the_reading_order_is_reported_as_a_fact_with_its_reason(tmp_path):
    out = worker.extract(_two_column_image(tmp_path / "two-column.png"), "eng", TESSDATA)
    order = _order(out)
    assert order["applied"] is True
    assert order["columns"] == 2
    assert order["gutter"] is not None
    assert order["model"] == worker.READING_ORDER_MODEL
    assert "gutter with words on both sides" in order["reason"]
    assert order["rows_grouped_by"].startswith("overlapping vertical extent")


def test_the_review_regions_follow_the_reading_order(tmp_path):
    """A review list in the engine's order would send a human across the page and back."""
    out = worker.extract(_two_column_image(tmp_path / "two-column.png"), "eng", TESSDATA)
    regions = out["loss_receipt"]["params"]["regions"]
    assert [region["text"] for region in regions[:4]] == ["LEFT", "FIRST", "LEFT", "SECOND"]
    first_right = next(region for region in regions if region["text"] == "RIGHT")
    assert first_right["bbox"]["x"] > 600


def test_a_single_column_image_is_left_exactly_as_the_engine_returned_it(tmp_path):
    out = worker.extract(_single_column_image(tmp_path / "single.png"), "eng", TESSDATA)
    order = _order(out)
    assert order["applied"] is False
    assert order["columns"] == 1
    assert "no vertical band" in order["reason"]
    assert _lines(out["text"]) == ["ALPHA ONE", "ALPHA TWO", "ALPHA THREE"]


def test_anchors_still_describe_the_projected_text(tmp_path):
    out = worker.extract(_two_column_image(tmp_path / "two-column.png"), "eng", TESSDATA)
    lines = out["text"].splitlines(keepends=True)
    assert len(out["structure"]) == len(lines)
    for anchor, line in zip(out["structure"], lines):
        assert out["text"][anchor["char_start"] : anchor["char_end"]] == line
    assert out["loss_receipt"]["covered"] == out["loss_receipt"]["total"] == len(lines)


def _word(text: str, x: float, y: float, w: float = 90, h: float = 30) -> dict:
    return {"text": text, "confidence": 95.0, "x": x, "y": y, "w": w, "h": h, "block": "1", "par": "1", "line": "1"}


def test_the_model_may_only_reorder_and_is_refused_when_it_would_not():
    words = [
        _word("LEFT", 60, 80),
        _word("FIRST", 170, 80),
        _word("RIGHT", 680, 80),
        _word("FIRST", 800, 80),
        _word("LEFT", 60, 200),
        _word("SECOND", 170, 200),
        _word("RIGHT", 680, 200),
        _word("SECOND", 800, 200),
    ]
    engine = "LEFT FIRST RIGHT FIRST\nLEFT SECOND RIGHT SECOND\n"
    text, facts, ordered = worker._reading_order(words, engine)
    assert facts["applied"] is True
    assert _lines(text) == ["LEFT FIRST", "LEFT SECOND", "RIGHT FIRST", "RIGHT SECOND"]
    assert [word["text"] for word in ordered[:4]] == ["LEFT", "FIRST", "LEFT", "SECOND"]

    # Engine text carrying a word the word boxes do not: the reconstruction would lose it.
    richer = engine + "A WORD THE BOXES DO NOT CARRY\n"
    kept, refused, kept_words = worker._reading_order(words, richer)
    assert refused["applied"] is False
    assert refused["reconstruction_refused"] is True
    assert kept == richer
    assert kept_words == words


def test_a_one_pixel_baseline_difference_does_not_reorder_a_row():
    """Measured defect: sorting a row by (y, x) turned "LEFT SECOND" into "SECOND LEFT"."""
    words = [
        _word("LEFT", 60, 213, h=30),
        _word("SECOND", 174, 212, w=170, h=32),
        _word("RIGHT", 684, 213),
        _word("SECOND", 820, 212, w=170, h=32),
    ]
    engine = "LEFT SECOND RIGHT SECOND\n"
    text, facts, _ = worker._reading_order(words, engine)
    assert facts["applied"] is True
    assert _lines(text) == ["LEFT SECOND", "RIGHT SECOND"]


def test_too_few_word_boxes_means_no_layout_is_inferred():
    words = [_word("ONLY", 60, 80, w=90), _word("TWO", 170, 80), _word("WORDS", 260, 80)]
    text, facts, ordered = worker._reading_order(words, "ONLY TWO WORDS\n")
    assert facts["applied"] is False
    assert "fewer than four word boxes" in facts["reason"]
    assert text == "ONLY TWO WORDS\n"
    assert ordered == words
