"""Finite guards for the exact owned workspace report contract.

These are pure/static checks. They do not launch Core, a model, a window or an
installed runtime, and they do not relax any existing path guard.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "scripts/probes/workspace_path_report.py"


@pytest.fixture(scope="module")
def report():
    spec = importlib.util.spec_from_file_location("v3_workspace_path_report", SOURCE)
    loaded = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(loaded)
    return loaded


def test_exact_plain_and_extended_local_reports_return_known_owned_path(report, tmp_path):
    expected = tmp_path / "data" / "workspace.sqlite"
    verbatim = "\\\\?\\" + str(expected)
    assert report.checked_workspace_report(str(expected), expected) is expected
    assert report.checked_workspace_report(verbatim, expected) is expected
    assert report.checked_workspace_report(verbatim, expected) != Path(verbatim)


@pytest.mark.parametrize("case", [
    "unc", "extended_unc", "device", "other_drive", "other_filename", "other_run",
    "slash_change", "case_change", "dotdot", "double_prefix", "trailing_space",
    "nul", "empty", "none", "path_object", "bytes_value",
])
def test_foreign_or_inexact_reports_are_rejected(report, tmp_path, case):
    expected = tmp_path / "data" / "workspace.sqlite"
    plain = str(expected)
    values = {
        "unc": "\\\\server\\share\\data\\workspace.sqlite",
        "extended_unc": "\\\\?\\UNC\\server\\share\\data\\workspace.sqlite",
        "device": "\\\\.\\PhysicalDrive0",
        "other_drive": "E:" + plain[2:],
        "other_filename": str(expected.with_name("other.sqlite")),
        "other_run": str(tmp_path / "other" / "data" / "workspace.sqlite"),
        "slash_change": plain.replace("\\", "/"),
        "case_change": plain.swapcase(),
        "dotdot": plain.replace("\\data\\", "\\data\\..\\data\\"),
        "double_prefix": "\\\\?\\\\\\?\\" + plain,
        "trailing_space": plain + " ",
        "nul": plain + "\x00",
        "empty": "",
        "none": None,
        "path_object": Path(plain),
        "bytes_value": plain.encode(),
    }
    with pytest.raises(ValueError):
        report.checked_workspace_report(values[case], expected)


@pytest.mark.parametrize("expected", [
    Path("relative/data/workspace.sqlite"),
    Path("E:/project/.project-local/runs/w/data/workspace.sqlite"),
    Path("F:/project/.project-local/runs/w/data/workspace.sqlite"),
    Path("D:/project/.project-local/runs/w/data/elsewhere/workspace.sqlite"),
    Path("D:/project/.project-local/runs/w/data/workspace.db"),
    Path("D:/project/.project-local/runs/w/data/../data/workspace.sqlite"),
])
def test_invalid_expected_owned_path_is_rejected(report, expected):
    with pytest.raises(ValueError):
        report.checked_workspace_report(str(expected), expected)


def test_repo_binding_rejects_a_path_outside_this_project_runs(report):
    ordinary = ROOT / ".project-local" / "runs" / "w" / "data" / "workspace.sqlite"
    verbatim = "\\\\?\\" + str(ordinary)
    assert report.checked_workspace_report(verbatim, ordinary, repo=ROOT) is ordinary
    outside = ROOT.parent / "other" / "data" / "workspace.sqlite"
    with pytest.raises(ValueError, match="outside"):
        report.checked_workspace_report(str(outside), outside, repo=ROOT)


def test_verbatim_report_still_fails_the_existing_dev_guard(report):
    """The original failure must stay reproducible without changing dev.safe_path."""
    from scripts.runtime import dev
    ordinary = ROOT / ".project-local" / "runs" / "w" / "data" / "workspace.sqlite"
    verbatim = "\\\\?\\" + str(ordinary)
    with pytest.raises(ValueError):
        dev.safe_path(Path(verbatim))
    assert report.checked_workspace_report(verbatim, ordinary, repo=ROOT) is ordinary


def test_both_formal_probes_use_the_exact_report_guard():
    model = (ROOT / "scripts/probes/colearning_asset_revision_smoke.py").read_text(encoding="utf-8")
    native = (ROOT / "scripts/probes/aaos_v3_consumer_native.py").read_text(encoding="utf-8")
    flat_model, flat_native = "".join(model.split()), "".join(native.split())
    assert "checked_workspace_report(version[\"workspace_db\"]" in flat_model
    assert "checked_workspace_report(launched[\"workspace\"]" in flat_model
    assert "dev.safe_path(Path(version[\"workspace_db\"]))" not in flat_model
    assert "checked_workspace_report(before[\"workspace_db\"]" in flat_native
    assert "checked_workspace_report(saved[\"database\"]" in flat_native
    assert "owned_path(before[\"workspace_db\"]" not in flat_native
