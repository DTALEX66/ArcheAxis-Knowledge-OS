"""R08: native PDF extraction shares the text worker's contract, carries
page+line anchors, and degrades explicitly (corrupt -> failure, no text -> OCR
note) instead of reporting an empty success or a model confidence as accuracy.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

WORKER = Path(__file__).resolve().parents[1] / "services" / "python-workers" / "document" / "worker_pdf.py"

fitz = pytest.importorskip("fitz", reason="native PDF engine required for the PDF route")


def _load():
    spec = importlib.util.spec_from_file_location("worker_pdf_under_test", WORKER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


worker = _load()


def _make_pdf(path: Path, pages: list[str]) -> None:
    doc = fitz.open()
    for body in pages:
        page = doc.new_page()
        page.insert_text((72, 100), body)
    doc.save(path)
    doc.close()


def test_native_extraction_returns_text_anchors_and_receipt(tmp_path: Path) -> None:
    pdf = tmp_path / "native.pdf"
    _make_pdf(pdf, ["Einstein radius 6371 km measured.", "Second page notes."])
    result = worker.extract(str(pdf))
    assert result["engine"] == worker.ENGINE
    assert "6371" in result["text"], "numbers must survive extraction"
    assert "km" in result["text"], "units must survive extraction"
    assert result["structure"], "page/line anchors are required"
    first = result["structure"][0]
    assert first["kind"] == "line"
    assert first["path"][0].startswith("page-"), first["path"]
    # Anchor offsets must address the projected text exactly.
    slice_text = result["text"][first["char_start"]:first["char_end"]]
    assert slice_text.strip() != "", "an anchor must point at real text"
    assert 0 <= first["char_start"] < first["char_end"] <= len(result["text"])
    receipt = result["loss_receipt"]
    assert receipt["engine"] == worker.ENGINE
    # Coverage is line-based (the same unit as the anchors) and supplied together
    # with covered/total; every line of this sample is anchored.
    assert receipt["params"]["pages"] == 2
    assert receipt["covered"] == receipt["total"] > 0
    assert receipt["coverage"] == 1.0
    assert "accuracy" not in json.dumps(receipt).lower(), "no accuracy claim may be fabricated"


def test_every_page_is_addressable(tmp_path: Path) -> None:
    pdf = tmp_path / "two-pages.pdf"
    _make_pdf(pdf, ["Alpha page one.", "Beta page two."])
    result = worker.extract(str(pdf))
    pages = {anchor["path"][0] for anchor in result["structure"]}
    assert {"page-1", "page-2"} <= pages, pages


def test_pdf_without_extractable_text_degrades_to_an_ocr_note(tmp_path: Path) -> None:
    pdf = tmp_path / "scan-like.pdf"
    _make_pdf(pdf, [""])  # a page with no text: what a scan or screenshot looks like
    result = worker.extract(str(pdf))
    assert result["text"].strip() == "", "no text may be invented"
    assert any("OCR" in loss for loss in result["loss_receipt"]["losses"]), result["loss_receipt"]
    # No lines exist in the projected text, so there is nothing to anchor: the
    # receipt says so instead of claiming partial coverage of a page.
    assert result["loss_receipt"]["covered"] == 0
    assert result["loss_receipt"]["total"] == 0
    assert result["loss_receipt"]["coverage"] == 1.0
    assert result["loss_receipt"]["params"]["pages_without_text"] == [1]


def test_corrupt_pdf_fails_explicitly(tmp_path: Path) -> None:
    pdf = tmp_path / "corrupt.pdf"
    pdf.write_bytes(b"%PDF-1.4\nthis is not a real pdf\n")
    with pytest.raises(ValueError):
        worker.extract(str(pdf))


def test_cli_reports_failure_with_a_non_zero_exit(tmp_path: Path) -> None:
    pdf = tmp_path / "corrupt-cli.pdf"
    pdf.write_bytes(b"not a pdf at all")
    proc = subprocess.run(
        [sys.executable, str(WORKER), str(pdf)],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    # A dependency may print warnings to stdout before our JSON; the worker's own
    # line is the last one, so parse that rather than assuming a clean stream.
    payload = json.loads(proc.stdout.strip().splitlines()[-1])
    assert proc.returncode == 1
    assert "error" in payload
    assert payload["engine"] == worker.ENGINE
    assert "text" not in payload, "a failed extraction must not publish text"
