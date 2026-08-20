from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import generate_golden_journey_receipt as receipt_generator


def test_golden_journey_receipt_is_sha_bound_and_remains_partial(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        receipt_generator,
        "_git",
        lambda *args: "head-sha" if args[-1] == "HEAD" else "tree-sha",
    )

    receipt = receipt_generator.generate(
        tmp_path / "receipt.json",
        test_targets=("tests/test_product_journey.py::test_one",),
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
    assert receipt["release_gate"] == "NOT_EXECUTED"
    assert receipt["release_authorization"] == "NOT_GRANTED_BY_THIS_RECEIPT"


def test_golden_journey_receipt_rejects_output_outside_artifact_root(
    tmp_path: Path,
) -> None:
    with pytest.raises(ValueError, match="must be stored"):
        receipt_generator.generate(
            tmp_path / "outside.json",
            test_targets=(),
            artifact_root=tmp_path / "artifacts",
        )
