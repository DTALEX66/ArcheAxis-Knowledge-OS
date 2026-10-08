"""The repository layout is a contract, so drift has to fail a test rather than be noticed later.

This is the guard for the failure the owner reported: after a clean-up the development root had again
accumulated 200+ loose scripts, logs and ad-hoc directories, and its size kept growing with no way to
tell expendable cache from cited evidence. The measurement lives in
`scripts/runtime/storage_report.py`; here it is asserted.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def load_report():
    spec = importlib.util.spec_from_file_location(
        "storage_report", REPO / "scripts" / "runtime" / "storage_report.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_no_entry_sits_outside_the_documented_layout():
    report = load_report().measure()
    assert report["out_of_layout"] == [], (
        "entries outside the layout: " + ", ".join(report["out_of_layout"])
        + " — classify them, then archive (never delete) via scripts/runtime/realign_dev_layout.py")


def test_the_development_root_holds_only_sanctioned_classes():
    report = load_report().measure()
    assert report["dev_strays"] == [], (
        "unsanctioned entries under .project-local: " + ", ".join(report["dev_strays"]))


def test_the_measurement_names_its_own_reference_point():
    """The root expectation comes from Git, so a new tracked directory is never reported as drift."""
    report = load_report().measure()
    assert report["root"], "the tracked root classes were not measured"
    assert all(entry["tracked"] is True for entry in report["root"])
    assert "data" in report["ignored_root"], "local runtime data must be a sanctioned ignored path"


def test_no_run_directory_sits_at_the_wrong_depth():
    """`runs/` holds identity digests and nothing else, and an exception has to be written down.

    The launcher builds `runs/<identity>/<run_id>`, so anything else at that level was improvised.
    This is the depth the rest of this file cannot see: the checks below look at direct children of
    `.project-local`, which is why 2,163 shallow entries and 1,866 loose files sat in the primary
    checkout while every one of those tests passed.

    Following `check_path_conventions.py`'s rule, an exception may exist but not unrecorded: the
    measured set must equal the baseline, so a new shallow directory fails and a stale baseline fails
    too. The recorded entries are directories an NTFS ACL refuses this account and ones holding a
    junction into the shared frontend install - neither is something this suite may force past.
    """
    import json

    module = load_report()
    baseline = json.loads((REPO / "docs" / "current"
                           / "AAOS-RUNS-LAYOUT-BASELINE-20261008.json").read_text(encoding="utf-8"))
    measured: set[str] = set()
    for root in module.checkout_roots(REPO):
        for finding in module.runs_layout(root / ".project-local", root)[0]:
            # Each finding is `runs: <name> (reason)`; the baseline records bare names so a reader
            # can diff it against `ls`, which means the prefix has to come off here.
            measured.add(finding.split("runs: ", 1)[1].split(" (")[0].rstrip("/"))
    recorded = set(baseline["blocked_entries"])
    assert not measured - recorded, (
        f"new entries at the wrong depth under runs/: {sorted(measured - recorded)}"
        " — move them with scripts/runtime/realign_dev_layout.py")
    assert not recorded - measured, (
        f"the runs baseline names paths that are no longer there: {sorted(recorded - measured)}"
        " — regenerate the baseline, do not leave a stale exemption")


def test_growth_budgets_are_recorded_and_respected():
    module = load_report()
    assert module.DEV_BUDGET_GB, "each class that grows needs a budget"
    report = module.measure()
    over = [entry["name"] for entry in report["dev_root"] if entry["over_budget"]]
    assert over == [], (
        "classes over budget: " + ", ".join(over)
        + " — exceeding a budget needs a decision, not an automatic delete")
