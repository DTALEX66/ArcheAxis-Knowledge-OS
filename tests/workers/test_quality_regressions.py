"""Regression coverage for byte-faithful metrics and complete loss receipts."""

import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]


def load_worker(name, relative_path):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


quality = load_worker("worker_quality", "services/python-workers/evaluation/worker_quality.py")
document = load_worker("worker_text", "services/python-workers/document/worker_text.py")


class WorkerQualityRegressions(unittest.TestCase):
    def setUp(self):
        # The project launcher owns the temporary directory, including on Windows.
        self.tmp = tempfile.TemporaryDirectory(dir=os.environ["ARCHEAXIS_RUN_ROOT"])
        self.addCleanup(self.tmp.cleanup)
        self.prediction = Path(self.tmp.name) / "prediction.txt"
        self.gold = Path(self.tmp.name) / "gold.txt"

    def evaluate(self, prediction, gold, normalize="none"):
        self.prediction.write_bytes(prediction)
        self.gold.write_bytes(gold)
        return quality.evaluate(self.prediction, self.gold, sample_id="sample", run_id="test", normalize=normalize)

    def test_none_preserves_boundary_whitespace_bom_and_line_endings(self):
        cases = [(b"a", b" a ", 0.666667), (b"a", b"\xef\xbb\xbfa", 0.5),
                 (b"a\nb", b"a\r\nb", 0.25), (b"a", b"a\r", 0.5)]
        for prediction, gold, expected_cer in cases:
            with self.subTest(gold=gold):
                report = self.evaluate(prediction, gold)
                self.assertEqual(report["rows"][0]["value"], expected_cer)

    def test_whitespace_gold_measures_cer_but_not_wer(self):
        cer, wer = self.evaluate(b"", b" \t\r\n")["rows"]
        self.assertEqual((cer["status"], cer["value"]), ("measured", 1.0))
        self.assertEqual((wer["status"], wer["value"]), ("unmeasured", None))

    def test_empty_gold_has_no_fake_metrics(self):
        for row in self.evaluate(b"prediction", b"")["rows"]:
            self.assertEqual((row["status"], row["value"]), ("unmeasured", None))

    def test_actual_report_passes_schema_and_extra_fields_fail(self):
        import jsonschema

        schema = json.loads((ROOT / "packages/contracts/v1/quality-report.schema.json").read_text(encoding="utf-8"))
        report = self.evaluate(b"x", b" x ")
        jsonschema.Draft202012Validator(schema).validate(report)
        report["unexpected"] = "must reject"
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.Draft202012Validator(schema).validate(report)

    def test_lower_casefolds_without_stripping(self):
        report = self.evaluate(b"A", b" a ", normalize="lower")
        self.assertEqual(report["rows"][0]["value"], 0.666667)

    def test_invalid_encoding_fails_in_both_inputs_and_cli(self):
        for prediction, gold in [(b"\xff", b"a"), (b"a", b"\xff")]:
            with self.subTest(prediction=prediction):
                with self.assertRaises(UnicodeDecodeError):
                    self.evaluate(prediction, gold)
                result = subprocess.run([sys.executable, "-B", quality.__file__,
                                         str(self.prediction), str(self.gold)],
                                        capture_output=True, text=True, check=False)
                self.assertEqual(result.returncode, 1)
                self.assertIn("error", json.loads(result.stdout))
                self.assertNotIn("rows", json.loads(result.stdout))

    def test_hash_identifies_bytes_used_even_when_source_changes_after_read(self):
        original_read = Path.read_bytes
        self.prediction.write_bytes(b"a")
        self.gold.write_bytes(b"a")

        def read_then_change(path):
            data = original_read(path)
            if path == self.prediction:
                path.write_bytes(b"changed after snapshot")
            return data

        with patch.object(Path, "read_bytes", read_then_change):
            report = quality.evaluate(self.prediction, self.gold, sample_id="s", run_id="r", normalize="none")
        for row in report["rows"]:
            self.assertEqual(row["value"], 0)
            self.assertEqual(row["prediction_ref"]["sha256"], hashlib.sha256(b"a").hexdigest())

    def test_receipt_records_reproducible_decode_and_normalization(self):
        params = self.evaluate(b"a", b"a")["loss_receipt"]["params"]
        self.assertEqual(params.get("encoding"), "utf-8")
        self.assertEqual(params.get("decode_errors"), "strict")
        for field in ("bom", "line_endings", "whitespace"):
            self.assertEqual(params.get(field), "preserve")
        self.assertEqual(params.get("normalize"), "none")

    def test_bom_and_anchor_limit_report_both_losses_for_all_line_separators(self):
        for separator in ("\n", "\r", "\r\n", "\u2028"):
            with self.subTest(separator=separator):
                content = separator.join(["x"] * 5001)
                self.prediction.write_bytes(b"\xef\xbb\xbf" + content.encode("utf-8"))
                result = document.extract(str(self.prediction))
                receipt = result["loss_receipt"]
                self.assertIn("BOM", receipt["loss_note"])
                self.assertIn("capped", receipt["loss_note"])
                self.assertEqual((receipt.get("covered"), receipt.get("total")), (5000, 5001))
                self.assertAlmostEqual(receipt.get("coverage", -1), 5000 / 5001)
                self.assertEqual(len(receipt.get("losses", [])), 2)
                self.assertEqual(result["text"], content)
                self.assertEqual(len(result["structure"]), 5000)
                self.assertEqual(result["structure"][-1]["char_end"], 5000 * (1 + len(separator)))

    def test_exact_anchor_limit_with_final_newline_is_not_truncated(self):
        self.prediction.write_bytes(b"x\n" * 5000)
        receipt = document.extract(str(self.prediction))["loss_receipt"]
        self.assertNotIn("capped", receipt["loss_note"])
        self.assertEqual((receipt.get("covered"), receipt.get("total"), receipt.get("coverage")),
                         (5000, 5000, 1.0))

    def test_empty_document_has_explicit_zero_anchor_coverage(self):
        self.prediction.write_bytes(b"")
        receipt = document.extract(str(self.prediction))["loss_receipt"]
        self.assertEqual((receipt.get("covered"), receipt.get("total"), receipt.get("coverage")),
                         (0, 0, 1.0))
        self.assertIn("zero-line coverage", receipt["loss_note"])


if __name__ == "__main__":
    unittest.main()
