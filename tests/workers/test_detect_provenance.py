"""Actual detector input identity is distinct from a caller's requested paths."""
from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import types
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
from pathlib import Path
from threading import Event

import pytest


ROOT = Path(__file__).resolve().parents[2]
WORKER = ROOT / "services/python-workers/document/worker_detect.py"
MODEL = ROOT / "shared/models/magika"
SAMPLE = ROOT / "tests/fixtures/sample.xlsx"


def load_worker():
    spec = importlib.util.spec_from_file_location("provenance_worker", WORKER)
    assert spec and spec.loader
    worker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(worker)
    return worker


def model_root(root: Path, label: str | None = None) -> Path:
    target = root / "shared/models/magika"
    target.mkdir(parents=True)
    shutil.copyfile(MODEL / "model.onnx", target / "model.onnx")
    config = json.loads((MODEL / "config.min.json").read_text(encoding="utf-8"))
    if label:
        config["target_labels_space"] = [label] * len(config["target_labels_space"])
        config["thresholds"] = {}
        config["overwrite_map"] = {}
    (target / "config.min.json").write_text(json.dumps(config), encoding="utf-8")
    return target


def hashes(directory: Path) -> dict[str, str]:
    return {f"{key}_sha256": sha256((directory / name).read_bytes()).hexdigest()
            for key, name in (("model", "model.onnx"), ("config", "config.min.json"))}


def test_caller_selects_model_data_but_not_code(tmp_path, monkeypatch):
    worker = load_worker()
    chosen = model_root(tmp_path / "caller", "pdf")
    environment = model_root(tmp_path / "environment", "png")
    monkeypatch.setenv("ARCHEAXIS_MAGIKA_MODEL_DIR", str(environment))
    malicious = types.ModuleType("shared.file_detection")
    malicious.detect = lambda *_args, **_kwargs: pytest.fail("untrusted detector imported")
    monkeypatch.setitem(sys.modules, "shared.file_detection", malicious)

    result = worker.detect(str(SAMPLE), str(tmp_path / "caller"))
    assert result["structure"]["label"] == "pdf"
    assert result["structure"]["model"]["config_sha256"] == hashes(chosen)["config_sha256"]
    assert result["loss_receipt"]["params"]["model_identity"] == hashes(chosen)
    assert result["structure"]["model"]["revision_status"] == "declared_profile_not_publisher_verified"


def test_default_selection_tracks_environment_and_recovers_when_it_changes(tmp_path, monkeypatch):
    worker = load_worker()
    first = model_root(tmp_path / "first", "pdf")
    second = model_root(tmp_path / "second", "png")
    monkeypatch.setenv("ARCHEAXIS_MAGIKA_MODEL_DIR", str(first))
    a = worker.detect(str(SAMPLE))
    monkeypatch.setenv("ARCHEAXIS_MAGIKA_MODEL_DIR", str(second))
    b = worker.detect(str(SAMPLE))
    assert a["structure"]["label"] == "pdf"
    assert b["structure"]["label"] == "png"
    assert a["loss_receipt"]["params"]["model_identity"] == hashes(first)
    assert b["loss_receipt"]["params"]["model_identity"] == hashes(second)


def test_alternate_model_bytes_do_not_inherit_vendored_licence(tmp_path):
    worker = load_worker()
    directory = model_root(tmp_path / "alternate")
    model = directory / "model.onnx"
    # A valid protobuf unknown field changes the actual ONNX bytes without
    # changing its graph, so this tests a real alternate runtime input.
    model.write_bytes(model.read_bytes() + b"\xf8\x07\x01")
    result = worker.detect(str(SAMPLE), str(tmp_path / "alternate"))
    assert result["structure"]["label"] == "xlsx"
    assert result["structure"]["model"]["model_sha256"] == hashes(directory)["model_sha256"]
    assert result["structure"]["model"]["licence"] == "unverified"


def test_real_worker_transport_uses_portable_installation_root(tmp_path):
    candidate = tmp_path / "candidate"
    script = candidate / "workers/document/worker_detect.py"
    script.parent.mkdir(parents=True)
    shutil.copyfile(WORKER, script)
    transport = candidate / "workers/transport/text_ndjson.py"
    transport.parent.mkdir(parents=True)
    shutil.copyfile(ROOT / "services/python-workers/transport/text_ndjson.py", transport)
    shared = candidate / "shared/file_detection.py"
    shared.parent.mkdir(parents=True)
    shutil.copyfile(ROOT / "shared/file_detection.py", shared)
    model = model_root(candidate)
    stage = tmp_path / "staging"
    (stage / "input").mkdir(parents=True)
    (stage / "output").mkdir()
    raw = SAMPLE.read_bytes()
    digest = sha256(raw).hexdigest()
    (stage / "input" / digest).write_bytes(raw)
    request = {"schema": "archeaxis.worker-request/v1", "type": "job_request",
               "request_id": "request-1", "job_id": "job-1", "attempt": 1,
               "protocol_minor": 0, "capability": "document.detect", "capability_version": "1",
               "deadline_ms": 30000,
               "inputs": [{"uri": f"job://input/{digest}", "sha256": digest,
                           "media_type": "application/octet-stream"}], "parameters": {}}
    env = {name: os.environ[name] for name in ("SystemRoot", "WINDIR") if name in os.environ}
    env.update({"TEMP": str(tmp_path), "TMP": str(tmp_path)})
    process = subprocess.run(
        [sys.executable, "-I", "-B", "-X", "utf8", str(script), "--staging-root", str(stage)],
        input=json.dumps(request) + "\n", capture_output=True, text=True, encoding="utf-8",
        env=env, timeout=30, check=False, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    assert process.returncode == 0, process.stderr
    hello, response = map(json.loads, process.stdout.splitlines())
    assert hello["capabilities"] == ["document.detect"]
    assert response["status"] == "succeeded"
    outputs = {entry["kind"]: entry for entry in response["outputs"]}
    for entry in outputs.values():
        content = (stage / "output" / entry["sha256"]).read_bytes()
        assert sha256(content).hexdigest() == entry["sha256"]
    loss = json.loads((stage / "output" / outputs["loss_report"]["sha256"]).read_bytes())
    assert loss["params"]["worker_structure"]["label"] == "xlsx"
    assert loss["params"]["model_identity"] == hashes(model)


def test_receipt_and_cached_session_bind_loaded_bytes(tmp_path, monkeypatch):
    worker = load_worker()
    directory = model_root(tmp_path / "selected")
    original = hashes(directory)
    detector = worker._load_detector()
    constructor = detector.rt.InferenceSession
    observed = []

    def replace_after_read(model_bytes, **kwargs):
        assert isinstance(model_bytes, bytes)
        observed.append(sha256(model_bytes).hexdigest())
        (directory / "model.onnx").write_bytes(b"not an ONNX model")
        (directory / "config.min.json").write_text("{}", encoding="utf-8")
        return constructor(model_bytes, **kwargs)

    monkeypatch.setattr(detector.rt, "InferenceSession", replace_after_read)
    first = worker.detect(str(SAMPLE), str(tmp_path / "selected"))
    second = worker.detect(str(SAMPLE), str(tmp_path / "selected"))
    assert first["structure"]["label"] == second["structure"]["label"] == "xlsx"
    assert first["loss_receipt"]["params"]["model_identity"] == original
    assert second["loss_receipt"]["params"]["model_identity"] == original
    assert original != hashes(directory)
    assert observed == [original["model_sha256"]]

    invalid = model_root(tmp_path / "invalid")
    (invalid / "model.onnx").write_bytes(b"not an ONNX model")
    with pytest.raises(Exception):
        worker.detect(str(SAMPLE), str(tmp_path / "invalid"))


def test_concurrent_requests_do_not_mix_models_or_receipts(tmp_path, monkeypatch):
    worker = load_worker()
    first_dir = model_root(tmp_path / "first", "pdf")
    second_dir = model_root(tmp_path / "second", "png")
    detector = worker._load_detector()
    constructor = detector.rt.InferenceSession
    entered, release, second_load = Event(), Event(), Event()
    count = 0

    class BlockingSession:
        def __init__(self, model_bytes, **kwargs):
            nonlocal count
            count += 1
            self.first = count == 1
            if not self.first:
                second_load.set()
            self.actual = constructor(model_bytes, **kwargs)

        def get_inputs(self):
            return self.actual.get_inputs()

        def run(self, *args):
            if self.first:
                entered.set()
                assert release.wait(15)
            return self.actual.run(*args)

    monkeypatch.setattr(detector.rt, "InferenceSession", BlockingSession)
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(worker.detect, str(SAMPLE), str(tmp_path / "first"))
        assert entered.wait(15)
        second = pool.submit(worker.detect, str(SAMPLE), str(tmp_path / "second"))
        try:
            assert not second_load.wait(0.2)
        finally:
            release.set()
        a, b = first.result(timeout=30), second.result(timeout=30)
    assert a["structure"]["label"] == "pdf"
    assert b["structure"]["label"] == "png"
    assert a["loss_receipt"]["params"]["model_identity"] == hashes(first_dir)
    assert b["loss_receipt"]["params"]["model_identity"] == hashes(second_dir)
