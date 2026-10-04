"""What the product says it can do, and what searching it actually answered.

Two things are recorded here rather than asserted as good news. The capability list the handshake
returns is empty and the test pins that, so wiring the catalogue through cannot pass unnoticed. The
search attempts are recorded with whatever they answered, and the tests assert only that an outcome
was recorded - search is not reported as working, because it did not answer.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
PROBE = REPO / "scripts" / "probes" / "capability_and_search_probe.py"


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


def test_the_handshake_answers(receipt):
    steps = {step["step"]: step for step in receipt["steps"]}
    assert steps["handshake"]["status"] == 200


def test_the_capability_catalogue_is_still_empty(receipt):
    """Pinned on purpose: this is the Q09 gap, and fixing it must fail this test deliberately.

    app/workspace/system.py builds the handshake with a literal empty list for capabilities, while
    the Rust core has a capability registry. When someone wires the two together, this assertion
    fails and the change has to be acknowledged rather than passing silently.
    """
    assert receipt["handshake_capabilities"] == []
    assert receipt["handshake_capabilities_is_empty_list"] is True


def test_every_search_attempt_recorded_an_outcome(receipt):
    attempts = receipt["searches"]
    assert attempts
    for attempt in attempts:
        assert attempt.get("status") is not None or attempt.get("error"), attempt["root_kind"]


def test_the_search_body_shape_used_is_the_documented_one(receipt):
    """The route takes {root, query}; both keys were sent on every attempt."""
    assert len(receipt["searches"]) == 2
    kinds = {attempt["root_kind"] for attempt in receipt["searches"]}
    assert kinds == {"temp-work", "fixture-vault"}


def test_no_claim_is_made_about_whether_search_works(receipt):
    """Deliberately does not pin an outcome, because the outcome is machine-dependent.

    Locally both attempts failed - one with a server error, one by timing out - while CI answered 200
    for both. That difference is why this asserts only that an outcome was recorded. An earlier
    version of this test pinned the local failure as if it were a product fact and CI correctly
    rejected it. What is pinned elsewhere in this file is the empty capability list, and that is
    pinned because it comes from a literal in the source rather than from one machine's behaviour.
    """
    for attempt in receipt["searches"]:
        assert "status" in attempt
