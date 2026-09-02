from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import generate_golden_journey_receipt as receipt_generator
from scripts.generate_current_reports import HISTORICAL_RELEASE_EVIDENCE


def test_golden_journey_runner_uses_project_local_short_basetemp(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(receipt_generator, "_project_runtime_root", lambda: tmp_path)
    monkeypatch.setattr(
        receipt_generator.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout="", stderr=""),
    )

    result = receipt_generator._run_pytest("tests/test_example.py::test_example")

    command = result["command"]
    assert "--basetemp" in command
    basetemp = Path(command[command.index("--basetemp") + 1])
    assert basetemp.parent == tmp_path
    assert basetemp.name.startswith("g-")


def test_golden_journey_runtime_root_belongs_to_the_current_worktree(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(receipt_generator, "ROOT", tmp_path)

    assert receipt_generator._project_runtime_root() == (
        tmp_path / ".hermes" / "task-runtime"
    )


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
        release_evidence=HISTORICAL_RELEASE_EVIDENCE,
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


def test_golden_journey_default_does_not_promote_historical_release_evidence(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        receipt_generator,
        "_git",
        lambda *args: "" if args == ("status", "--porcelain") else "sha",
    )

    receipt = receipt_generator.generate(
        tmp_path / "receipt.json",
        test_targets=(),
        artifact_root=tmp_path,
    )

    assert receipt["release_gate"] == "NOT_EXECUTED"
    assert receipt["release_evidence"] is None
    assert receipt["coverage"]["three_distribution_lifecycle"] == "NOT_EXECUTED"


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
