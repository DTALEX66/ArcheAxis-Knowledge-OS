"""The process tree and the isolated worker must stay measured, wherever a core can be built.

This probe needs a built core binary, so where one is absent it skips loudly rather than passing.
The worker sighting is timing dependent - the process may live for a moment - so it is recorded and
not required. What is required is what must hold wherever the core runs.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
PROBE = REPO / "scripts" / "probes" / "process_tree_probe.py"
BUILD_HINT = "cargo build -p archeaxis-api --target-dir .project-local/build/aaos01-core"


@pytest.fixture(scope="module")
def receipt():
    result = subprocess.run([sys.executable, str(PROBE)], cwd=str(REPO), capture_output=True,
                            text=True, encoding="utf-8", errors="replace", timeout=1800)
    payload = (result.stdout or "").strip()
    start = payload.find("{")
    if start < 0:
        pytest.fail("probe produced no receipt (exit %s): %s" % (result.returncode, payload[-300:]))
    loaded = json.loads(payload[start:])
    if not loaded.get("core_present"):
        pytest.skip("core binary not built; run " + BUILD_HINT)
    if loaded.get("failed_step") == "no_powershell":
        pytest.skip("no PowerShell available to enumerate the process tree")
    return loaded


def test_the_core_started_and_announced_readiness(receipt):
    assert receipt["ok"] is True, receipt.get("failed_step")
    assert receipt["readiness_announced"] is True


def test_the_core_is_a_child_of_the_process_that_launched_it(receipt):
    assert receipt["core_parent_pid"] == receipt["launched_by_python_pid"]


def test_timings_are_recorded_as_numbers(receipt):
    for key in ("seconds_to_ready", "capability_seconds"):
        assert isinstance(receipt[key], (int, float)), key
        assert receipt[key] >= 0, key


def test_the_capability_names_its_transport(receipt):
    assert receipt["capability_status"] == 200
    assert receipt["capability_name"] == "text.extract"
    assert "text_ndjson.py" in receipt["capability_provider"]


def test_the_watcher_actually_ran(receipt):
    assert receipt["watch_seconds"] > 0
    assert isinstance(receipt["worker_seen"], bool)
    assert isinstance(receipt["watcher_lines"], int)


def test_any_sighting_is_a_python_child_of_the_core(receipt):
    for sighting in receipt["sightings"]:
        assert sighting["name"].lower().startswith("python")
        assert sighting["pid"] != str(receipt["core_pid"])
