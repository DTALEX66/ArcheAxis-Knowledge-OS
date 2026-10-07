"""F09: one cell of a workbook is a location of its own, and the anchor mechanism can address it.

Before this the smallest addressable thing in an xlsx projection was the row line, which carries
several cells joined by " | ": a quote from one cell could only be anchored to a line that also
contained its neighbours, so the anchor claimed more than the evidence supported. The generic
`params.format.locations` verifier is what makes a reported location addressable, so the worker must
report cells the way it reports ODF paragraphs and Python symbols - by a unique path, with the value
exactly as the projection shows it.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKER = ROOT / "services" / "python-workers" / "document" / "worker_office.py"
spec = importlib.util.spec_from_file_location("worker_office_xlsx", WORKER)
assert spec and spec.loader
worker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(worker)

RESULT = worker._xlsx_text(ROOT / "tests" / "fixtures" / "sample.xlsx")


def cell_locations() -> list[dict]:
    return RESULT["loss_receipt"]["params"]["format"]["locations"]


def test_a_cell_reports_a_location_of_its_own() -> None:
    locations = cell_locations()
    assert locations, "the projection has cells, so it must report cell locations"
    paths = [entry["path"] for entry in locations]
    assert len(paths) == len(set(paths)), "an ambiguous path is refused by the verifier, not resolved"
    assert any(path.endswith("!A1") for path in paths), paths


def test_every_reported_value_is_what_the_projection_actually_shows() -> None:
    text = RESULT["text"]
    for entry in cell_locations():
        assert entry["value"] in text, f"{entry['path']} reports bytes the projection does not carry"
        assert entry["value"].startswith(f"{entry['coordinate']}="), entry


def test_a_cell_is_addressable_apart_from_the_row_line_that_carries_it() -> None:
    """The point of F09: a row line can hold several cells, and each is anchorable alone."""
    rows = [
        RESULT["text"][entry["char_start"]:entry["char_end"]] for entry in RESULT["structure"]
    ]
    multi_cell_rows = [row for row in rows if " | " in row]
    assert multi_cell_rows, "no row carried more than one cell, so this test would prove nothing"
    row = multi_cell_rows[0]
    tokens = row.split(" | ")
    paths = [entry["path"] for entry in cell_locations() if entry["value"] in tokens]
    assert len(paths) == len(tokens), (tokens, paths)
    assert len(set(paths)) == len(paths), paths


def test_the_cap_is_stated_rather_than_silently_applied() -> None:
    format_params = RESULT["loss_receipt"]["params"]["format"]
    assert format_params["locations_capped"] is False
    assert format_params["locations_reported"] == format_params["locations_total"] == len(cell_locations())
    assert "location_model" in format_params
    assert "live calculations" in RESULT["loss_receipt"]["loss_note"]


def test_row_anchors_still_exist_and_do_not_pretend_to_be_cells() -> None:
    kinds = {entry["kind"] for entry in RESULT["structure"]}
    assert kinds == {"sheet_row"}, kinds
    assert all(isinstance(entry["path"], list) for entry in RESULT["structure"]), RESULT["structure"][:2]


XLS_RESULT = worker.extract(str(ROOT / "tests" / "fixtures" / "golden" / "golden-xls-anchor.xls"))


def xls_cell_locations() -> list[dict]:
    return XLS_RESULT["loss_receipt"]["params"]["format"]["locations"]


def test_a_binary_workbook_cell_is_addressable_too() -> None:
    """The same gap existed in .xls, where the projected unit was a whole sheet body."""
    locations = xls_cell_locations()
    assert locations, "the golden workbook has cells, so it must report cell locations"
    paths = [entry["path"] for entry in locations]
    assert len(paths) == len(set(paths)), "an ambiguous path is refused by the verifier, not resolved"
    text = XLS_RESULT["text"]
    for entry in locations:
        assert entry["value"] in text, f"{entry['path']} reports bytes the projection does not show"
    assert len(XLS_RESULT["structure"]) < len(locations), (
        "cell locations must be finer than the sheet-level structure this projection reports"
    )


def test_the_binary_workbook_reports_the_cell_type_it_read() -> None:
    kinds = {entry["cell_type"] for entry in xls_cell_locations()}
    assert {"text", "number"} <= kinds, kinds
    format_params = XLS_RESULT["loss_receipt"]["params"]["format"]
    assert format_params["locations_capped"] is False
    assert format_params["locations_reported"] == format_params["locations_total"] == len(
        xls_cell_locations())
