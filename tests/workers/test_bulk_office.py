"""BULK-0907 P10: Office worker bulk cases (worker_office.py real entry).

Uses project golden fixtures (docx/pptx/xlsx) with independent substring expectations
from tests/fixtures/golden/manifest.json, plus deterministic corrupt/absent inputs for
genuine failure cases. DOCX engine is pure stdlib ZIP/XML (worker_office._docx_text);
no python-docx dependency is involved.
"""

import importlib.util
import io
import json
import os
import tempfile
import unittest
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
OFFICE = ROOT / "services/python-workers/document/worker_office.py"
GOLDEN = ROOT / "tests/fixtures/golden"

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def _load_worker():
    spec = importlib.util.spec_from_file_location("worker_office", OFFICE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class OfficeBulkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.worker = _load_worker()
        cls.manifest = json.loads((GOLDEN / "manifest.json").read_text(encoding="utf-8"))

    def _tmp(self):
        return tempfile.TemporaryDirectory(dir=os.environ["ARCHEAXIS_RUN_ROOT"])

    def test_docx_golden_projects_text_and_paragraph_anchor(self):
        out = self.worker.extract(str(GOLDEN / "golden-docx-anchor.docx"))
        self.assertEqual(out["format"], "docx")
        self.assertIn("Document evidence anchor", out["text"])
        kinds = [a["kind"] for a in out["structure"]]
        self.assertIn("paragraph", kinds)
        paragraph = next(a for a in out["structure"] if a["kind"] == "paragraph")
        self.assertTrue(paragraph["path"][0].startswith("paragraph-"))
        self.assertLessEqual(paragraph["char_end"], len(out["text"]))

    def test_pptx_golden_projects_slide_anchor(self):
        out = self.worker.extract(str(GOLDEN / "golden-pptx-anchor.pptx"))
        self.assertEqual(out["format"], "pptx")
        self.assertIn("Slide evidence anchor", out["text"])
        slide = next(a for a in out["structure"] if a["kind"] == "slide")
        self.assertEqual(slide["path"][0], "slide-1")
        self.assertLessEqual(slide["char_end"], len(out["text"]))

    def test_xlsx_golden_projects_sheet_anchor(self):
        out = self.worker.extract(str(GOLDEN / "golden-xlsx-anchor.xlsx"))
        self.assertEqual(out["format"], "xlsx")
        self.assertIn("Sheet evidence anchor", out["text"])
        rows = [a for a in out["structure"] if a["kind"] == "sheet_row"]
        self.assertTrue(rows)
        self.assertTrue(rows[0]["path"][0].startswith("sheet-"))
        # formula cache is not presented as a live computation (data_only=False policy).
        self.assertIn("data_only=False", out["loss_receipt"]["loss_note"])

    def test_docx_without_body_is_rejected(self):
        with self._tmp() as tmp:
            root_xml = ET.Element(f"{{{W_NS}}}document")
            buffer = io.BytesIO()
            with zipfile.ZipFile(buffer, "w") as archive:
                archive.writestr("word/document.xml", ET.tostring(root_xml, encoding="unicode"))
            path = Path(tmp) / "no-body.docx"
            path.write_bytes(buffer.getvalue())
            with self.assertRaises(ValueError) as ctx:
                self.worker.extract(str(path))
            self.assertIn("no body", str(ctx.exception))

    def test_missing_file_and_wrong_suffix_are_rejected(self):
        with self._tmp() as tmp:
            missing = Path(tmp) / "absent.docx"
            with self.assertRaises(ValueError):
                self.worker.extract(str(missing))
            wrong = Path(tmp) / "plain.txt"
            wrong.write_text("not office", encoding="utf-8")
            with self.assertRaises(ValueError) as ctx:
                self.worker.extract(str(wrong))
            self.assertIn("unsupported", str(ctx.exception))

    def test_garbage_docx_bytes_are_rejected(self):
        with self._tmp() as tmp:
            path = Path(tmp) / "garbage.docx"
            path.write_bytes(b"\x50\x4b\x05\x06" + b"\x00" * 18)  # zip trailer without members
            with self.assertRaises(KeyError):
                self.worker.extract(str(path))


if __name__ == "__main__":
    unittest.main()
