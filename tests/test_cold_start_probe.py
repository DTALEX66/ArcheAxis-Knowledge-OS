"""What survives stopping and restarting the product on the same store.

The probe takes a real file in during a first boot, stops the application, starts it again on the
same database without re-ingesting anything, and reports what it finds. The assertions below keep
two things apart: what genuinely survived, and what looks survived only because the list is empty.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
PROBE = REPO / "scripts" / "probes" / "cold_start_probe.py"


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


def test_both_boots_started(receipt):
    steps = {step["step"]: step for step in receipt["steps"]}
    assert steps["first_boot"]["started"] is True
    assert steps["second_boot"]["started"] is True


def test_the_original_hash_survived_intake(receipt):
    assert receipt["intake_preserved_hash"] is True


def test_the_library_answers_before_and_after_the_restart(receipt):
    assert receipt["library_before_restart_status"] == 200
    assert receipt["library_after_restart_status"] == 200


def test_the_library_holds_the_same_thing_across_the_restart(receipt):
    assert receipt["library_identical_across_restart"] is True


def test_the_conversion_run_still_answers_and_still_names_the_same_file(receipt):
    assert receipt["conversion_run_after_restart_status"] == 200
    assert receipt["conversion_run_reports_hash_after_restart"] is True


def test_the_schema_version_is_unchanged_across_the_restart(receipt):
    assert receipt["schema_version_identical_across_restart"] is True


def test_the_capability_list_is_empty_today_so_identity_proves_little(receipt):
    """Recorded so that "identical" is not read as stronger than it is.

    Both boots report no capabilities, so of course they match. When the catalogue is wired through,
    this test fails and the comparison starts meaning something - which is the point of pinning it.
    """
    assert receipt["capabilities_identical_across_restart"] is True
    assert receipt["first_boot"]["capabilities"] == []
    assert receipt["second_boot"]["capabilities"] == []
