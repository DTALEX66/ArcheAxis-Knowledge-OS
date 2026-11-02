"""Output-size checks for the shared transport's actual staging writer."""

import hashlib
import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "services/python-workers/transport/text_ndjson.py"


def load_transport():
    spec = importlib.util.spec_from_file_location("output_preflight_transport", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_oversized_later_artifact_is_rejected_before_any_new_outputs(tmp_path, monkeypatch):
    transport = load_transport()
    staging = tmp_path / "staging"
    (staging / "input").mkdir(parents=True)
    output = staging / "output"
    output.mkdir()
    existing = output / "existing-unrelated"
    existing.write_bytes(b"preserve")
    raw = b"synthetic input"
    digest = hashlib.sha256(raw).hexdigest()
    (staging / "input" / digest).write_bytes(raw)
    request = {
        "schema": "archeaxis.worker-request/v1", "type": "job_request",
        "request_id": "output-preflight", "job_id": "output-preflight-job", "attempt": 1,
        "protocol_minor": 0, "capability": "text.extract", "capability_version": "1",
        "deadline_ms": 30000,
        "inputs": [{"uri": f"job://input/{digest}", "sha256": digest, "media_type": "text/plain"}],
        "parameters": {},
    }
    # The first two synthetic outputs are small; JSON framing makes the final
    # artifact exceed the actual 16 MiB output read limit by a few bytes.
    monkeypatch.setattr(transport, "_run_route", lambda *_args, **_kwargs: {
        "text": "synthetic", "structure": [],
        "loss_receipt": {"loss_note": "x" * transport.MAX_INPUT_BYTES},
    })
    with pytest.raises(transport.Rejected) as rejected:
        transport.execute(request, staging)
    assert rejected.value.code == "AAK-VAL-003"
    assert str(rejected.value) == "output artifact exceeds byte limit"
    assert existing.read_bytes() == b"preserve"
    assert {path.name for path in output.iterdir()} == {existing.name}


@pytest.mark.parametrize("size,accepted", [(128, True), (129, False)])
def test_output_size_boundary_preserves_equal_and_rejects_one_more_byte(tmp_path, monkeypatch, size, accepted):
    transport = load_transport()
    monkeypatch.setattr(transport, "MAX_INPUT_BYTES", 128)
    staging = tmp_path / "staging"
    (staging / "input").mkdir(parents=True)
    output = staging / "output"
    output.mkdir()
    raw = b"input"
    digest = hashlib.sha256(raw).hexdigest()
    (staging / "input" / digest).write_bytes(raw)
    request = {
        "schema": "archeaxis.worker-request/v1", "type": "job_request",
        "request_id": "boundary", "job_id": "boundary-job", "attempt": 1,
        "protocol_minor": 0, "capability": "text.extract", "capability_version": "1",
        "deadline_ms": 30000,
        "inputs": [{"uri": f"job://input/{digest}", "sha256": digest, "media_type": "text/plain"}],
        "parameters": {},
    }
    monkeypatch.setattr(transport, "_run_route", lambda *_args, **_kwargs: {
        "text": "x" * size, "structure": [], "loss_receipt": {"loss_note": ""},
    })
    if accepted:
        outputs, _, _ = transport.execute(request, staging)
        item = next(item for item in outputs if item["kind"] == "text")
        assert item["byte_length"] == size
        assert (output / item["sha256"]).read_bytes() == b"x" * size
    else:
        with pytest.raises(transport.Rejected) as rejected:
            transport.execute(request, staging)
        assert rejected.value.code == "AAK-VAL-003"
        assert str(rejected.value) == "output artifact exceeds byte limit"
        assert list(output.iterdir()) == []
