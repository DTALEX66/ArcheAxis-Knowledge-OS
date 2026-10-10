"""A precise position must not be reported as returning when it does not, and loss must be shown.

These assertions are about rules. The one pinned value is the pair of outcomes measured on
2026-10-04: the read projection returns only page and source format, and the conversion run for
this markdown file reports no loss notes. Pinning them means that if either improves, the test
fails and the improvement has to be recorded deliberately.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
PROBE = REPO / "scripts" / "probes" / "anchor_and_loss_probe.py"


@pytest.fixture(scope="module")
def receipt():
    result = subprocess.run([sys.executable, str(PROBE)], cwd=str(REPO), capture_output=True,
                            text=True, encoding="utf-8", errors="replace", timeout=900)
    payload = (result.stdout or "").strip()
    start = payload.find("{")
    if start < 0:
        pytest.fail(f"probe produced no receipt (exit {result.returncode}): {payload[-400:]}")
    return json.loads(payload[start:])


def test_the_sanctioned_migration_ran_first(receipt):
    steps = {step["step"]: step for step in receipt["steps"]}
    assert steps["migrate"]["exit"] == 0


def test_the_original_hash_survived_intake(receipt):
    assert receipt["intake_preserved_hash"] is True


def test_the_locator_offset_actually_lands_on_the_phrase(receipt):
    assert receipt["locator_offset_lands_on_the_phrase"] is True


def test_the_create_response_returns_the_locator_it_was_given(receipt):
    assert receipt["anchor_response_matches_sent_locator"] is True


def test_a_precise_position_is_not_reported_returned_without_one(receipt):
    """The rule: precision is claimed only when a precision field actually came back."""
    returned = receipt["precision_fields_returned"]
    assert receipt["precise_position_returned"] is (len(returned) > 0)
    for field in returned:
        assert field in receipt["locator_readback"]


def test_the_conversion_run_answers_and_reports_its_engine(receipt):
    assert receipt["conversion_run_status"] == 200
    assert receipt["conversion_run_engine"]


def test_the_loss_notes_channel_is_present(receipt):
    assert isinstance(receipt["loss_notes"], list)


# Measured on 2026-10-04 at commit 383a4708 and its successor. Pinned on purpose.
def test_the_outcomes_recorded_are_the_ones_measured(receipt):
    assert receipt["precision_fields_returned"] == []
    assert receipt["locator_readback_keys"] == ["page", "source_format"]
    assert receipt["loss_notes"] == []
