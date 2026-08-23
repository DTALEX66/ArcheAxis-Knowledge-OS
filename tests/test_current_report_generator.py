from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import generate_current_reports as report_generator
from scripts.generate_current_reports import (
    DEFAULT_OUTPUT_DIR,
    DEFAULT_RELEASE_EVIDENCE,
    DEFAULT_TASKPACK_BASELINE,
    ROOT,
    generate,
    load_release_evidence,
)


def test_current_report_generator_emits_exact_sha_bound_reports(tmp_path: Path) -> None:
    generate(
        tmp_path,
        DEFAULT_TASKPACK_BASELINE,
        release_evidence=DEFAULT_RELEASE_EVIDENCE,
    )

    baseline = json.loads((tmp_path / "CLOUD_BASELINE.json").read_text(encoding="utf-8"))
    exact = json.loads((tmp_path / "EXACT_SHA_VERIFICATION.json").read_text(encoding="utf-8"))
    matrix = json.loads((tmp_path / "CURRENT_CAPABILITY_MATRIX.json").read_text(encoding="utf-8"))

    assert baseline["commit_sha"] == exact["commit_sha"]
    assert baseline["tree_sha"] == exact["tree_sha"]
    assert baseline["taskpack_baseline_sha"] == DEFAULT_TASKPACK_BASELINE
    assert baseline["release"]["state"] == "stable"
    assert baseline["release"]["tag"] == "v0.6.9"
    assert baseline["release"]["commit_sha"] == (
        "de5b5ba6efde2f306d029725c046b56d91226e4c"
    )
    assert matrix["overall_status"] == "PARTIAL"
    assert matrix["release_gate"] == "PASS"
    assert matrix["capabilities"]["windows_setup_green_portable_lifecycle"] == (
        "PASS"
    )
    assert matrix["capabilities"]["six_space_ui_real_data"] == "PARTIAL"
    assert matrix["release_evidence"]["verification_ci_run_id"] == 32622348279
    assert matrix["release_evidence"]["release_run_id"] == 32623033058


def test_default_current_report_output_is_an_ignored_project_artifact() -> None:
    assert DEFAULT_OUTPUT_DIR == ROOT / ".hermes" / "task-artifacts" / "current-reports"


def test_release_evidence_loader_rejects_equal_ci_and_release_runs(
    tmp_path: Path,
) -> None:
    payload = json.loads(DEFAULT_RELEASE_EVIDENCE.read_text(encoding="utf-8"))
    payload["runs"]["release"]["id"] = payload["runs"]["verification_ci"]["id"]
    invalid = tmp_path / "invalid-release-evidence.json"
    invalid.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="must differ"):
        load_release_evidence(invalid)


def test_current_reports_do_not_claim_exact_match_for_a_dirty_worktree(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    values = {
        ("rev-parse", "HEAD"): "a" * 40,
        ("rev-parse", "HEAD^{tree}"): "b" * 40,
        ("rev-parse", "origin/main"): "a" * 40,
        ("status", "--porcelain"): " M app/main.py",
        ("remote", "get-url", "origin"): "https://example.invalid/repo.git",
        ("branch", "--show-current"): "codex/example",
    }
    monkeypatch.setattr(report_generator, "_git", lambda *args: values[args])

    generate(tmp_path, DEFAULT_TASKPACK_BASELINE, release_evidence=None)

    baseline = json.loads((tmp_path / "CLOUD_BASELINE.json").read_text())
    exact = json.loads((tmp_path / "EXACT_SHA_VERIFICATION.json").read_text())
    assert baseline["worktree_clean"] is False
    assert baseline["head_matches_origin_main"] is False
    assert baseline["release"] == {
        "version": "0.6.9",
        "state": "development",
        "evidence_level": "NOT_EXECUTED",
    }
    assert exact["worktree_clean"] is False
    assert exact["match"] is False
