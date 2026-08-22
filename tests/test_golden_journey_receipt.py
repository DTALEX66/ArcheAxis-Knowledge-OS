from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts import generate_golden_journey_receipt as receipt_generator


def test_golden_journey_receipt_cli_can_be_invoked_as_a_script() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            str(receipt_generator.ROOT / "scripts" / "generate_golden_journey_receipt.py"),
            "--help",
        ],
        cwd=receipt_generator.ROOT,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    assert completed.returncode == 0, completed.stderr
    assert "Golden Journey" in completed.stdout


def test_golden_journey_receipt_is_sha_bound_and_remains_partial(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        receipt_generator,
        "_git",
        lambda *args: (
            ""
            if args == ("status", "--porcelain")
            else "head-sha"
            if args[-1] == "HEAD"
            else "tree-sha"
        ),
    )

    receipt = receipt_generator.generate(
        tmp_path / "receipt.json",
        test_targets=receipt_generator.DEFAULT_TEST_TARGETS,
        artifact_root=tmp_path,
        runner=lambda target: {
            "target": target,
            "command": ["python", "-m", "pytest", target, "-q"],
            "status": "PASS",
            "exit_code": 0,
            "duration_seconds": 0.1,
        },
    )

    persisted = json.loads((tmp_path / "receipt.json").read_text(encoding="utf-8"))
    assert persisted == receipt
    assert receipt["commit_sha"] == "head-sha"
    assert receipt["tree_sha"] == "tree-sha"
    assert receipt["local_journey_status"] == "PASS"
    assert receipt["overall_status"] == "PARTIAL"
    assert receipt["release_gate"] == "PASS_EXTERNAL_EVIDENCE"
    assert receipt["release_authorization"] == "NOT_GRANTED_BY_THIS_RECEIPT"
    assert receipt["coverage"] == {
        "four_library_setup_restart": "PASS",
        "raw_asset_conversion_anchors": "PASS",
        "identity_bound_review": "PASS",
        "dual_learning_writeback": "PASS",
        "export_import_fresh_workspace": "PASS",
        "six_space_browser": "NOT_EXECUTED",
        "installed_desktop_restart": "NOT_EXECUTED",
        "tier_a_ingestion_matrix": "NOT_EXECUTED",
        "three_distribution_lifecycle": "PASS_EXTERNAL_EVIDENCE",
    }


def test_golden_journey_receipt_rejects_output_outside_artifact_root(
    tmp_path: Path,
) -> None:
    with pytest.raises(ValueError, match="must be stored"):
        receipt_generator.generate(
            tmp_path / "outside.json",
            test_targets=(),
            artifact_root=tmp_path / "artifacts",
        )


def test_golden_journey_receipt_rejects_dirty_worktree(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        receipt_generator,
        "_git",
        lambda *args: " M app/main.py" if args == ("status", "--porcelain") else "sha",
    )

    with pytest.raises(RuntimeError, match="clean worktree"):
        receipt_generator.generate(
            tmp_path / "receipt.json",
            test_targets=(),
            artifact_root=tmp_path,
        )
