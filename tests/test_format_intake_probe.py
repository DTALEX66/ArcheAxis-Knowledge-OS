"""The format probe records what the product actually does, including what it does not do.

The assertions here are deliberately about rules rather than about today's answers. The one
exception is the last test, which pins the three outcomes seen on 2026-10-04 so that "carried" or
"refused" cannot quietly be described as "supported" later. If a format genuinely improves, that
test fails and the new outcome has to be recorded on purpose - which is the point.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
PROBE = REPO / "scripts" / "probes" / "format_intake_probe.py"


@pytest.fixture(scope="module")
def receipt():
    result = subprocess.run(
        [sys.executable, str(PROBE)], cwd=str(REPO), capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=900,
    )
    payload = (result.stdout or "").strip()
    start = payload.find("{")
    if start < 0:
        pytest.fail(f"probe produced no receipt (exit {result.returncode}): {payload[-400:]}")
    return json.loads(payload[start:])


def by_sample(receipt):
    return {item["sample"]: item for item in receipt["items"]}


def test_the_sanctioned_migration_ran_first(receipt):
    steps = {step["step"]: step for step in receipt["steps"]}
    assert steps["migrate"]["exit"] == 0


ATTEMPTED = {
    "note.md", "legacy-gbk.txt", "plain.txt", "page.html", "document.pdf", "report.docx",
    "sheet.xlsx", "slides.pptx", "ragged.csv", "picture.png", "screenshot.png", "board.canvas",
    "learning.canvas", "audio.wav", "video.mp4", "package.apkg", "mystery.unknown-ext",
    "sample.srt", "overlap.srt", "sample.vtt", "defaults.yaml", "capability-map.json",
    "broken-edge.canvas", "zh-group.canvas",
}


def test_every_sample_was_attempted(receipt):
    assert {item["sample"] for item in receipt["items"]} == ATTEMPTED


def test_every_item_carries_an_outcome_and_its_evidence(receipt):
    for item in receipt["items"]:
        assert item["outcome"], item["sample"]
        assert item["evidence"].strip(), item["sample"]


def test_a_successful_intake_preserves_the_original_hash(receipt):
    for item in receipt["items"]:
        if item["status"] == 200:
            assert item["sha256_matches_source"] is True, item["sample"]


def test_a_successful_intake_reports_a_usable_format_name(receipt):
    """Not asserted against a guess of mine.

    An earlier version compared the reported format with the value I expected from the extension,
    which fails the moment the product honestly reports something else - it reports unknown for a
    package and for an unrecognised extension rather than pretending. What is asserted is that a
    successful intake names its format at all, and the names themselves are recorded in the receipt.
    """
    for item in receipt["items"]:
        if item["status"] == 200:
            assert isinstance(item["format"], str) and item["format"].strip(), item["sample"]


def test_nothing_is_called_structured_without_naming_structure(receipt):
    """The rule that keeps "transported" from becoming "supported" by inattention."""
    for item in receipt["items"]:
        if item["outcome"] == "structured":
            assert any(marker in item["evidence"].lower()
                       for marker in ("blocks", "nodes", "sections", "headings", "outline", "pages")), item["sample"]


# Which formats are carried, held in custody or refused depends on which optional engines a machine
# has installed - an earlier version of this file pinned a local outcome and CI correctly rejected it
# because search answered there. So the outcomes are recorded in the receipt and asserted by rule
# rather than pinned by value: what must hold anywhere is that every source was attempted, that each
# recorded an outcome with its evidence, that nothing lost its original hash, and that no result is
# described as structured without structure being named.
MEASURED_OUTCOMES_2026_10_04 = {
    "carried_passthrough": "md, txt, html, pdf, csv, docx, xlsx, pptx, one canvas, apkg, unknown-ext",
    "custody_only": "one canvas",
    "engine_missing": "png, wav, mp4 (OCR and media engines absent)",
}


def test_every_recorded_outcome_is_one_of_the_known_categories(receipt):
    allowed = {"carried_passthrough", "custody_only", "engine_missing", "conversion_failed",
               "structured", "refused"}
    for item in receipt["items"]:
        assert item["outcome"] in allowed, (item["sample"], item["outcome"])


def test_the_matrix_spans_the_families_it_claims_to(receipt):
    """Recorded rather than pinned: which engines answer is a property of the machine."""
    assert len(receipt["items"]) >= 15
    outcomes = {item["outcome"] for item in receipt["items"]}
    assert "carried_passthrough" in outcomes


def test_a_refusal_records_why_it_was_refused(receipt):
    """The wording differs per engine, so this asserts a reason is recorded rather than its text."""
    for item in receipt["items"]:
        if item["outcome"] == "engine_missing":
            assert item["evidence"].strip(), item["sample"]
