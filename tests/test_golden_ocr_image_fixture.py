"""G0: the screenshot/image corpus entry must retain source bytes and OCR truth."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "golden" / "golden-screenshot-ocr.png"
MANIFEST = ROOT / "tests" / "fixtures" / "golden" / "manifest.json"


def test_golden_screenshot_fixture_has_project_owned_bytes_and_ocr_expectation() -> None:
    record = json.loads(MANIFEST.read_text(encoding="utf-8"))["fixtures"][FIXTURE.name]

    assert record["format"] == "image/png"
    assert record["rights_basis"] == "project-authored synthetic test fixture"
    assert record["privacy"] == "no personal data"
    assert record["expected"]["text"] == "OCR GOLDEN ANCHOR"
    assert record["expected"]["anchor"] == "image_region=full"
    assert record["expected"]["engine"] == "pytesseract+tesseract"
    assert record["expected"]["language"] == "eng"
    assert hashlib.sha256(FIXTURE.read_bytes()).hexdigest() == record["sha256"]
