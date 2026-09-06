"""Actual document output must satisfy the shared receipt schema, not a fixture-only contract."""
import importlib.util
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = json.loads((ROOT / "packages/contracts/v1/loss-receipt.schema.json").read_text(encoding="utf-8"))
VALIDATOR = Draft202012Validator(SCHEMA)


def test_actual_bom_and_capped_worker_receipt_matches_schema(tmp_path):
    spec = importlib.util.spec_from_file_location("receipt_worker", ROOT / "services/python-workers/document/worker_text.py")
    worker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(worker)
    path = tmp_path / "source.txt"
    path.write_bytes(b"\xef\xbb\xbf" + "行😀\r\n".encode() * 5001)
    receipt = worker.extract(str(path))["loss_receipt"]
    VALIDATOR.validate(receipt)
    assert (receipt["covered"], receipt["total"]) == (5000, 5001)
    assert len(receipt["losses"]) == 2


@pytest.mark.parametrize("extra", [
    {"covered": None}, {"total": None}, {"coverage": None}, {"losses": None},
    {"covered": 1}, {"covered": -1, "total": 1, "coverage": 1},
    {"covered": True, "total": 1, "coverage": 1}, {"coverage": 1.1},
    {"covered": 9007199254740992, "total": 9007199254740992, "coverage": 1},
    {"covergae": 1}, {"losses": [""]}, {"params": []}, {"engine_version": " "},
])
def test_schema_rejects_loss_accounting_shape_errors(extra):
    receipt = {"engine": "worker", "engine_version": "1", "params": {}, "loss_note": None, **extra}
    assert list(VALIDATOR.iter_errors(receipt))


def test_nullable_note_is_required_and_mathematical_integer_counts_are_accepted():
    receipt = {"engine": "worker", "engine_version": "1", "params": {}}
    assert list(VALIDATOR.iter_errors(receipt))
    receipt.update(loss_note=None, covered=1.0, total=1e0, coverage=1)
    VALIDATOR.validate(receipt)
