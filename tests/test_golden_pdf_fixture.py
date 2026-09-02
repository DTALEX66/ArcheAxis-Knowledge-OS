"""G0: the generated PDF corpus entry must have committed original bytes."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from tests.golden_pdf_fixture import GOLDEN_PDF, GOLDEN_PDF_SHA256


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "golden" / "golden-journey-evidence.pdf"
MANIFEST = ROOT / "tests" / "fixtures" / "golden" / "manifest.json"


def test_golden_pdf_fixture_has_project_owned_raw_bytes_and_integrity_metadata() -> None:
    record = json.loads(MANIFEST.read_text(encoding="utf-8"))["fixtures"][FIXTURE.name]

    assert record["format"] == "pdf"
    assert record["rights_basis"] == "project-authored synthetic test fixture"
    assert record["privacy"] == "no personal data"
    assert FIXTURE.read_bytes() == GOLDEN_PDF
    assert record["sha256"] == GOLDEN_PDF_SHA256
    assert hashlib.sha256(FIXTURE.read_bytes()).hexdigest() == record["sha256"]
