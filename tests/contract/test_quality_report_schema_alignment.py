"""X04 regression: worker_quality report is schema-aligned and does not strip.

Locks the X04 contract items for worker_quality that were reported as defects
in the REUSE-FIRST taskpack and are verified fixed on this branch:
1. the top-level loss_receipt block must be a valid instance of BOTH the
   inline quality-report definition and the shared loss-receipt schema;
2. normalize=none must mean identity (no strip / no whitespace collapse for
   CER); a leading space is a real character difference;
3. loss information must accumulate per sample, never overwrite across runs
   (each row's refs point at its own byte snapshot).
"""

import importlib.util
import json
import tempfile
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]


def _quality():
    spec = importlib.util.spec_from_file_location(
        "worker_quality_x04", ROOT / "services/python-workers/evaluation/worker_quality.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _schema(name: str) -> dict:
    return json.loads(
        (ROOT / f"packages/contracts/v1/{name}.schema.json").read_text(encoding="utf-8")
    )


def test_quality_report_matches_its_schema_and_loss_receipt_is_shared_compatible(tmp_path):
    quality = _quality()
    prediction = tmp_path / "p.txt"
    gold = tmp_path / "g.txt"
    prediction.write_text(" ab\n", encoding="utf-8")
    gold.write_text("ab", encoding="utf-8")
    report = quality.evaluate(
        prediction, gold, sample_id="x04", run_id="r1", normalize="none"
    )
    assert not list(Draft202012Validator(_schema("quality-report")).iter_errors(report))
    # the embedded loss_receipt must also be a valid instance of the shared
    # loss-receipt schema (minimal instance: params + loss_note present).
    assert not list(
        Draft202012Validator(_schema("loss-receipt")).iter_errors(report["loss_receipt"])
    )


def test_normalize_none_does_not_strip_or_collapse(tmp_path):
    quality = _quality()
    prediction = tmp_path / "p.txt"
    gold = tmp_path / "g.txt"
    # Leading space is a genuine code-point difference when normalize=none.
    prediction.write_text(" a", encoding="utf-8")
    gold.write_text("a", encoding="utf-8")
    report = quality.evaluate(
        prediction, gold, sample_id="s", run_id="r", normalize="none"
    )
    cer = next(row for row in report["rows"] if row["metric"] == "cer")
    assert cer["status"] == "measured"
    assert cer["value"] == 1.0
    assert report["loss_receipt"]["params"]["normalize"] == "none"


def test_sample_losses_accumulate_without_cross_sample_overwrite(tmp_path):
    quality = _quality()
    reports = []
    for marker in ("alpha", "beta"):
        prediction = tmp_path / f"p-{marker}.txt"
        gold = tmp_path / f"g-{marker}.txt"
        prediction.write_text(marker, encoding="utf-8")
        gold.write_text(marker, encoding="utf-8")
        reports.append(
            quality.evaluate(
                prediction, gold, sample_id=marker, run_id=f"run-{marker}", normalize="none"
            )
        )
    for report, marker in zip(reports, ("alpha", "beta")):
        for row in report["rows"]:
            assert row["sample_id"] == marker
    # The two reports describe different byte snapshots; nothing from the first
    # report leaks into the second (accumulation is per-report, not global).
    first_pred = reports[0]["rows"][0]["prediction_ref"]["sha256"]
    second_pred = reports[1]["rows"][0]["prediction_ref"]["sha256"]
    assert first_pred != second_pred
