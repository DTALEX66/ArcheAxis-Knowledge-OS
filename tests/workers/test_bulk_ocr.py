"""BULK-0907 P13: local OCR reproducible small samples (vision/worker_ocr.py).

Runs the system Tesseract over the project golden screenshot and a synthetic
white image, using the public profile-free path with a working TESSDATA_PREFIX
(eng/chi_sim present under the shared toolchain tessdata). If OCR is not
probe-capable in the current environment the group is SKIPPED with a clear
reason (never a fake pass). Text recognition and diagram semantics are separate
lanes; assertions stay at substring/word level, not full-document accuracy.
"""

import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OCR = ROOT / "services/python-workers/vision/worker_ocr.py"
GOLDEN = ROOT / "tests/fixtures/golden/golden-screenshot-ocr.png"


def _load_worker():
    spec = importlib.util.spec_from_file_location("worker_ocr", OCR)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _probe(worker) -> dict:
    return worker.probe(lang="eng")


class OcrBulkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.worker = _load_worker()
        cls.capable = _probe(cls.worker).get("capability") is True

    def _skip_if_no_ocr(self):
        if not self.capable:
            self.skipTest("tesseract not probe-capable in this environment (TESSDATA_PREFIX)")

    def test_eng_probe_reports_capability_and_languages(self):
        if not self.capable:
            self.skipTest("tesseract not probe-capable in this environment")
        probe = _probe(self.worker)
        self.assertTrue(probe["capability"])
        self.assertIn("eng", probe["languages"])

    def test_golden_ocr_substring_words(self):
        self._skip_if_no_ocr()
        out = self.worker.extract(Path(GOLDEN), lang="eng")
        self.assertIn("GOLDEN", out["text"])
        self.assertTrue(out["words"])
        self.assertTrue(any("GOLDEN" in word["text"] for word in out["words"]))

    def test_white_image_yields_empty_ocr_not_error(self):
        self._skip_if_no_ocr()
        with tempfile.TemporaryDirectory(dir=os.environ["ARCHEAXIS_RUN_ROOT"]) as tmp:
            image = Path(tmp) / "white.png"
            code = f"from PIL import Image; Image.new('RGB',(120,40),'white').save(r'{image.as_posix()}')"
            subprocess.run(
                [sys.executable, "-c", code],
                check=True, capture_output=True,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            out = self.worker.extract(image, lang="eng")
        self.assertEqual(out["text"], "")
        self.assertEqual(out["words"], [])

    def test_unsupported_extension_is_rejected(self):
        self._skip_if_no_ocr()
        with tempfile.TemporaryDirectory(dir=os.environ["ARCHEAXIS_RUN_ROOT"]) as tmp:
            bad = Path(tmp) / "sample.txt"
            bad.write_text("x", encoding="utf-8")
            with self.assertRaises(ValueError):
                self.worker.extract(bad, lang="eng")


if __name__ == "__main__":
    unittest.main()
