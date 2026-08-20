from __future__ import annotations

import json
from pathlib import Path

from scripts.generate_current_reports import DEFAULT_TASKPACK_BASELINE, generate


def test_current_report_generator_emits_exact_sha_bound_reports(tmp_path: Path) -> None:
    generate(tmp_path, DEFAULT_TASKPACK_BASELINE)

    baseline = json.loads((tmp_path / "CLOUD_BASELINE.json").read_text(encoding="utf-8"))
    exact = json.loads((tmp_path / "EXACT_SHA_VERIFICATION.json").read_text(encoding="utf-8"))
    matrix = json.loads((tmp_path / "CURRENT_CAPABILITY_MATRIX.json").read_text(encoding="utf-8"))

    assert baseline["commit_sha"] == exact["commit_sha"]
    assert baseline["tree_sha"] == exact["tree_sha"]
    assert baseline["taskpack_baseline_sha"] == DEFAULT_TASKPACK_BASELINE
    assert matrix["overall_status"] == "PARTIAL"
    assert matrix["release_gate"] == "NOT_EXECUTED"
