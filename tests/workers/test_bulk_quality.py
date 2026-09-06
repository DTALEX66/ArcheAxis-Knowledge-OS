"""BULK-0907 P15: quality metric and report validation cases (worker_quality.py).

CER/WER expectations are hand-computed code-point/token edit distances over gold
length; nothing is copied from worker output. Empty gold is unmeasured (no fake
zero). Normalization lower uses casefold. Report metric semantics are enforced by
validate_report_metrics beyond the JSON Schema (non-finite, non-measured value,
reversed interval, unknown status).
"""

import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
QUALITY = ROOT / "services/python-workers/evaluation/worker_quality.py"


def _load():
    spec = importlib.util.spec_from_file_location("worker_quality", QUALITY)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class QualityBulkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.quality = _load()

    def _evaluate(self, prediction: str, gold: str, *, normalize: str = "none"):
        with tempfile.TemporaryDirectory(dir=os.environ["ARCHEAXIS_RUN_ROOT"]) as tmp:
            pred = Path(tmp) / "p.txt"
            ref = Path(tmp) / "g.txt"
            pred.write_text(prediction, encoding="utf-8")
            ref.write_text(gold, encoding="utf-8")
            return self.quality.evaluate(pred, ref, sample_id="s", run_id="r", normalize=normalize)

    def _row(self, report: dict, metric: str) -> dict:
        return next(row for row in report["rows"] if row["metric"] == metric)

    def test_hand_computed_substitution_cer(self):
        report = self._evaluate("abcd", "abxd")  # one substitution over 4 gold chars
        cer = self._row(report, "cer")
        self.assertEqual(cer["status"], "measured")
        self.assertEqual(cer["value"], 1 / 4)

    def test_empty_gold_is_unmeasured_without_fake_zero(self):
        report = self._evaluate("anything", "")
        for metric in ("cer", "wer"):
            row = self._row(report, metric)
            self.assertEqual(row["status"], "unmeasured")
            self.assertIsNone(row["value"])
            self.assertIn("no fake value", row["note"])

    def test_normalize_lower_casefold_reaches_zero(self):
        report = self._evaluate("ABC", "abc", normalize="lower")
        self.assertEqual(self._row(report, "cer")["value"], 0.0)

    def test_single_whitespace_token_gold_is_still_measured(self):
        # Non-empty gold always has >=1 whitespace token, so WER is measured;
        # WER unmeasured is reserved for an empty gold file (covered above).
        report = self._evaluate("预测", "参考")
        cer = self._row(report, "cer")
        wer = self._row(report, "wer")
        self.assertEqual(cer["status"], "measured")
        self.assertEqual(cer["value"], 1.0)  # 2 char substitutions over 2 gold chars
        self.assertEqual(wer["status"], "measured")
        self.assertEqual(wer["value"], 1.0)  # one token substitution over one gold token

    def test_astral_emoji_counts_as_one_code_point(self):
        report = self._evaluate("\U0001f600x", "\U0001f600x")
        self.assertEqual(self._row(report, "cer")["value"], 0.0)
        # insertion of one extra astral character over two gold chars
        report2 = self._evaluate("\U0001f600x\U0001f601", "\U0001f600x")
        self.assertEqual(self._row(report2, "cer")["value"], 0.5)

    def test_rows_carry_reference_hashes_for_recomputation(self):
        report = self._evaluate("预测文本", "参考文本")
        row = self._row(report, "cer")
        self.assertEqual(len(row["prediction_ref"]["sha256"]), 64)
        self.assertEqual(len(row["gold_ref"]["sha256"]), 64)

    def test_validate_report_metrics_rejects_invalid_rows(self):
        row_measured = {"metric": "cer", "sample_id": "s", "status": "measured",
                        "value": 0.1, "unit": "error_rate"}
        base = {"schema": "archeaxis.quality-report/v1", "report_id": "r", "run_id": "run",
                "engine": {"name": "e", "version": "v"}, "rows": [], "generated_at": "x"}
        measured_null = {**base, "rows": [{**row_measured, "value": None}]}
        with self.assertRaises(ValueError):
            self.quality.validate_report_metrics(measured_null)
        measured_nan = {**base, "rows": [{**row_measured, "value": float("nan")}]}
        with self.assertRaises(ValueError):
            self.quality.validate_report_metrics(measured_nan)
        unmeasured_with_value = {**base, "rows": [{**row_measured, "status": "unmeasured"}]}
        with self.assertRaises(ValueError):
            self.quality.validate_report_metrics(unmeasured_with_value)
        reversed_interval = {**base, "rows": [{**row_measured, "interval": [0.9, 0.1]}]}
        with self.assertRaises(ValueError):
            self.quality.validate_report_metrics(reversed_interval)
        unknown = {**base, "rows": [{**row_measured, "status": "guessed"}]}
        with self.assertRaises(ValueError):
            self.quality.validate_report_metrics(unknown)
        # error rates above one are legitimate and must not be rejected
        high = {**base, "rows": [{**row_measured, "value": 9.0}]}
        self.quality.validate_report_metrics(high)

    def test_main_boundary_rejects_missing_files(self):
        # Real process entrypoint: two missing files must exit non-zero with an error envelope.
        result = subprocess.run(
            [sys.executable, "-B", str(QUALITY), "no-pred.txt", "no-gold.txt"],
            capture_output=True, text=True, encoding="utf-8", timeout=60,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn('"error"', result.stdout)


if __name__ == "__main__":
    unittest.main()
