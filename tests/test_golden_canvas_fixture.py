"""G0: a committed JSON Canvas fixture must carry its own integrity record."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "golden" / "learning-evidence.canvas"
MANIFEST = ROOT / "tests" / "fixtures" / "golden" / "manifest.json"


def test_golden_canvas_fixture_has_project_owned_integrity_metadata() -> None:
    record = json.loads(MANIFEST.read_text(encoding="utf-8"))["fixtures"]["learning-evidence.canvas"]

    assert record["format"] == "json-canvas"
    assert record["rights_basis"] == "project-authored synthetic test fixture"
    assert record["privacy"] == "no personal data"
    assert record["sha256"] == hashlib.sha256(FIXTURE.read_bytes()).hexdigest()
    document = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert {node["id"] for node in document["nodes"]} == {"source", "evidence"}
    assert document["edges"] == [
        {"id": "source-evidence", "fromNode": "source", "toNode": "evidence"}
    ]
