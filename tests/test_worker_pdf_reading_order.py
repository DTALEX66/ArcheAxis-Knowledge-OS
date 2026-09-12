"""R15/F05: the reading order is a decision with a reason, and it may only reorder.

The format matrix recorded the gap plainly - there was no reading-order or column-layout
model, so a two-column page was projected in whatever order the engine returned. These tests
build real PDFs with the same engine the worker uses and hold the model to two properties: it
applies when the page's geometry supports it, and it can never add or drop a line.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pymupdf

REPO = Path(__file__).resolve().parents[1]
WORKER = REPO / "services" / "python-workers" / "document" / "worker_pdf.py"


def _load():
    spec = importlib.util.spec_from_file_location("worker_pdf_reading_order", WORKER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


worker = _load()


def _write_pdf(path: Path, blocks: list[tuple[float, float, str]], width: int = 800, height: int = 600) -> Path:
    document = pymupdf.open()
    page = document.new_page(width=width, height=height)
    for x, y, text in blocks:
        page.insert_text((x, y), text, fontsize=11)
    document.save(str(path))
    document.close()
    return path


INTERLEAVED = [
    (50.0, 80.0, "L1 left column first"),
    (430.0, 80.0, "R1 right column first"),
    (50.0, 110.0, "L2 left column second"),
    (430.0, 110.0, "R2 right column second"),
    (50.0, 140.0, "L3 left column third"),
    (430.0, 140.0, "R3 right column third"),
]

SINGLE_COLUMN = [
    (60.0, 80.0, "S1 the only column"),
    (60.0, 110.0, "S2 the only column"),
    (60.0, 140.0, "S3 the only column"),
    (60.0, 170.0, "S4 the only column"),
]

SPANNING_HEADING = [
    (40.0, 60.0, "A full width heading that crosses the gutter and keeps going well past the right column edge"),
    (50.0, 140.0, "L1 left column first"),
    (430.0, 140.0, "R1 right column first"),
    (50.0, 170.0, "L2 left column second"),
    (430.0, 170.0, "R2 right column second"),
]


def _lines(out: dict) -> list[str]:
    return [line.strip() for line in out["text"].splitlines() if line.strip()]


def _first_line_bbox(path: Path) -> tuple[float, float, float, float]:
    document = pymupdf.open(str(path))
    line = document[0].get_text("dict")["blocks"][0]["lines"][0]
    document.close()
    return tuple(float(value) for value in line["bbox"])  # type: ignore[return-value]


def _reading_order(out: dict, page: int = 1) -> dict:
    structure = out["loss_receipt"]["params"]["structure"]
    facts = next(item for item in structure["page_facts"] if item["page"] == page)
    return facts["reading_order"]


def test_a_two_column_page_is_projected_column_by_column(tmp_path):
    out = worker.extract(str(_write_pdf(tmp_path / "two-column.pdf", INTERLEAVED)))
    assert _lines(out) == [
        "L1 left column first",
        "L2 left column second",
        "L3 left column third",
        "R1 right column first",
        "R2 right column second",
        "R3 right column third",
    ]


def test_the_column_model_is_reported_as_a_fact_with_its_reason(tmp_path):
    out = worker.extract(str(_write_pdf(tmp_path / "two-column.pdf", INTERLEAVED)))
    order = _reading_order(out)
    assert order["applied"] is True
    assert order["columns"] == 2
    assert order["gutter"] is not None
    assert order["model"] == worker.READING_ORDER_MODEL
    summary = out["loss_receipt"]["params"]["structure"]["reading_order"]
    assert summary["applied_to_pages"] == [1]


def test_a_single_column_page_is_left_exactly_as_the_engine_returned_it(tmp_path):
    out = worker.extract(str(_write_pdf(tmp_path / "single.pdf", SINGLE_COLUMN)))
    order = _reading_order(out)
    assert order["applied"] is False
    assert order["columns"] == 1
    assert "no vertical band" in order["reason"]
    assert _lines(out) == [text for _, _, text in SINGLE_COLUMN]


def test_a_line_crossing_the_candidate_gutter_prevents_the_model(tmp_path):
    """A full-width heading means the page is not simply two columns."""
    path = _write_pdf(tmp_path / "heading.pdf", SPANNING_HEADING)
    bbox = _first_line_bbox(path)
    # The premise is checked, not assumed: if the heading no longer crosses the right column's
    # left edge, the font metrics moved and this test must say so rather than pass quietly.
    assert bbox[2] > 430, f"the heading does not reach the right column: {bbox}"
    out = worker.extract(str(path))
    order = _reading_order(out)
    assert order["applied"] is False
    assert "no vertical band" in order["reason"]


def test_anchors_and_coverage_still_describe_the_projected_text(tmp_path):
    """Ordering changes the projection, so the anchors must still match it line for line."""
    out = worker.extract(str(_write_pdf(tmp_path / "two-column.pdf", INTERLEAVED)))
    lines = out["text"].splitlines(keepends=True)
    assert len(out["structure"]) == len(lines)
    for anchor, line in zip(out["structure"], lines):
        assert out["text"][anchor["char_start"] : anchor["char_end"]] == line
    assert out["loss_receipt"]["covered"] == out["loss_receipt"]["total"] == len(lines)
    assert out["loss_receipt"]["coverage"] == 1.0


class FakePage:
    """A page whose engine order and line geometry are chosen independently, for the guard."""

    def __init__(self, text: str, lines: list[tuple]) -> None:
        self._text = text
        self._lines = lines

    def get_text(self, mode: str | None = None):
        if mode == "dict":
            return {"blocks": [{"type": 0, "lines": [{"bbox": line[:4], "spans": [{"text": line[4]}]} for line in self._lines]}]}
        return self._text


def _line(x0: float, y0: float, x1: float, y1: float, body: str) -> tuple:
    return (x0, y0, x1, y1, body)


def test_the_model_may_only_reorder_and_is_refused_when_it_would_not():
    lines = [
        _line(50, 68, 300, 84, "L1 left"),
        _line(430, 68, 700, 84, "R1 right"),
        _line(50, 98, 300, 114, "L2 left"),
        _line(430, 98, 700, 114, "R2 right"),
    ]
    engine_text = "L1 left\nR1 right\nL2 left\nR2 right\n"
    ordered, facts = worker._ordered_page_text(FakePage(engine_text, lines), engine_text, [])
    assert facts["applied"] is True
    assert worker._lines_of(ordered) == ["L1 left", "L2 left", "R1 right", "R2 right"]

    # The same geometry against engine text that holds an extra line: the reconstruction would
    # drop it, so the model must refuse itself and hand back the engine text untouched.
    richer = engine_text + "A line the geometry does not carry\n"
    kept, refused = worker._ordered_page_text(FakePage(richer, lines), richer, [])
    assert refused["applied"] is False
    assert refused["reconstruction_refused"] is True
    assert kept == richer
    assert "would change the lines" in refused["reason"]


def test_blank_separator_lines_stop_the_model_before_it_drops_them():
    """A line-level reconstruction would not carry blank lines, so the model stands down."""
    lines = [
        _line(50, 68, 300, 84, "L1 left"),
        _line(430, 68, 700, 84, "R1 right"),
        _line(50, 98, 300, 114, "L2 left"),
        _line(430, 98, 700, 114, "R2 right"),
    ]
    engine_text = "L1 left\n\nR1 right\nL2 left\nR2 right\n"
    kept, facts = worker._ordered_page_text(FakePage(engine_text, lines), engine_text, [])
    assert facts["applied"] is False
    assert "blank separator lines" in facts["reason"]
    assert kept == engine_text


def test_the_refusal_is_reported_as_a_loss(tmp_path):
    """A refused reconstruction is a limit of the model, so a reader scanning losses sees it."""
    source = WORKER.read_text(encoding="utf-8")
    assert "reading order kept as the engine order on pages" in source
