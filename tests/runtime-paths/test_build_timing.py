"""Failures retain stage durations and cannot turn into successful build receipts."""
import json
import subprocess

import pytest

from desktop.scripts import prepare_bundle
from scripts.runtime.build_timing import BuildTimings


def test_exception_and_nonzero_exit_are_saved_without_sensitive_error_text(tmp_path):
    timings = BuildTimings(tmp_path, {"ARCHEAXIS_SOURCE_COMMIT": "source-fixture"})
    with timings.stage("success"):
        pass
    with timings.stage("returned-failure") as stage:
        stage["exit_code"] = 23
    with pytest.raises(RuntimeError), timings.stage("raised-failure"):
        raise RuntimeError("sensitive-output-fixture")
    report = json.loads(timings.path.read_text())
    assert [item["status"] for item in report["stages"]] == ["PASS", "FAIL", "FAIL"]
    assert all(item["seconds"] >= 0 for item in report["stages"])
    assert "sensitive-output-fixture" not in timings.path.read_text()
    assert report["source"]["ARCHEAXIS_SOURCE_COMMIT"] == "source-fixture"


def test_runtime_dependency_failure_keeps_copy_export_and_install_timings(tmp_path, monkeypatch):
    from contextlib import nullcontext
    monkeypatch.setattr(prepare_bundle.sys, "version_info", (3, 12, 9))
    monkeypatch.setattr(prepare_bundle.sys, "base_prefix", str(tmp_path))
    destination = tmp_path / "runtime-candidate"
    run = tmp_path / "run"
    (run / "tmp").mkdir(parents=True)
    env = {"ARCHEAXIS_RUN_ROOT": str(run), "UV_PROJECT_ENVIRONMENT": str(run / "tmp/build-venv")}
    monkeypatch.setattr(prepare_bundle, "runtime_build_environment", lambda _: env)
    monkeypatch.setattr(prepare_bundle.shutil, "which", lambda _: "synthetic-uv")
    monkeypatch.setattr(prepare_bundle.growth, "snapshot", lambda *args, **kwargs: {})
    monkeypatch.setattr(prepare_bundle.growth, "batch", lambda *args, **kwargs: nullcontext())

    def copy(**_):
        python = destination / "runtime/python/python.exe"
        python.parent.mkdir(parents=True)
        python.write_bytes(b"synthetic executable")
        return python

    def execute(command, **_):
        if command[1:3] == ["pip", "install"]:
            raise subprocess.CalledProcessError(23, command)

    monkeypatch.setattr(prepare_bundle, "stage_runtime", copy)
    monkeypatch.setattr(prepare_bundle.subprocess, "run", execute)
    with pytest.raises(subprocess.CalledProcessError):
        prepare_bundle.prepare_bundle_runtime(repository=tmp_path, destination=destination, storage_generated_bytes=1)
    report = json.loads(next((run / "artifacts").glob("bt-*.json")).read_text())
    assert [(item["name"], item["status"]) for item in report["stages"]] == [("python-copy", "PASS"), ("dependency-export", "PASS"), ("dependency-install", "FAIL")]
    assert report["stages"][0]["bytes"] == len(b"synthetic executable")
