"""BULK-0907 P08: bulk text decode / line-anchor cases (worker_text pure functions).

Builds on the R2 independent-coordinate assertions but targets gaps not covered by
tests/workers/test_text_ndjson.py: Unicode line/paragraph separators (U+2028/U+2029,
NEL U+0085, VT U+000B, FF U+000C), zero-width non-separators, cp1252-only fallback,
all-invalid fallback precision, and the 5000-line cap boundary. Expectations are
hand-written; they are never copied from the parser output.
"""

import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKER = ROOT / "services/python-workers/document/worker_text.py"


def _load_worker():
    spec = importlib.util.spec_from_file_location("worker_text", WORKER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class DecodeAnchorBulkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.worker = _load_worker()

    def _case(self, raw: bytes, expected_text: str, expected_decode: str, ranges: list):
        text, note = self.worker.decode_bytes(raw, source="<bulk>")
        self.assertEqual(text, expected_text)
        self.assertEqual(note["encoding"], expected_decode)
        anchors = self.worker.line_anchors(text)
        self.assertEqual([(a["char_start"], a["char_end"]) for a in anchors], ranges)
        self.assertEqual([a["path"] for a in anchors],
                         [[f"line-{i}"] for i in range(1, len(ranges) + 1)])
        return text

    def test_unicode_line_and_paragraph_separators_are_anchored(self):
        # U+2028 LINE SEPARATOR and U+2029 PARAGRAPH SEPARATOR split lines and are
        # kept at the end of the line they terminate (splitlines keepends).
        raw = "a\u2028b\u2029c".encode("utf-8")
        self._case(raw, "a\u2028b\u2029c", "utf-8", [(0, 2), (2, 4), (4, 5)])

    def test_nel_vt_ff_are_unicode_line_breaks(self):
        # NEL U+0085, VT U+000B and FF U+000C are line breaks for str.splitlines;
        # each separator is kept with the line it terminates.
        raw = "x\u0085y\u000bz\u000cw".encode("utf-8")
        text, note = self.worker.decode_bytes(raw, source="<bulk>")
        self.assertEqual(note["encoding"], "utf-8")
        anchors = self.worker.line_anchors(text)
        self.assertEqual([(a["char_start"], a["char_end"]) for a in anchors],
                         [(0, 2), (2, 4), (4, 6), (6, 7)])

    def test_zero_width_space_is_not_a_separator(self):
        raw = "a\u200bb".encode("utf-8")
        self._case(raw, "a\u200bb", "utf-8", [(0, 3)])

    def test_crlf_and_lone_cr_anchor_precisely(self):
        raw = b"a\r\nb\rc\n"
        self._case(raw, "a\r\nb\rc\n", "utf-8", [(0, 3), (3, 5), (5, 7)])

    def test_cp1252_only_fallback_is_used_when_utf8_and_gbk_fail(self):
        # 0x82 is invalid UTF-8 and invalid GBK (no trail byte), valid cp1252 (U+201A).
        text, note = self.worker.decode_bytes(b"\x82", source="<bulk>")
        self.assertEqual(note["encoding"], "cp1252")
        self.assertEqual(text, "\u201a")

    def test_all_invalid_bytes_fall_to_replace_with_exact_replacement(self):
        text, note = self.worker.decode_bytes(b"\x81\xff\x81", source="<bulk>")
        self.assertEqual(note["encoding"], "utf-8-replace")
        self.assertEqual(text, "\ufffd\ufffd\ufffd")
        self.assertIn("U+FFFD", note["loss_note"])

    def test_cap_boundary_keeps_5000_anchors_and_reports_loss(self):
        lines = [f"l{i}" for i in range(5001)]
        text = "\n".join(lines) + "\n"
        anchors = self.worker.line_anchors(text)  # default cap 5000
        self.assertEqual(len(anchors), 5000)
        self.assertEqual(anchors[-1]["path"], ["line-5000"])
        total = len(text.splitlines(keepends=True))
        self.assertEqual(total, 5001)
        # independent anchor length check: every anchor covers its own line length
        offsets = [a["char_start"] for a in anchors]
        self.assertEqual(offsets[0], 0)
        self.assertEqual(offsets[-1], sum(len(f"l{i}") + 1 for i in range(4999)))

    def test_extract_loss_receipt_rounds_to_capped_coverage(self):
        with tempfile.TemporaryDirectory(dir=os.environ["ARCHEAXIS_RUN_ROOT"]) as tmp:
            path = Path(tmp) / "big.txt"
            lines = [f"x{i}" for i in range(5001)]
            path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
            out = self.worker.extract(str(path))
        receipt = out["loss_receipt"]
        self.assertEqual(receipt["covered"], 5000)
        self.assertEqual(receipt["total"], 5001)
        self.assertIn("capped at 5000", receipt["loss_note"])
        self.assertEqual(len(out["structure"]), 5000)
        payload = {"kind": "line", "path": ["line-1"], "char_start": 0, "char_end": 3}
        self.assertEqual(out["structure"][0], payload)

    def test_document_json_roundtrip_preserves_unicode_and_coordinates(self):
        raw = "中文😀\u2028next".encode("utf-8")
        with tempfile.TemporaryDirectory(dir=os.environ["ARCHEAXIS_RUN_ROOT"]) as tmp:
            path = Path(tmp) / "uni.txt"
            path.write_bytes(raw)
            out = self.worker.extract(str(path))
            text = out["text"]
            self.assertEqual(text, "中文😀\u2028next")
            structure = out["structure"]
            self.assertEqual([(a["char_start"], a["char_end"]) for a in structure],
                             [(0, 4), (4, 8)])
            # JSON-encode/decode must keep character offsets (unicode code points).
            decoded = json.loads(json.dumps(out, ensure_ascii=False))
            self.assertEqual(decoded["structure"], out["structure"])


if __name__ == "__main__":
    unittest.main()
