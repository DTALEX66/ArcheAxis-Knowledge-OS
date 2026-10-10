'''The two live chain probes are the strongest evidence this work produced, so a gate runs them.

They were driven by hand, which means a Core regression would break them silently and keep the
receipt claiming they pass. This runs them the way they were run, and skips - loudly - where no
built Core is present, because a skipped probe is honest and a fabricated pass is not.
'''

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

PROBES = {
    "conversion": ROOT / "scripts/probes/r10_core_journey_smoke.py",
    "learning": ROOT / "scripts/probes/r10_learning_chain_smoke.py",
}

# The probes read the Core from this path. A checkout that never built one skips rather than fails.
CORE = ROOT / ".project-local" / "build" / "cargo" / "debug" / "archeaxis-api.exe"


def _run(probe: Path) -> dict:
    completed = subprocess.run(
        [sys.executable, str(probe)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=600,
    )
    assert completed.returncode == 0, (
        f"{probe.name} exited {completed.returncode}\n{completed.stdout[-2000:]}\n{completed.stderr[-2000:]}"
    )
    line = [row for row in completed.stdout.splitlines() if row.startswith("{")]
    assert line, f"{probe.name} printed no receipt: {completed.stdout[-800:]}"
    return json.loads(line[-1])


needs_core = pytest.mark.skipif(
    not (CORE.is_file() and PROBES["conversion"].is_file()),
    reason="no built Core in this checkout, so the live probes cannot be driven",
)


@needs_core
def test_the_conversion_chain_still_runs_and_still_declines_to_claim_the_loop() -> None:
    receipt = _run(PROBES["conversion"])
    assert receipt["ok"] is True, receipt
    assert receipt["failed_step"] is None, receipt
    # It is a conversion probe and says so; if that ever changes the receipt must be re-read.
    assert receipt["scope"] == "real_conversion_probe", receipt
    assert receipt["closed_loop_verified"] is False, (
        "the conversion probe must not claim the loop: it stops before knowledge and learning")
    steps = {row["step"] for row in receipt["steps"]}
    assert {"reachability", "import", "search"} <= steps, steps


@needs_core
def test_the_learning_chain_still_runs_and_still_excludes_human_review() -> None:
    receipt = _run(PROBES["learning"])
    assert receipt["ok"] is True, receipt
    assert receipt["failed_step"] is None, receipt
    steps = {row["step"]: row["status"] for row in receipt["steps"]}
    for name in ("reachability", "accepted_fact", "learning_event", "reference", "assessment",
                 "answer", "item_state"):
        assert name in steps, steps
        assert 200 <= steps[name] < 300, (name, steps)
    # The answer is the feedback, and it carries a schedule and a projection, read not guessed.
    assert "next_review" in receipt["answer_keys"], receipt
    assert "mastery_projection" in receipt["answer_keys"], receipt
    assert "question" in receipt["assessment_keys"], receipt
    # Reviewing knowledge stays a human act and must never enter the journey.
    assert receipt["not_covered"] == ["human knowledge review"], receipt
