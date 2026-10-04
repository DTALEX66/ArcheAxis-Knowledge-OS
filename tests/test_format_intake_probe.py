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


def test_every_sample_was_attempted(receipt):
    assert {item["sample"] for item in receipt["items"]} == {"note.md", "board.canvas", "picture.png"}


def test_every_item_carries_an_outcome_and_its_evidence(receipt):
    for item in receipt["items"]:
        assert item["outcome"], item["sample"]
        assert item["evidence"].strip(), item["sample"]


def test_a_successful_intake_preserves_the_original_hash(receipt):
    for item in receipt["items"]:
        if item["status"] == 200:
            assert item["sha256_matches_source"] is True, item["sample"]


def test_a_successful_intake_reports_the_expected_format(receipt):
    for item in receipt["items"]:
        if item["status"] == 200:
            assert item["format"] == item["expected_format"], item["sample"]


def test_nothing_is_called_structured_without_naming_structure(receipt):
    """The rule that keeps "transported" from becoming "supported" by inattention."""
    for item in receipt["items"]:
        if item["outcome"] == "structured":
            assert any(marker in item["evidence"].lower()
                       for marker in ("blocks", "nodes", "sections", "headings", "outline", "pages")), item["sample"]


# What the three formats actually did on 2026-10-04, at commit df221d5e and its successor.
# Pinned on purpose: see the module docstring.
EXPECTED_OUTCOMES = {
    "note.md": "carried_passthrough",
    "board.canvas": "custody_only",
    "picture.png": "engine_missing",
}


def test_the_recorded_outcomes_are_the_ones_measured(receipt):
    seen = {name: item["outcome"] for name, item in by_sample(receipt).items()}
    assert seen == EXPECTED_OUTCOMES


def test_the_engine_missing_evidence_names_what_is_missing(receipt):
    item = by_sample(receipt)["picture.png"]
    lowered = item["evidence"].lower()
    assert "tesseract" in lowered or "pytesseract" in lowered
