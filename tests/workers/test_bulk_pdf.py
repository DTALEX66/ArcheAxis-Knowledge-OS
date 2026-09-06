"""BULK-0907 P11: PDF page-type and loss cases (worker_office._pdf_text, PyMuPDF).

Synthetic PDFs are built in the run root with PyMuPDF (text page, image-only page,
rotated page). Per-page text extraction, per-page anchors, scanned-page reporting and
the corrupt-input failure contract are asserted with independent expectations.
Synthetic text pages use ASCII because PyMuPDF's default base-14 font has no CJK
glyphs (CJK coverage is exercised elsewhere via HTML/Office fixtures). No
unauthorized real PDFs are used.
"""

import importlib.util
import io
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OFFICE = ROOT / "services/python-workers/document/worker_office.py"


def _load_worker():
    spec = importlib.util.spec_from_file_location("worker_office", OFFICE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PdfBulkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.worker = _load_worker()
        import pymupdf as fitz
        cls.fitz = fitz

    def _build(self, tmp: Path, pages: list, rotation: int = 0) -> Path:
        fitz = self.fitz
        document = fitz.open()
        for page_spec in pages:
            page = document.new_page()
            if rotation:
                page.set_rotation(rotation)
            if page_spec:
                page.insert_text((72, 72), page_spec, fontsize=12)
        path = tmp / "synthetic.pdf"
        document.save(str(path))
        document.close()
        return path

    def test_two_text_pages_produce_per_page_anchors(self):
        with tempfile.TemporaryDirectory(dir=os.environ["ARCHEAXIS_RUN_ROOT"]) as tmp:
            path = self._build(Path(tmp), ["Page One Alpha", "Page Two Beta"])
            out = self.worker.extract(str(path))
        self.assertEqual(out["format"], "pdf")
        self.assertIn("Page One Alpha", out["text"])
        self.assertIn("Page Two Beta", out["text"])
        self.assertEqual([a["path"] for a in out["structure"]], [["page-1"], ["page-2"]])
        self.assertGreater(out["structure"][1]["char_start"], out["structure"][0]["char_start"])
        self.assertEqual(out["loss_receipt"]["params"]["scanned_pages_no_text_layer"], 0)

    def test_rotated_text_page_is_still_extracted(self):
        with tempfile.TemporaryDirectory(dir=os.environ["ARCHEAXIS_RUN_ROOT"]) as tmp:
            path = self._build(Path(tmp), ["Rotated Text Line"], rotation=90)
            out = self.worker.extract(str(path))
        self.assertIn("Rotated Text Line", out["text"])

    def test_image_only_page_is_reported_as_scanned_not_fabricated(self):
        from PIL import Image

        fitz = self.fitz
        document = fitz.open()
        text_page = document.new_page()
        text_page.insert_text((72, 72), "Visible Text Page", fontsize=12)
        image_page = document.new_page()
        stream = io.BytesIO()
        Image.new("RGB", (60, 30), "white").save(stream, format="PNG")
        image_page.insert_image(fitz.Rect(50, 50, 110, 80), stream=stream.getvalue())
        with tempfile.TemporaryDirectory(dir=os.environ["ARCHEAXIS_RUN_ROOT"]) as tmp:
            path = Path(tmp) / "mixed.pdf"
            document.save(str(path))
            document.close()
            out = self.worker.extract(str(path))
        self.assertEqual(len(out["structure"]), 1)  # only the text page is anchored
        self.assertEqual(out["structure"][0]["path"], ["page-1"])
        self.assertEqual(out["loss_receipt"]["params"]["scanned_pages_no_text_layer"], 1)

    def test_corrupt_pdf_bytes_fail_at_the_real_main_boundary(self):
        with tempfile.TemporaryDirectory(dir=os.environ["ARCHEAXIS_RUN_ROOT"]) as tmp:
            path = Path(tmp) / "corrupt.pdf"
            path.write_bytes(b"not a pdf at all " + b"\x00" * 32)
            result = subprocess.run(
                [sys.executable, "-B", str(OFFICE), str(path)],
                capture_output=True, text=True, encoding="utf-8", timeout=60,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        self.assertEqual(result.returncode, 1)
        self.assertIn('"error"', result.stdout)


if __name__ == "__main__":
    unittest.main()
