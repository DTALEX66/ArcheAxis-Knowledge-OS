"""Detector staging is source-bound and counted; no installer or product acceptance."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest

from tests.test_backend_in_place import prepared, run_stager, stager  # shared canonical growth fixture


@pytest.fixture
def detector_inputs(tmp_path, monkeypatch):
    donor = tmp_path / "detector-source"
    contents = {
        "shared/file_detection.py": b"# synthetic detector, never executed\n",
        "shared/models/magika/model.onnx": b"synthetic model",
        "shared/models/magika/config.min.json": b"{}\n",
        "shared/models/magika/LICENSE": b"synthetic license\n",
    }
    expected = {}
    for name, value in contents.items():
        path = donor / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(value)
        expected[name] = {"bytes": len(value), "sha256": hashlib.sha256(value).hexdigest()}
    monkeypatch.setattr(stager, "DETECTOR_SOURCE", donor)
    monkeypatch.setattr(stager, "DETECTOR_FILES", expected)
    return donor, expected


def declare_detector(case):
    worker = case["repo"] / "services/python-workers/document/worker_detect.py"
    worker.parent.mkdir(parents=True, exist_ok=True)
    worker.write_bytes(b"# synthetic detector worker\n")


def test_deep_runtime_allows_only_recorded_package_internal_files(tmp_path):
    runtime = tmp_path.joinpath(*(["long-runtime-component-1234567890"] * 5)) / "runtime"
    package = runtime / "Lib/site-packages/fastapi/.agents"
    record = runtime / "Lib/site-packages/fastapi-1.0.dist-info/RECORD"
    stager.filesystem_path(package).mkdir(parents=True)
    stager.filesystem_path(record.parent).mkdir(parents=True)
    stager.filesystem_path(package / "upstream.md").write_bytes(b"synthetic package data")
    stager.filesystem_path(record).write_text("fastapi/.agents/upstream.md,,\n", encoding="utf-8")
    if os.name == "nt":
        assert len(str(package)) > 260
    stager.validate_runtime_tree(runtime)
    stager.filesystem_path(package / "unrecorded.md").write_bytes(b"unrecorded")
    with pytest.raises(ValueError, match="protected staging path"):
        stager.validate_runtime_tree(runtime)


def test_detector_route_stages_exact_four_inputs_and_manifest(prepared, detector_inputs):
    donor, expected = detector_inputs
    declare_detector(prepared)
    assert run_stager(prepared) == 0
    output = prepared["output"]
    manifest = json.loads((output / "backend-runtime-manifest.json").read_text(encoding="utf-8"))
    profile = json.loads((output / "worker-profile.json").read_text(encoding="utf-8"))
    assert any(row["capability"] == "document.detect" for row in profile["routes"])
    for name, identity in expected.items():
        assert manifest["files"][name] == identity
        assert (output / name).read_bytes() == (donor / name).read_bytes()
    # Existing growth batch observes both pre and post accounting for this in-place run.
    assert len(prepared["storage_calls"]) == 2


def test_growth_plan_counts_and_binds_every_detector_donor(prepared, detector_inputs, monkeypatch):
    donor, expected = detector_inputs
    declare_detector(prepared)
    args = SimpleNamespace(runtime=prepared["output"] / "runtime",
        workers=prepared["repo"] / "services/python-workers", core=prepared["core"],
        shared=prepared["repo"] / "shared/learning_scheduler.py", vc_runtime=prepared["vc"],
        asr_model=None, webview2_runtime=None, dep=[])
    inputs, total = stager.runtime_copy_plan(args, True)
    assert args._detector_plan == expected
    for name, identity in expected.items():
        assert inputs[stager.growth.plain(donor / name)] == identity
    monkeypatch.setitem(stager.ROUTE_SCRIPTS, "document.detect", ())
    without, smaller = stager.runtime_copy_plan(args, True)
    assert args._detector_plan is None
    assert all(stager.growth.plain(donor / name) not in without for name in expected)
    assert total - smaller == sum(row["bytes"] for row in expected.values())


def test_detector_absent_does_not_need_or_copy_detector_inputs(prepared, detector_inputs):
    donor, expected = detector_inputs
    (donor / "shared/file_detection.py").unlink()
    assert run_stager(prepared) == 0
    manifest = json.loads((prepared["output"] / "backend-runtime-manifest.json").read_text(encoding="utf-8"))
    assert not set(expected).intersection(manifest["files"])


@pytest.mark.parametrize("name", ["shared/file_detection.py", "shared/models/magika/model.onnx",
                                  "shared/models/magika/config.min.json", "shared/models/magika/LICENSE"])
@pytest.mark.parametrize("change", ["missing", "changed"])
def test_missing_or_changed_donor_refused_before_output(prepared, detector_inputs, name, change):
    donor, _ = detector_inputs
    declare_detector(prepared)
    path = donor / name
    if change == "missing":
        path.unlink()
    else:
        path.write_bytes(b"changed")
    with pytest.raises(ValueError, match="detector donor"):
        run_stager(prepared)
    assert not prepared["output"].exists()


@pytest.mark.parametrize("mutation", ["source_after_plan", "copy_after_write", "manifest_after_write"])
def test_drift_at_later_staging_boundaries_is_refused(prepared, detector_inputs, monkeypatch, mutation):
    donor, _ = detector_inputs
    declare_detector(prepared)
    original_copy = stager.growth.copy2
    original_write = Path.write_text
    changed = False

    def copy_with_drift(source, target, **kwargs):
        nonlocal changed
        result = original_copy(source, target, **kwargs)
        target = Path(target)
        if mutation == "source_after_plan" and target.name == "archeaxis-api.exe" and not changed:
            (donor / "shared/file_detection.py").write_bytes(b"changed after plan")
            changed = True
        if mutation == "copy_after_write" and target.name == "config.min.json" and "magika" in target.parts:
            target.write_bytes(b"changed after copy")
            changed = True
        return result

    def write_with_drift(path, data, *args, **kwargs):
        nonlocal changed
        if mutation == "manifest_after_write" and path.name == "backend-runtime-manifest.json":
            value = json.loads(data)
            value["files"]["shared/models/magika/config.min.json"]["sha256"] = "0" * 64
            data = json.dumps(value)
            changed = True
        return original_write(path, data, *args, **kwargs)

    monkeypatch.setattr(stager.growth, "copy2", copy_with_drift)
    monkeypatch.setattr(Path, "write_text", write_with_drift)
    with pytest.raises(ValueError, match="detector"):
        run_stager(prepared)
    assert changed


def test_actual_portable_worker_reads_staged_pinned_files_and_refuses_missing_model(tmp_path):
    pytest.importorskip("numpy")
    pytest.importorskip("onnxruntime")
    root = Path(__file__).resolve().parents[2]
    candidate = tmp_path / "candidate"
    candidate.mkdir()
    worker = root / "services/python-workers/document/worker_detect.py"
    transport = root / "services/python-workers/transport/text_ndjson.py"
    inputs = {stager.growth.plain(stager.DETECTOR_SOURCE / name): identity
              for name, identity in stager.DETECTOR_FILES.items()}
    for source in (worker, transport):
        inputs[stager.growth.plain(source)] = stager.growth.row(source)
    with stager.growth.batch(candidate, inputs, sum(row["bytes"] for row in inputs.values())):
        stager.stage_detector(candidate, stager.detector_source_rows())
        for source, relative in ((worker, "workers/document/worker_detect.py"),
                                 (transport, "workers/transport/text_ndjson.py")):
            target = candidate / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            stager.growth.copy2(source, target)
    sample = root / "tests/fixtures/sample.xlsx"
    env = {name: os.environ[name] for name in ("SystemRoot", "WINDIR") if name in os.environ}
    env.update({"TEMP": str(tmp_path), "TMP": str(tmp_path)})
    command = [sys.executable, "-I", "-B", str(candidate / "workers/document/worker_detect.py"), str(sample)]
    process = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", env=env,
                             timeout=30, check=False, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    assert process.returncode == 0, process.stderr
    result = json.loads(process.stdout)
    assert result["structure"]["state"] == "detected"
    assert result["structure"]["model"]["model_sha256"] == stager.DETECTOR_FILES["shared/models/magika/model.onnx"]["sha256"]
    assert result["structure"]["model"]["config_sha256"] == stager.DETECTOR_FILES["shared/models/magika/config.min.json"]["sha256"]
    (candidate / "shared/models/magika/model.onnx").unlink()
    missing = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", env=env,
                             timeout=30, check=False, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    assert missing.returncode == 0, missing.stderr
    assert json.loads(missing.stdout)["structure"]["state"] == "unavailable"
