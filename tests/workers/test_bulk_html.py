"""BULK-0907 P12: static HTML snapshot extraction cases (web/worker_html.py).

Uses one real saved snapshot (tests/fixtures/vnext/documents/sample-page.html) plus
synthetic static HTML. Assertions verify scripts/styles/templates are never executed
or projected, block separation and anchors, link capture, entity handling, encoding
fallback, and tolerance of malformed input. No network, no dynamic DOM.
"""

import importlib.util
import os
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HTML_WORKER = ROOT / "services/python-workers/web/worker_html.py"
SNAPSHOT = ROOT / "tests/fixtures/vnext/documents/sample-page.html"


def _load_worker():
    spec = importlib.util.spec_from_file_location("worker_html", HTML_WORKER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class HtmlBulkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.worker = _load_worker()

    def _write(self, content: str) -> str:
        fd, path = tempfile.mkstemp(suffix=".html", dir=os.environ["ARCHEAXIS_RUN_ROOT"])
        with open(fd, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(content)
        return path

    def _bytes(self, raw: bytes) -> str:
        fd, path = tempfile.mkstemp(suffix=".html", dir=os.environ["ARCHEAXIS_RUN_ROOT"])
        os.close(fd)
        Path(path).write_bytes(raw)
        return path

    def test_real_static_snapshot_extracts_title_and_body_text(self):
        out = self.worker.extract(str(SNAPSHOT))
        self.assertEqual(out["title"], "托卡马克等离子体约束演示页")
        self.assertIn("托卡马克", out["text"])
        self.assertIn("1e20", out["text"])
        self.assertIsInstance(out["links"], list)
        self.assertTrue(out["structure"])

    def test_script_style_template_svg_are_never_projected(self):
        content = (
            "<html><head><title>静</title></head><body>"
            "<script>document.write('should-not-run')</script>"
            "<style>.x{color:red}</style><template><p>tmpl</p></template>"
            "<svg><text>svg-text</text></svg>"
            "<p>真实段落</p></body></html>"
        )
        out = self.worker.extract(self._write(content))
        self.assertEqual(out["title"], "静")
        self.assertNotIn("should-not-run", out["text"])
        self.assertNotIn("tmpl", out["text"])
        self.assertNotIn("svg-text", out["text"])
        self.assertIn("真实段落", out["text"])

    def test_links_capture_href_and_visible_text(self):
        content = '<html><body><a href="/docs/a.md">链接文本</a><p>正文</p></body></html>'
        out = self.worker.extract(self._write(content))
        self.assertTrue(out["links"])
        self.assertEqual(out["links"][0]["href"], "/docs/a.md")
        self.assertIn("链接文本", out["links"][0]["text"])

    def test_block_separation_and_anchor_coordinates(self):
        content = "<html><body><p>第一段</p><p>第二段</p></body></html>"
        out = self.worker.extract(self._write(content))
        self.assertEqual(out["text"], "第一段\n\n第二段")
        self.assertEqual([(a["char_start"], a["char_end"]) for a in out["structure"]],
                         [(0, 3), (5, 8)])

    def test_html_entity_nbsp_kept_as_nbsp_not_lost(self):
        content = "<html><body><p>a&nbsp;&amp;&nbsp;b</p></body></html>"
        out = self.worker.extract(self._write(content))
        self.assertEqual(out["text"], "a\u00a0&\u00a0b")

    def test_malformed_unclosed_html_does_not_raise_and_keeps_title(self):
        content = "<html><head><title>破碎</title></head><body><p>保留段</p>"
        out = self.worker.extract(self._write(content))
        self.assertEqual(out["title"], "破碎")
        self.assertIn("保留段", out["text"])

    def test_empty_body_yields_empty_projection(self):
        content = "<html><head><title>空</title></head><body></body></html>"
        out = self.worker.extract(self._write(content))
        self.assertEqual(out["text"], "")
        self.assertEqual(out["structure"], [])

    def test_non_utf8_snapshot_uses_replace_and_marks_encoding(self):
        out = self.worker.extract(self._bytes(b"\xff\xfe<b>hi</b>"))
        self.assertEqual(out["loss_receipt"]["params"]["encoding"], "utf-8-replace")


if __name__ == "__main__":
    unittest.main()
