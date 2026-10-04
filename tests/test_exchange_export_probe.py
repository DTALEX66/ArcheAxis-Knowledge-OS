"""Exporting writes what the read projection withholds, and the receipt proves both.

The contrast asserted here is the point of the test: the anchor read route returns only the page
and the source format, while the exported record carries block identifiers. That difference is
measured in one receipt rather than described, so it cannot quietly change.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
PROBE = REPO / "scripts" / "probes" / "exchange_export_probe.py"


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


def test_the_export_reports_what_it_wrote(receipt):
    assert receipt["export_status"] == 200
    assert isinstance(receipt["export"]["item_count"], int)
    assert receipt["export"]["item_count"] >= 1
    assert re.fullmatch(r"[0-9a-f]{64}", receipt["export"]["manifest_sha256"] or "")


def test_the_export_directory_exists_and_is_not_empty(receipt):
    assert receipt["destination_exists"] is True
    assert receipt["exported_file_count"] >= 1


def test_the_product_verifies_its_own_export(receipt):
    assert receipt["verify_status"] == 200
    assert receipt["verify"]["valid"] is True
    assert receipt["verify"]["verified_items"] >= 1


def test_the_read_projection_and_the_exported_record_are_compared_not_described(receipt):
    """Measured in one receipt: the read withholds what the export carries."""
    contrast = receipt["contrast"]
    assert contrast["read_projection_has_block_ids"] is False
    assert "block_ids" not in receipt["read_projection_keys"]
    assert contrast["exported_has_block_ids"] is True
    assert "block_ids" in receipt["exported_locator_keys"]


def test_the_manifest_file_hash_is_recorded_but_not_compared_with_the_manifest_field(receipt):
    """Guards against reviving the wrong expectation: the two hashes are different things."""
    assert re.fullmatch(r"[0-9a-f]{64}", receipt["manifest_file_sha256"] or "")
    assert "manifest_sha256_matches_report" not in receipt
