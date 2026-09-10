"""R15/F05-F06: the PDF route reports the structure the engine really exposes.

The projection stays canonical - text plus page/line anchors, coverage over lines -
and what the page actually contains beyond its text (engine text blocks with their
boxes, image references, tables the engine's own finder detects, per-page character
counts) is reported as facts in `loss_receipt.params.structure`.

The samples are built here with PyMuPDF, so nothing private is involved, and every
fact asserted is read back from the sample that was just written:

  * two text blocks are two blocks, with their first lines;
  * an inserted image is an image reference;
  * a ruled grid is detected as a table when the engine can detect tables at all, and
    when it cannot, the fact says `table_support: false` with zero tables instead of
    implying nobody looked;
  * a page with no text is still named as needing OCR, now with per-page character
    counts to show which pages those are.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

pytest.importorskip("pymupdf", reason="PyMuPDF is the native PDF engine under test")
import pymupdf  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
WORKER = REPO / "services" / "python-workers" / "document" / "worker_pdf.py"


def _load():
    spec = importlib.util.spec_from_file_location("worker_pdf_structure", WORKER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


worker = _load()


def _two_paragraph_pdf(path: Path, image: bool = False) -> None:
    document = pymupdf.open()
    page = document.new_page()
    page.insert_text((72, 100), "First measured block about 6371 km.", fontsize=12)
    page.insert_text((72, 200), "Second block, separated from the first.", fontsize=12)
    if image:
        pixmap = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 16, 16))
        pixmap.set_rect(pixmap.irect, (200, 30, 30))
        page.insert_image(pymupdf.Rect(300, 300, 340, 340), pixmap=pixmap)
    document.save(str(path))
    document.close()


def _ruled_table_pdf(path: Path) -> None:
    document = pymupdf.open()
    page = document.new_page()
    for x in (72, 172, 272):
        page.draw_line(pymupdf.Point(x, 100), pymupdf.Point(x, 160))
    for y in (100, 130, 160):
        page.draw_line(pymupdf.Point(72, y), pymupdf.Point(272, y))
    page.insert_text((80, 118), "name", fontsize=11)
    page.insert_text((180, 118), "qty", fontsize=11)
    page.insert_text((80, 148), "bolt", fontsize=11)
    page.insert_text((180, 148), "4", fontsize=11)
    document.save(str(path))
    document.close()


def _structure(result: dict) -> dict:
    return result["loss_receipt"]["params"]["structure"]


def test_two_text_blocks_are_reported_as_two_blocks(tmp_path: Path):
    sample = tmp_path / "two.pdf"
    _two_paragraph_pdf(sample)
    result = worker.extract(str(sample))
    structure = _structure(result)

    assert structure["text_block_count"] == 2
    first_lines = [block["first_line"] for block in structure["text_blocks"]]
    assert any("First measured block" in line for line in first_lines), first_lines
    assert any("Second block" in line for line in first_lines), first_lines
    for block in structure["text_blocks"]:
        assert block["page"] == 1
        assert len(block["bbox"]) == 4
        assert block["chars"] > 0
    # the blocks are engine blocks, and the receipt says so rather than calling them
    # linguistic paragraphs
    assert "not a linguistic paragraph" in structure["block_meaning"]


def test_the_projection_stays_canonical_page_line_anchors(tmp_path: Path):
    sample = tmp_path / "two.pdf"
    _two_paragraph_pdf(sample)
    result = worker.extract(str(sample))
    text = result["text"]
    assert "6371" in text
    anchors = result["structure"]
    assert anchors and all(anchor["kind"] == "line" for anchor in anchors)
    assert all(anchor["path"][0] == "page-1" for anchor in anchors)
    assert all(anchor["path"][1].startswith("line-") for anchor in anchors)
    assert anchors[-1]["char_end"] == len(text)
    receipt = result["loss_receipt"]
    assert receipt["covered"] == receipt["total"] == len(anchors)
    assert receipt["coverage"] == 1.0
    assert "accuracy" not in str(receipt).lower()


def test_page_facts_carry_character_counts_and_zero_image_references(tmp_path: Path):
    sample = tmp_path / "two.pdf"
    _two_paragraph_pdf(sample)
    result = worker.extract(str(sample))
    structure = _structure(result)
    pages = structure["page_facts"]
    assert [page["page"] for page in pages] == [1]
    assert pages[0]["chars"] == len(result["text"])
    assert pages[0]["image_references"] == 0
    assert structure["image_reference_count"] == 0


def test_an_inserted_image_becomes_an_image_reference(tmp_path: Path):
    sample = tmp_path / "image.pdf"
    _two_paragraph_pdf(sample, image=True)
    result = worker.extract(str(sample))
    structure = _structure(result)
    assert structure["image_reference_count"] >= 1
    assert structure["page_facts"][0]["image_references"] >= 1


def test_a_ruled_grid_is_reported_honestly_either_way(tmp_path: Path):
    sample = tmp_path / "table.pdf"
    _ruled_table_pdf(sample)
    result = worker.extract(str(sample))
    structure = _structure(result)
    if structure["table_support"]:
        # the sample is a ruled 2x2 grid, so a finder that works should see one
        assert structure["table_count"] >= 1, structure["tables"]
        assert structure["tables"][0]["rows"] >= 2 and structure["tables"][0]["cols"] >= 2
        assert "not a guarantee" in structure["table_detection"]
    else:
        # no finder in this engine version: say so instead of implying a search
        assert structure["table_count"] == 0
        assert structure["tables"] == []


def test_a_page_without_text_is_named_and_counted(tmp_path: Path):
    sample = tmp_path / "scan.pdf"
    document = pymupdf.open()
    page = document.new_page()
    pixmap = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 32, 32))
    pixmap.set_rect(pixmap.irect, (10, 10, 10))
    page.insert_image(pymupdf.Rect(72, 72, 300, 300), pixmap=pixmap)
    document.save(str(sample))
    document.close()

    result = worker.extract(str(sample))
    structure = _structure(result)
    assert result["text"].strip() == ""
    assert result["loss_receipt"]["params"]["pages_without_text"] == [1]
    assert structure["page_facts"][0]["chars"] == 0
    assert any("OCR" in loss for loss in result["loss_receipt"]["losses"])


def test_a_corrupt_pdf_still_fails_loudly(tmp_path: Path):
    sample = tmp_path / "broken.pdf"
    sample.write_bytes(b"%PDF-1.4 not really a document")
    with pytest.raises(ValueError):
        worker.extract(str(sample))


def test_engine_chatter_never_reaches_stdout(tmp_path: Path):
    """The stdio protocol is one JSON envelope per line: engine prints must not leak.

    PyMuPDF prints a layout hint on first table use, which broke the Core's
    end-to-end PDF job with 'unexpected trailing worker output'. The text is now
    captured into the receipt instead.
    """
    import json
    import subprocess
    import sys

    sample = tmp_path / "table.pdf"
    _ruled_table_pdf(sample)
    result = subprocess.run(
        [sys.executable, "-X", "utf8", str(WORKER), str(sample)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert result.returncode == 0, result.stderr
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    assert len(lines) == 1, f"stdout must be exactly one envelope, got {len(lines)}: {lines[:3]}"
    payload = json.loads(lines[0])
    assert payload["engine"] == worker.ENGINE
    assert "loss_receipt" in payload

    structure = payload["loss_receipt"]["params"]["structure"]
    assert "engine chatter is captured" in structure["engine_message_policy"]
    # if this engine version printed a hint, it is recorded rather than lost
    if structure["engine_messages"]:
        assert any("diverted from stdout" in loss for loss in payload["loss_receipt"]["losses"])
