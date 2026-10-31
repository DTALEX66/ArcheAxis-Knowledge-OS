"""Pure-logic tests for the pinned build-time transcript model fetch.

No network is used: a local file URL stands in for the pinned Hugging Face revision, and the
fixed manifest is replaced with one synthetic small file for the transfer assertions.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/release/fetch_asr_model.py"
SPEC = importlib.util.spec_from_file_location("fetch_asr_model_under_test", SCRIPT)
probe = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(probe)


def test_manifest_pins_the_required_ctranslate2_files():
    assert {"model.bin", "config.json", "tokenizer.json", "vocabulary.txt"} <= set(probe.FILES)
    assert len(probe.REVISION) == 40 and all(char in "0123456789abcdef" for char in probe.REVISION)
    for name, expected in probe.FILES.items():
        assert isinstance(expected["bytes"], int) and 0 < expected["bytes"] <= probe.MAX_FILE_BYTES
        assert len(expected["sha256"]) == 64
        assert expected["sha256"] == expected["sha256"].lower()
    assert probe.LICENSE["code_license"] == "MIT"


def test_download_verify_reuse_and_receipt(tmp_path, monkeypatch):
    payload = b"synthetic ctranslate2 weights"
    donor = tmp_path / "donor"
    donor.mkdir()
    (donor / "model.bin").write_bytes(payload)
    monkeypatch.setattr(probe, "FILES", {"model.bin": {
        "bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}})
    monkeypatch.setattr(probe, "BASE_URL", donor.as_uri() + "/{name}")
    out = tmp_path / "models" / "faster-whisper-base"
    receipt = tmp_path / "receipt.json"

    first = probe.fetch_model(out, receipt)
    assert first["downloaded"] == 1 and first["reused"] == 0
    assert first["network_performed"] is True and first["runtime_download"] is False
    assert (out / "model.bin").read_bytes() == payload
    on_disk = json.loads(receipt.read_text(encoding="utf-8"))
    assert on_disk["schema"] == "archeaxis.asr-model-fetch/v1"
    assert on_disk["files"]["model.bin"]["state"] == "DOWNLOADED_VERIFIED"
    assert on_disk["revision"] == probe.REVISION

    second = probe.fetch_model(out, receipt)
    assert second["reused"] == 1 and second["downloaded"] == 0
    assert second["network_performed"] is False


def test_corrupt_existing_file_is_refused_without_overwrite(tmp_path, monkeypatch):
    payload = b"expected"
    donor = tmp_path / "donor"
    donor.mkdir()
    (donor / "model.bin").write_bytes(payload)
    monkeypatch.setattr(probe, "FILES", {"model.bin": {
        "bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}})
    monkeypatch.setattr(probe, "BASE_URL", donor.as_uri() + "/{name}")
    out = tmp_path / "model"
    out.mkdir()
    (out / "model.bin").write_bytes(b"corrupt")
    with pytest.raises(ValueError, match="size mismatch"):
        probe.fetch_model(out)
    assert (out / "model.bin").read_bytes() == b"corrupt"


def test_output_that_is_a_file_is_refused(tmp_path):
    target = tmp_path / "model"
    target.write_bytes(b"not a directory")
    with pytest.raises(ValueError, match="not a directory"):
        probe.fetch_model(target)
