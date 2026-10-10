"""The detection worker names bytes from the vendored model, or says which artefact is missing.

F04's requirement is that an unnameable extension is not guessed at. A model judgement is not a
guess only while it is traceable: which model ran, over which bytes, with what score, and with the
product's own rule that a score is not an accuracy claim.
"""

from __future__ import annotations

import importlib.util
from hashlib import sha256
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKER = ROOT / "services" / "python-workers" / "document" / "worker_detect.py"
spec = importlib.util.spec_from_file_location("worker_detect", WORKER)
assert spec and spec.loader
worker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(worker)


def _nameless_copy(tmp_path: Path) -> Path:
    """A real XLSX fixture handed over under a name that declares nothing."""
    payload = (ROOT / "tests" / "fixtures" / "sample.xlsx").read_bytes()
    target = tmp_path / "field_notes"
    target.write_bytes(payload)
    return target


def test_names_the_bytes_from_the_vendored_model(tmp_path: Path) -> None:
    result = worker.detect(str(_nameless_copy(tmp_path)), str(ROOT))
    structure = result["structure"]
    assert structure["state"] == "detected"
    assert structure["label"] == "xlsx" and structure["group"] == "office"
    assert result["text"] == f"xlsx\toffice\t{structure['model_score']:.4f}\n"
    blob = (tmp_path / "field_notes").read_bytes()
    assert structure["input_sha256"] == sha256(blob).hexdigest()
    model_bytes = (ROOT / "shared" / "models" / "magika" / "model.onnx").read_bytes()
    assert structure["model"]["model_sha256"] == sha256(model_bytes).hexdigest()
    assert "\\?\\" not in str(structure["model"])


def test_a_missing_vendored_model_is_refused_by_exact_artefact_names(tmp_path: Path) -> None:
    result = worker.detect(str(_nameless_copy(tmp_path)), str(tmp_path))
    assert result["text"] == ""
    assert result["structure"]["state"] == "unavailable"
    assert sorted(result["loss_receipt"]["params"]["missing_artifacts"]) == [
        "shared/models/magika/config.min.json",
        "shared/models/magika/model.onnx",
    ]
    assert result["loss_receipt"]["params"]["claim"] == "no content judgement was produced, so none is asserted"


def test_an_absent_input_is_refused_rather_than_reported_as_unknown(tmp_path: Path) -> None:
    result = worker.detect(str(tmp_path / "never_written"), str(ROOT))
    assert result["structure"]["state"] == "unavailable"
    assert "not a file" in result["loss_receipt"]["params"]["reason"]


def test_the_receipt_refuses_to_pass_a_model_score_as_accuracy(tmp_path: Path) -> None:
    result = worker.detect(str(_nameless_copy(tmp_path)), str(ROOT))
    assert "not an accuracy measure" in result["loss_receipt"]["params"]["claim"]
    # The worker states its own limit: no media type is invented here, because the vendored config
    # carries no mime table and inventing one would be the guess the requirement refuses.
    assert "media_type" not in result["structure"]
    assert result["structure"]["basis"].startswith("a model judgement")


def test_a_job_refusal_is_raised_so_it_cannot_settle_as_an_empty_success(tmp_path) -> None:
    import pytest

    with pytest.raises(RuntimeError) as raised:
        worker.extract(str(tmp_path / "never_written"))
    assert "not a file" in str(raised.value)
