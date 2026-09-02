"""G0: Tier-A text, web and Office fixtures must be project-owned and hashed."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GOLDEN = ROOT / "tests" / "fixtures" / "golden"
MANIFEST = GOLDEN / "manifest.json"


def test_golden_tier_a_text_web_and_office_fixtures_have_owned_bytes_and_anchor_truth() -> None:
    records = json.loads(MANIFEST.read_text(encoding="utf-8"))["fixtures"]
    expectations = {
        "golden-text-anchor.txt": ("text/plain", "Plaintext evidence anchor", "line_number=1"),
        "golden-web-anchor.html": ("text/html", "Web evidence anchor", "source=main-content"),
        "golden-docx-anchor.docx": ("application/vnd.openxmlformats-officedocument.wordprocessingml.document", "Document evidence anchor", "source_md=# Document evidence anchor"),
        "golden-pptx-anchor.pptx": ("application/vnd.openxmlformats-officedocument.presentationml.presentation", "Slide evidence anchor", "slide_number=1"),
        "golden-xlsx-anchor.xlsx": ("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "Sheet evidence anchor", "sheet=Evidence"),
    }

    for name, (format_name, expected_text, anchor) in expectations.items():
        fixture = GOLDEN / name
        record = records[name]
        assert record["format"] == format_name
        assert record["rights_basis"] == "project-authored synthetic test fixture"
        assert record["privacy"] == "no personal data"
        assert record["expected"]["text"] == expected_text
        assert record["expected"]["anchor"] == anchor
        assert hashlib.sha256(fixture.read_bytes()).hexdigest() == record["sha256"]
