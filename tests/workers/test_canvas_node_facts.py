"""R15/F12: the canvas's own geometry, colour and style come back as declared facts.

The matrix row used to claim geometry was not projected; the worker had been reporting it for
slices. These tests pin what the code actually does - including the parts that are NOT projected,
so the next reader does not have to re-derive it from the source.
"""

from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CANVAS = REPO / "services" / "python-workers" / "document" / "worker_canvas.py"
GOLDEN = REPO / "tests" / "fixtures" / "golden" / "golden-canvas-anchor.canvas"

CANVAS_BODY = {
    "nodes": [
        {"id": "a", "type": "text", "text": "Alpha", "x": 0, "y": 10, "width": 240,
         "height": 120, "color": "4", "style": "filled"},
        {"id": "b", "type": "group", "label": "Frame", "x": -50, "y": 0, "width": 600,
         "height": 400, "color": "  "},
        {"id": "c", "type": "text", "text": "Gamma", "x": "not a number", "y": None,
         "width": 3, "height": 4},
    ],
    "edges": [
        {"id": "e1", "fromNode": "a", "fromSide": "right", "fromEnd": "arrow",
         "toNode": "b", "toSide": "left", "toEnd": "line", "color": "1"},
    ],
}


def load():
    spec = importlib.util.spec_from_file_location("worker_canvas_facts", CANVAS)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class CanvasFactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.worker = load()

    def run_canvas(self, payload: dict) -> dict:
        with tempfile.TemporaryDirectory() as box:
            path = Path(box) / "board.canvas"
            path.write_text(json.dumps(payload), encoding="utf-8")
            return self.worker.extract(str(path))

    def test_geometry_colour_and_style_are_reported_per_node(self):
        out = self.run_canvas(CANVAS_BODY)
        by_id = {row["node_id"]: row for row in out["node_geometry"]}
        self.assertEqual(by_id["a"]["geometry"], {"x": 0, "y": 10, "width": 240, "height": 120})
        self.assertEqual(by_id["a"]["color"], "4")
        self.assertEqual(by_id["a"]["style"], "filled")
        self.assertEqual(by_id["b"]["geometry"], {"x": -50, "y": 0, "width": 600, "height": 400})

    def test_a_blank_declared_colour_is_dropped_rather_than_reported_as_empty(self):
        out = self.run_canvas(CANVAS_BODY)
        by_id = {row["node_id"]: row for row in out["node_geometry"]}
        self.assertNotIn("color", by_id["b"], "whitespace is not a colour")

    def test_geometry_fields_must_be_numbers_to_be_reported(self):
        out = self.run_canvas(CANVAS_BODY)
        by_id = {row["node_id"]: row for row in out["node_geometry"]}
        self.assertEqual(by_id["c"]["geometry"], {"width": 3, "height": 4},
                         "a string and a null x/y are not coordinates")

    def test_edge_ports_and_sides_travel_with_the_edge_verbatim(self):
        out = self.run_canvas(CANVAS_BODY)
        self.assertEqual(out["edges"], CANVAS_BODY["edges"],
                         "edges are preserved, not flattened into the text projection")

    def test_the_loss_note_states_what_is_not_read(self):
        out = self.run_canvas(CANVAS_BODY)
        note = out["loss_receipt"]["loss_note"]
        for clause in ("not resolved to a rendered swatch", "z-order", "group containment",
                       "verbatim"):
            self.assertIn(clause, note)
        self.assertNotIn("colors/ports are not projected", note,
                         "the stale claim that ports were dropped must not survive")

    def test_the_golden_canvas_still_projects_and_its_bytes_are_untouched(self):
        raw = GOLDEN.read_bytes()
        out = self.worker.extract(str(GOLDEN))
        self.assertTrue(out["node_geometry"], "the golden canvas carries coordinates")
        self.assertIn("Golden Journey Evidence", out["text"])
        self.assertEqual(GOLDEN.read_bytes(), raw,
                         "a fixture cited by journey receipts is not edited to suit a test")


if __name__ == "__main__":
    unittest.main()
