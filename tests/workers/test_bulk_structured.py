"""BULK-0907 P09: bulk structured (Canvas / SRT / VTT) boundary cases.

Extends the R1 fixture matrix with uncovered edges: default node types, missing
nodes/edges handling, multi-line SRT cue text, duration clamping, fractional
millisecond timecodes, VTT inline timing tags, empty/malformed rejections and
BOM handling. Expectations are independent and never copied from worker output.
"""

import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CANVAS = ROOT / "services/python-workers/document/worker_canvas.py"
SUBTITLES = ROOT / "services/python-workers/document/worker_subtitles.py"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class CanvasBulkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.canvas = _load("worker_canvas", CANVAS)

    def _write(self, payload) -> str:
        fd, path = tempfile.mkstemp(suffix=".canvas", dir=os.environ["ARCHEAXIS_RUN_ROOT"])
        with open(fd, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(payload, fh, ensure_ascii=False)
        return path

    def test_node_without_type_defaults_to_text_and_group_does_not_project(self):
        payload = {
            "nodes": [
                {"id": "g1", "type": "group", "label": "grp"},
                {"id": "n1", "text": "首行"},
                {"id": "n2", "type": "text", "text": "次行"},
            ],
            "edges": [],
        }
        out = self.canvas.extract(self._write(payload))
        self.assertEqual(out["text"], "首行\n次行")
        self.assertEqual([a["node_id"] for a in out["structure"]], ["n1", "n2"])

    def test_text_anchor_coordinates_match_projection_without_trailing_newline(self):
        payload = {
            "nodes": [
                {"id": "n1", "type": "text", "text": "甲"},
                {"id": "n2", "type": "text", "text": "乙丙"},
            ],
            "edges": [],
        }
        out = self.canvas.extract(self._write(payload))
        self.assertEqual(out["text"], "甲\n乙丙")
        self.assertEqual([(a["char_start"], a["char_end"]) for a in out["structure"]],
                         [(0, 1), (2, 4)])
        self.assertEqual(out["structure"][1]["char_end"], len(out["text"]))

    def test_file_and_link_nodes_surface_as_references_only(self):
        payload = {
            "nodes": [
                {"id": "f1", "type": "file", "file": "x/evidence.pdf", "label": "原件"},
                {"id": "l1", "type": "link", "url": "https://example.org", "label": "web"},
                {"id": "n1", "type": "text", "text": "正文"},
            ],
            "edges": [],
        }
        out = self.canvas.extract(self._write(payload))
        self.assertEqual(out["text"], "正文")
        self.assertEqual([r["kind"] for r in out["references"]], ["file", "link"])
        self.assertEqual(out["references"][0]["url"], "x/evidence.pdf")

    def test_edges_preserved_verbatim_and_geometry_not_projected(self):
        payload = {
            "nodes": [
                {"id": "a", "type": "text", "text": "A", "x": 1, "y": 2},
                {"id": "b", "type": "text", "text": "B"},
            ],
            "edges": [{"id": "e9", "fromNode": "a", "toNode": "b", "label": "keep-me"}],
        }
        out = self.canvas.extract(self._write(payload))
        self.assertEqual(out["edges"], payload["edges"])
        self.assertEqual(out["text"], "A\nB")
        # geometry/colors are not projected into text or anchors
        self.assertEqual([a["char_end"] for a in out["structure"]], [1, 3])
        self.assertLessEqual(out["structure"][-1]["char_end"], len(out["text"]))

    def test_missing_nodes_array_is_rejected(self):
        with self.assertRaises(self.canvas.CanvasError):
            self.canvas.extract(self._write({"edges": []}))

    def test_node_type_without_id_is_rejected(self):
        with self.assertRaises(self.canvas.CanvasError):
            self.canvas.extract(self._write({"nodes": [{"type": "text", "text": "x"}]}))


class SubtitleBulkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sub = _load("worker_subtitles", SUBTITLES)

    def _write(self, content: str, suffix: str) -> str:
        fd, path = tempfile.mkstemp(suffix=suffix, dir=os.environ["ARCHEAXIS_RUN_ROOT"])
        with open(fd, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(content)
        return path

    def test_multiline_cue_text_and_char_ranges(self):
        content = "1\n00:00:01,000 --> 00:00:02,500\n第一行\n第二行\n\n2\n00:00:03,000 --> 00:00:04,000\n尾"
        out = self.sub.extract(self._write(content, ".srt"))
        self.assertEqual(out["text"], "第一行\n第二行\n尾\n")
        self.assertEqual([a["path"] for a in out["structure"]], [["cue-1"], ["cue-2"]])
        self.assertEqual(out["structure"][0]["char_end"], len("第一行\n第二行"))

    def test_fractional_millisecond_timecode_and_duration_clamp(self):
        content = "1\n00:00:01,5 --> 00:00:00,1\nx"  # end before start
        out = self.sub.extract(self._write(content, ".srt"))
        first = out["structure"][0]
        self.assertEqual(first["offset_ms"], 1500)
        self.assertEqual(first["duration_ms"], 0)  # clamped, not negative

    def test_vtt_inline_timing_tags_are_stripped(self):
        content = (
            "WEBVTT\n\n00:00:01.000 --> 00:00:02.000 align:start\n"
            "<00:00:01.200>开场 <c.red>红字</c>\n\n"
        )
        out = self.sub.extract(self._write(content, ".vtt"))
        self.assertEqual(out["text"], "开场 红字\n")
        self.assertNotIn("<", out["text"])

    def test_vtt_note_block_is_dropped(self):
        content = "WEBVTT\n\nNOTE 这是备注\n\n00:00:01.000 --> 00:00:02.000\n正文\n"
        out = self.sub.extract(self._write(content, ".vtt"))
        self.assertNotIn("备注", out["text"])
        self.assertEqual(out["text"], "正文\n")

    def test_srt_block_without_numeric_index_is_rejected(self):
        with self.assertRaises(ValueError):
            self.sub.extract(self._write("not-a-number\n00:00:01,000 --> 00:00:02,000\nx", ".srt"))

    def test_empty_srt_is_rejected(self):
        with self.assertRaises(ValueError):
            self.sub.extract(self._write("", ".srt"))

    def test_vtt_without_webvtt_header_is_rejected(self):
        with self.assertRaises(ValueError):
            self.sub.extract(self._write("00:00:01.000 --> 00:00:02.000\nx", ".vtt"))

    def test_utf8_bom_srt_is_accepted(self):
        content = "\ufeff1\n00:00:01,000 --> 00:00:02,000\n中文"
        out = self.sub.extract(self._write(content, ".srt"))
        self.assertEqual(out["structure"][0]["path"], ["cue-1"])


if __name__ == "__main__":
    unittest.main()
