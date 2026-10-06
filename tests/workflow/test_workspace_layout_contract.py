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


def test_growth_budgets_are_recorded_and_respected():
    module = load_report()
    assert module.DEV_BUDGET_GB, "each class that grows needs a budget"
    report = module.measure()
    over = [entry["name"] for entry in report["dev_root"] if entry["over_budget"]]
    assert over == [], (
        "classes over budget: " + ", ".join(over)
        + " — exceeding a budget needs a decision, not an automatic delete")
