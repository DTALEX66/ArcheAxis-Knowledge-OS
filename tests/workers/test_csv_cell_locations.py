"""F01: one cell of a delimited file is a location of its own.

Before this the smallest thing an anchor could name in a CSV/TSV projection was the row, which
carries every other field of that line, so a quote from a single value claimed its neighbours as
evidence. The generic `params.format.locations` verifier is what makes a reported location
addressable, so the cells are reported the way workbook cells and Python symbols are: by a unique
path, with the value the engine actually parsed.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKER = ROOT / "services" / "python-workers" / "document" / "worker_text.py"
spec = importlib.util.spec_from_file_location("worker_text_csv", WORKER)
assert spec and spec.loader
worker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(worker)

CSV_TEXT = 'name,radius_km,note\n"Earth",6371,"round, mostly"\nMars,3389,\n'
FACTS = worker._delimited_facts(CSV_TEXT, ",")


def cells() -> list[dict]:
    return FACTS["locations"]


def test_a_cell_reports_a_location_of_its_own() -> None:
    assert cells(), "the projection has cells, so it must report cell locations"
    paths = [entry["path"] for entry in cells()]
    assert len(paths) == len(set(paths)), "an ambiguous path is refused by the verifier, not resolved"
    by_path = {entry["path"]: entry for entry in cells()}
    assert by_path["csv!B2"]["value"] == "6371", by_path["csv!B2"]
    assert by_path["csv!C2"]["value"] == "round, mostly", by_path["csv!C2"]
    assert by_path["csv!C2"]["column_name"] == "note", by_path["csv!C2"]


def test_a_cell_is_addressable_apart_from_the_row_that_carries_it() -> None:
    second_row = [entry for entry in cells() if entry["row"] == 2]
    assert [entry["path"] for entry in second_row] == ["csv!A2", "csv!B2", "csv!C2"], second_row
    assert len({entry["path"] for entry in second_row}) == len(second_row)
    # one projected line carries all three, which is exactly what a row anchor used to conflate
    assert CSV_TEXT.splitlines()[1] == '"Earth",6371,"round, mostly"'
    assert FACTS["row_count"] == 3 and FACTS["header"] == ["name", "radius_km", "note"]


def test_an_empty_cell_is_not_reported_as_a_location() -> None:
    assert not [entry for entry in cells() if entry["path"] == "csv!C3"], cells()


def test_a_value_the_projection_does_not_show_verbatim_is_flagged_not_silently_anchorable() -> None:
    escaped = worker._delimited_facts('say\n"quote ""inside"""\n', ",")
    entry = [item for item in escaped["locations"] if item["coordinate"] == "A2"][0]
    assert entry["value"] == 'quote "inside"', entry
    assert entry["in_projection"] is False, entry
    assert "in_projection=false" in escaped["note"], escaped["note"]


def test_the_cap_is_stated_rather_than_silently_applied() -> None:
    many = "\n".join(f"{i},{i + 1}" for i in range(50))
    facts = worker._delimited_facts(many, ",")
    assert facts["locations_total"] == 100, facts["locations_total"]
    original = worker.TABLE_CELL_CAP
    worker.TABLE_CELL_CAP = 10
    try:
        capped = worker._delimited_facts(many, ",")
    finally:
        worker.TABLE_CELL_CAP = original
    assert capped["locations_capped"] is True
    assert capped["locations_reported"] == 10
    assert len(capped["locations"]) == 10
    assert "capped at 10 of 100" in capped["note"], capped["note"]
