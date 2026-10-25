"""The transcript model is packaged by explicit donor, with identity and licence recorded.

A candidate that ships no model fails every media job by name; a candidate that ships one
without recording which weights and which licence it carries is worse. These tests pin the
staging step itself: byte-for-byte copy, SHA-256 per file, the identity file the worker reads,
and the refusals that keep an arbitrary directory from becoming "a model".
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
STAGER = ROOT / "scripts/release/stage_backend_runtime.py"


def load_stager():
    spec = importlib.util.spec_from_file_location("stager_asr_model", STAGER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def donor(tmp_path, name="faster-whisper-base"):
    directory = tmp_path / "donor" / name
    directory.mkdir(parents=True)
    (directory / "model.bin").write_bytes(b"synthetic ctranslate2 weights")
    (directory / "config.json").write_text('{"model": "base"}', encoding="utf-8")
    (directory / "tokenizer.json").write_text("{}", encoding="utf-8")
    (directory / "vocabulary.txt").write_text("a\nb\n", encoding="utf-8")
    return directory


def test_the_model_is_copied_byte_for_byte_with_its_identity(tmp_path):
    stager = load_stager()
    source = donor(tmp_path)
    identity = stager.stage_asr_model(source, tmp_path, "faster-whisper-base")
    target = tmp_path / "runtime" / "models" / "asr" / "faster-whisper-base"
    assert target.is_dir()
    for name in ("model.bin", "config.json", "tokenizer.json", "vocabulary.txt"):
        assert (target / name).read_bytes() == (source / name).read_bytes()
        recorded = identity["files"][name]
        assert recorded["sha256"] == hashlib.sha256((target / name).read_bytes()).hexdigest()
        assert recorded["bytes"] == (target / name).stat().st_size
    assert identity["status"] == "BUNDLED"
    assert identity["bundled_location"] == "runtime/models/asr/faster-whisper-base"
    assert identity["license"]["code_license"] == "MIT"
    on_disk = json.loads((target / "aaos-model.json").read_text(encoding="utf-8"))
    assert on_disk["schema"] == "archeaxis.asr-model/v1"
    assert on_disk["name"] == "faster-whisper-base"
    assert on_disk["license"]["asset_license"]


def test_a_donor_without_weights_is_refused(tmp_path):
    stager = load_stager()
    source = donor(tmp_path)
    (source / "model.bin").unlink()
    with pytest.raises(ValueError, match="no model.bin"):
        stager.stage_asr_model(source, tmp_path, "faster-whisper-base")
    assert not (tmp_path / "runtime" / "models" / "asr" / "faster-whisper-base").exists()


@pytest.mark.parametrize("name", ["../escape", "A Model", "models/asr", "con:", ".hidden"])
def test_an_unsafe_or_invalid_bundle_name_is_refused(tmp_path, name):
    stager = load_stager()
    source = donor(tmp_path)
    with pytest.raises(ValueError):
        stager.stage_asr_model(source, tmp_path, name)


def test_an_existing_bundle_is_never_overwritten(tmp_path):
    stager = load_stager()
    source = donor(tmp_path)
    stager.stage_asr_model(source, tmp_path, "faster-whisper-base")
    with pytest.raises(ValueError, match="refusing ASR model overwrite"):
        stager.stage_asr_model(source, tmp_path, "faster-whisper-base")


def test_an_unrecognised_model_does_not_inherit_another_model_s_licence(tmp_path):
    stager = load_stager()
    source = donor(tmp_path, "some-unknown-asr")
    identity = stager.stage_asr_model(source, tmp_path, "some-unknown-asr")
    assert identity["license"]["code_license"] == "UNCONFIRMED"
    assert identity["license"]["evidence"] == "NOT_READ"


def test_the_bundle_lives_under_the_runtime_resource():
    """The model must travel with `runtime/`, the bundle resource the shell already maps."""
    stager = load_stager()
    assert stager.ASR_MODEL_ROOT == "runtime/models/asr"
    assert stager.ASR_MODEL_IDENTITY == "aaos-model.json"
    assert set(stager.ASR_MODEL_REQUIRED) == {"model.bin", "config.json"}
