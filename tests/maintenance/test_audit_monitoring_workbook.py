"""Tests for the read-only monitoring workbook structural audit."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "maintenance" / "audit_monitoring_workbook.py"
SPEC = importlib.util.spec_from_file_location("audit_monitoring_workbook", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


def test_audit_reports_structure_without_formula_evaluation(tmp_path: Path) -> None:
    openpyxl = pytest.importorskip("openpyxl")
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "Scenario"
    sheet["A1"] = "=1/0"
    sheet["B1"] = "=IF(A1>0,1,0)"
    source = tmp_path / "source.xlsx"
    workbook.save(source)

    report = MODULE.audit(source)

    assert report["status"] == "STRUCTURAL_AUDIT_ONLY"
    assert report["input_opened_read_only"] is True
    assert report["formula_evaluation"] == "NOT_PERFORMED"
    assert report["formula_cells"] == 2
    assert report["formula_cells_containing_division"] == 1
    assert report["division_formulas"][0]["cell"] == "A1"
    assert report["division_formulas"][0]["boundary_regression"] == "REQUIRED"
    assert report["sheet_count"] == 1


def test_output_path_must_be_project_local() -> None:
    with pytest.raises(ValueError, match=r"inside \.project-local"):
        MODULE._reject_path(Path("C:/outside/report.json"), output=True)


def test_protected_drive_is_rejected() -> None:
    with pytest.raises(ValueError, match="protected drive"):
        MODULE._reject_path(Path("E:/private/source.xlsx"))
