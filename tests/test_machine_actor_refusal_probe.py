"""The human-review route must refuse a machine session, and this keeps that measured.

Two rounds of hand measurement established this and hand measurement goes stale, so it is a probe
now. The assertions pin the refusal itself and the two properties that make it a boundary rather
than a courtesy: the session declared machine, and nothing declared human.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
PROBE = REPO / "scripts" / "probes" / "machine_actor_refusal_probe.py"


@pytest.fixture(scope="module")
def receipt():
    result = subprocess.run([sys.executable, str(PROBE)], cwd=str(REPO), capture_output=True,
                            text=True, encoding="utf-8", errors="replace", timeout=900)
    payload = (result.stdout or "").strip()
    start = payload.find("{")
    if start < 0:
        pytest.fail(f"probe produced no receipt (exit {result.returncode}): {payload[-400:]}")
    return json.loads(payload[start:])


def test_the_core_binary_was_available(receipt):
    assert receipt["core_present"] is True, "build the core before running this probe"


def test_the_machine_session_started_and_answered(receipt):
    assert receipt["ok"] is True, receipt.get("failed_step")
    assert receipt["version_status"] == 200


def test_the_machine_session_was_refused_the_human_review(receipt):
    assert receipt["review_status"] == 403
    assert receipt["refused_with_403"] is True


def test_the_refusal_names_the_reason(receipt):
    assert receipt["refusal_names_the_reason"] is True
    assert "machine principal" in receipt["review_body"]


def test_no_human_declaration_was_sent(receipt):
    """The refusal is obtained without emitting a false human claim, which is the point.

    If a future version of this probe was tempted to declare human in order to see the header
    overridden, this assertion records that the evidence was available without doing so.
    """
    assert receipt["sent_human_declaration"] is False
    assert receipt["launch_declared_actor"] == "machine"
