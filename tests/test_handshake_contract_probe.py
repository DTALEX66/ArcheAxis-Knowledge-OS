"""The handshake probe must keep passing, and this is what stops it rotting silently."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from scripts.runtime import dev

REPO = Path(__file__).resolve().parents[1]
PROBE = REPO / "scripts" / "probes" / "handshake_contract_probe.py"

# The conditions frontend/src/api/client.ts applies, restated here so the test fails if the
# probe or the endpoint drifts away from what the shell actually requires.
PINNED_PRODUCT_ID = "archeaxis-workspace"
PINNED_API_CONTRACT = "1.x"
REQUIRED_NON_EMPTY = ("product_name", "backend_version", "source_commit", "runtime_mode", "workspace_id")


@pytest.fixture(scope="module")
def receipt():
    paths = dev.layout(REPO, "handshake-test")
    dev.prepare(paths)
    result = subprocess.run(
        [sys.executable, str(PROBE), "--json-out", str(paths["artifacts"] / "handshake-test-receipt.json")],
        cwd=str(REPO), capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=900,
    )
    payload = (result.stdout or "").strip()
    start = payload.find("{")
    if start < 0:
        pytest.fail(f"probe produced no receipt (exit {result.returncode}): {payload[-400:]} {(result.stderr or "")[-400:]}")
    return json.loads(payload[start:])


def test_the_probe_drove_the_sanctioned_migration(receipt):
    steps = {step["step"]: step for step in receipt["steps"]}
    assert steps["migrate"]["exit"] == 0
    assert receipt["database_created"] is True


def test_the_endpoint_answered(receipt):
    steps = {step["step"]: step for step in receipt["steps"]}
    assert steps["handshake"]["status"] == 200


def test_the_handshake_satisfies_the_shell_contract(receipt):
    assert receipt["contract_violations"] == []
    assert receipt["ok"] is True


def test_the_pinned_values_are_what_the_shell_pins(receipt):
    body = receipt["handshake"]
    assert body["product_id"] == PINNED_PRODUCT_ID
    assert body["api_contract"] == PINNED_API_CONTRACT


def test_the_required_fields_are_present_and_non_empty(receipt):
    body = receipt["handshake"]
    for field in REQUIRED_NON_EMPTY:
        assert isinstance(body[field], str) and body[field].strip(), field
    assert isinstance(body["schema_version"], int) and body["schema_version"] >= 1
    assert isinstance(body["capabilities"], list)
    assert body["migration_state"] == "ready"


def test_the_reported_commit_is_a_real_commit_of_this_repository(receipt):
    commit = receipt["handshake"]["source_commit"]
    exists = subprocess.run(["git", "cat-file", "-e", f"{commit}^{{commit}}"], cwd=str(REPO),
                            capture_output=True, text=True)
    assert exists.returncode == 0, f"source_commit {commit!r} is not a commit in this repository"


def test_the_probe_did_not_report_a_failure_step(receipt):
    assert "failed_step" not in receipt
