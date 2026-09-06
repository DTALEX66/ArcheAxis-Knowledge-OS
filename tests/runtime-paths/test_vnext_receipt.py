import copy

import pytest


def test_receipt_rejects_stale_identity_failed_or_missing_steps():
    from scripts.ci.check_vnext_receipt import validate

    steps = {f"{i:02}_step": "PASS: checked" for i in range(1, 13)}
    receipt = {"schema": "archeaxis.vnext/v01-closed-loop-receipt", "schema_version": 2,
               "source_commit": "a" * 40, "run_id": "current", "total_steps": 12,
               "steps": steps, "manifest_sha256": "b" * 64}
    validate(receipt, "a" * 40, "current")
    for key, value in (("source_commit", "c" * 40), ("run_id", "previous"),
                       ("total_steps", 0), ("steps", {"01_step": "PASS: old"}),
                       ("steps", {**steps, "05_step": "FAIL: failure"})):
        bad = copy.deepcopy(receipt)
        bad[key] = value
        with pytest.raises(ValueError):
            validate(bad, "a" * 40, "current")
