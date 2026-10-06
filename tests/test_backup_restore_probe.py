"""Backup and restore must keep working, and this keeps both halves measured.

The backup side must produce a manifest whose hash really describes the file it names, and the
restore side must land in a target that was independently established and survive a restart. The one
thing deliberately not asserted is byte-identity: the restored file is not a byte copy of the backup,
which is recorded rather than required, because a logical restore is the honest description.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
PROBE = REPO / "scripts" / "probes" / "backup_restore_probe.py"


@pytest.fixture(scope="module")
def receipt():
    result = subprocess.run([sys.executable, str(PROBE)], cwd=str(REPO), capture_output=True,
                            text=True, encoding="utf-8", errors="replace", timeout=1800)
    payload = (result.stdout or "").strip()
    start = payload.find("{")
    if start < 0:
        pytest.fail(f"probe produced no receipt (exit {result.returncode}): {payload[-400:]}")
    return json.loads(payload[start:])


def test_a_backup_was_produced(receipt):
    assert receipt["ok"] is True, receipt.get("failed_step")
    assert receipt["backup_count"] >= 1


def test_the_manifest_hash_describes_the_file_it_names(receipt):
    """The point of a manifest: its hash must be the hash of the backup, not a claim about it."""
    assert receipt["manifest_sha256"] == receipt["backup_sha256"]


def test_the_manifest_size_matches_the_file(receipt):
    assert receipt["manifest_bytes"] == receipt["backup_bytes"]


def test_the_manifest_names_the_tables_it_requires(receipt):
    assert "schema_migrations" in receipt["manifest_required_tables"]
    assert "core_objects" in receipt["manifest_required_tables"]


def test_the_restore_target_was_established_before_restoring(receipt):
    """A candidate binds to its target, so the target has to exist first - measured, not assumed."""
    assert receipt["target_before_restore"]["db_present"] is True


def test_the_restored_store_is_intact(receipt):
    assert receipt["after_restore"]["integrity_check"] == "ok"
    assert receipt["after_restore"]["table_count"] > 0
    assert receipt["restore_integrity_ok"] is True


def test_the_restored_store_survives_a_restart(receipt):
    assert receipt["survives_cold_start"] is True


def test_byte_identity_is_recorded_rather_than_required(receipt):
    """A logical restore, not a byte copy. Asserted only that the answer is recorded at all.

    If a future change made the restore a byte copy this would still pass, and the receipt would
    show it; what must not happen is the property going unobserved in either direction.
    """
    assert isinstance(receipt["restore_is_byte_identical_to_backup"], bool)
    assert receipt["restored_sha256"] is not None
