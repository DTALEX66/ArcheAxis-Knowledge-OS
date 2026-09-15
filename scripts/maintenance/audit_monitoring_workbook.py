#!/usr/bin/env python3
"""Read-only structural audit for the monitoring workbook.

The workbook is an evidence source, not an execution budget engine.  This
utility never edits it and reports only facts available from the XLSX package
and formula text; it does not evaluate formulas.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _reject_path(path: Path, *, output: bool = False) -> Path:
    absolute = Path(os.path.abspath(path))
    if absolute.drive.upper() == "E:" or str(absolute).startswith("\\\\"):
        raise ValueError("protected drive or UNC path")
    if output:
        project_local = (ROOT / ".project-local").resolve()
        try:
            absolute.resolve().relative_to(project_local)
        except ValueError as exc:
            raise ValueError("output must stay inside .project-local") from exc
    return absolute


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def audit(input_path: Path) -> dict:
    try:
        from openpyxl import load_workbook
    except ImportError as exc:
        raise RuntimeError("openpyxl is required for workbook structural audit") from exc

    input_path = _reject_path(input_path)
    if not input_path.is_file():
        raise ValueError(f"input workbook is not a file: {input_path}")
    before = input_path.stat()
    workbook = load_workbook(input_path, read_only=True, data_only=False)
    sheets = []
    formula_count = 0
    formula_division_count = 0
    try:
        for worksheet in workbook.worksheets:
            validations = getattr(worksheet, "data_validations", None)
            validation_count = len(validations.dataValidation) if validations else 0
            sheet_formula_count = 0
            sheet_division_count = 0
            for row in worksheet.iter_rows():
                for cell in row:
                    value = cell.value
                    if isinstance(value, str) and value.startswith("="):
                        sheet_formula_count += 1
                        if "/" in value:
                            sheet_division_count += 1
            formula_count += sheet_formula_count
            formula_division_count += sheet_division_count
            sheets.append({
                "title": worksheet.title,
                "max_row": worksheet.max_row,
                "max_column": worksheet.max_column,
                "sheet_state": worksheet.sheet_state,
                "protected": bool(getattr(getattr(worksheet, "protection", None), "sheet", False)),
                "data_validation_rules": validation_count,
                "formula_cells": sheet_formula_count,
                "formula_cells_containing_division": sheet_division_count,
            })
    finally:
        workbook.close()
    after = input_path.stat()
    return {
        "schema": "archeaxis.monitoring-workbook-audit/v1",
        "status": "STRUCTURAL_AUDIT_ONLY",
        "input": str(input_path),
        "input_opened_read_only": True,
        "input_unchanged_during_audit": before.st_size == after.st_size and before.st_mtime_ns == after.st_mtime_ns,
        "bytes": before.st_size,
        "sha256": _sha256(input_path),
        "sheet_count": len(sheets),
        "defined_names": 0,
        "formula_cells": formula_count,
        "formula_cells_containing_division": formula_division_count,
        "sheets": sheets,
        "formula_evaluation": "NOT_PERFORMED",
        "interpretation": "Structural metadata only; formula correctness and scenario outcomes require a separate evaluated regression.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="XLSX path to inspect")
    parser.add_argument("--output-json", type=Path, help="optional output path under .project-local")
    args = parser.parse_args()
    try:
        report = audit(args.input)
        encoded = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
        if args.output_json:
            output = _reject_path(args.output_json, output=True)
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(encoded, encoding="utf-8")
        else:
            print(encoded, end="")
    except (ImportError, OSError, RuntimeError, ValueError) as exc:
        print(f"audit_monitoring_workbook: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
