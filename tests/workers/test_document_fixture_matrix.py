"""DS05: document fixture matrix — Canvas and subtitle parsers (real entry)."""

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CANVAS = ROOT / "services/python-workers/document/worker_canvas.py"
SUBTITLES = ROOT / "services/python-workers/document/worker_subtitles.py"
FIXTURES = ROOT / "tests/fixtures/vnext/documents"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class CanvasParserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.canvas = _load("worker_canvas", CANVAS)

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=os.environ["ARCHEAXIS_RUN_ROOT"])
        self.addCleanup(self.tmp.cleanup)

    def _write(self, payload: dict) -> str:
        fd, path = tempfile.mkstemp(suffix=".canvas", dir=self.tmp.name)
        with open(fd, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(payload, fh, ensure_ascii=False)
        return path

    def test_chinese_text_group_file_link_and_edges(self):
        out = self.canvas.extract(str(FIXTURES / "canvas-zh-group.canvas"))
        # group is not text; only the two text nodes project, document order.
        self.assertEqual(out["text"], "核聚变研究\n目标与测量")
        self.assertEqual([a["node_id"] for a in out["structure"]], ["n1", "n3"])
        self.assertEqual(len(out["edges"]), 2)
        self.assertEqual([r["kind"] for r in out["references"]], ["file", "link"])
        # edges never flattened: ids survive verbatim
        self.assertEqual({e["id"] for e in out["edges"]}, {"e1", "e2"})

    def test_missing_node_id_rejected(self):
        payload = {"nodes": [{"type": "text", "text": "x"}], "edges": []}
        with self.assertRaises(self.canvas.CanvasError):
            self.canvas.extract(self._write(payload))

    def test_duplicate_node_id_rejected(self):
        payload = {"nodes": [{"id": "a", "type": "text", "text": "x"},
                             {"id": "a", "type": "text", "text": "y"}], "edges": []}
        with self.assertRaises(self.canvas.CanvasError):
            self.canvas.extract(self._write(payload))

    def test_unknown_edge_node_rejected(self):
        payload = {"nodes": [{"id": "n1", "type": "text", "text": "x"}],
                   "edges": [{"id": "e1", "fromNode": "ghost", "toNode": "n1"}]}
        with self.assertRaises(self.canvas.CanvasError):
            self.canvas.extract(self._write(payload))

    def test_unsupported_node_type_rejected(self):
        payload = {"nodes": [{"id": "n1", "type": "video", "src": "x"}], "edges": []}
        with self.assertRaises(self.canvas.CanvasError):
            self.canvas.extract(self._write(payload))


class SubtitleParserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sub = _load("worker_subtitles", SUBTITLES)

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=os.environ["ARCHEAXIS_RUN_ROOT"])
        self.addCleanup(self.tmp.cleanup)

    def _write(self, content: str, suffix: str) -> str:
        fd, path = tempfile.mkstemp(suffix=suffix, dir=self.tmp.name)
        with open(fd, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(content)
        return path

    def test_srt_unicode_and_timing_preserved(self):
        out = self.sub.extract(str(FIXTURES / "sample.srt"))
        self.assertEqual(len(out["structure"]), 3)
        first = out["structure"][0]
        self.assertEqual((first["offset_ms"], first["duration_ms"]), (1000, 2500))
        self.assertIn("托卡马克", out["text"])

    def test_overlapping_cues_are_kept_not_merged(self):
        out = self.sub.extract(str(FIXTURES / "sample-overlap.srt"))
        self.assertEqual(len(out["structure"]), 2)
        first, second = out["structure"][:2]
        # overlap: second starts before first ends; both timings preserved
        self.assertEqual(first["offset_ms"], 1000)
        self.assertEqual(second["offset_ms"], 3000)
        self.assertLess(second["offset_ms"], first["offset_ms"] + first["duration_ms"])

    def test_empty_srt_is_rejected(self):
        with self.assertRaises(ValueError):
            self.sub.extract(self._write("", ".srt"))

    def test_malformed_timing_is_rejected(self):
        with self.assertRaises(ValueError):
            self.sub.extract(self._write("1\nnot-a-time --> also-not\nx\n", ".srt"))

    def test_no_trailing_newline_still_parses(self):
        content = "1\n00:00:00,000 --> 00:00:01,000\n末行无换行"
        out = self.sub.extract(self._write(content, ".srt"))
        self.assertEqual(len(out["structure"]), 1)
        self.assertEqual(out["text"], "末行无换行\n")

    def test_vtt_notes_and_inline_tags_stripped(self):
        out = self.sub.extract(str(FIXTURES / "sample.vtt"))
        self.assertEqual(len(out["structure"]), 3)
        self.assertNotIn("<v", out["text"])
        self.assertNotIn("dropped note", out["text"])


class TempFileFailClosedTests(unittest.TestCase):
    def test_setup_is_fail_closed_without_run_root(self):
        # Prove the shared setUp raises before creating any temp file when
        # ARCHEAXIS_RUN_ROOT is absent, instead of falling back to the system
        # temp directory. An isolated child env keeps the parent env untouched.
        child = textwrap.dedent(
            """
            import importlib.util, sys
            spec = importlib.util.spec_from_file_location("fixture_matrix", sys.argv[1])
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            case = mod.CanvasParserTests()
            try:
                case.setUp()
            except KeyError:
                sys.exit(0)
            sys.exit(2)
            """
        )
        env = {k: v for k, v in os.environ.items() if k != "ARCHEAXIS_RUN_ROOT"}
        env["TMP"] = env["TEMP"] = env["TMPDIR"] = ""
        result = subprocess.run(
            [sys.executable, "-c", child, str(Path(__file__))],
            env=env, capture_output=True, text=True, timeout=30, check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)


if __name__ == "__main__":
    unittest.main()
