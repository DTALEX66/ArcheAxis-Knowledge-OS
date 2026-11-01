"""Isolated CI initialization with tiny installed files; no installer or engine executes."""
import copy
import json
import os
import subprocess
from pathlib import Path

import pytest

from scripts.release import ci_runtime_checkpoint as ci
from scripts.release import runtime_growth as growth
from scripts.release import tauri_portable_candidate as portable
from scripts.runtime import dev


@pytest.fixture
def job(tmp_path, monkeypatch):
    for key in list(os.environ):
        if key.startswith(("ARCHEAXIS_", "GITHUB_", "UV_", "RUNNER_")):
            monkeypatch.delenv(key)
    repo = tmp_path / "checkout"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    project = b'''[project]
name="fixture"
version="1"
readme="README.md"
[build-system]
requires=["setuptools==83.0.0"]
build-backend="setuptools.build_meta"
[tool.setuptools.packages.find]
include=["app*"]
exclude=["app.tests*"]
namespaces=true
[tool.setuptools.package-data]
app=["data/*.json"]
'''
    for name, raw in {".gitignore": b".project-local/\n", "uv.lock": b"version = 1\n",
                      "pyproject.toml": project, "README.md": b"public build metadata",
                      "module.py": b"# unrelated source bound by clean HEAD\n",
                      "app/module.py": b"# known project payload\n", "app/data/payload.json": b'{}',
                      "app/tests/excluded.py": b"# excluded test\n", "docs/retained.md": b"unrelated retained history"}.items():
        (repo / name).parent.mkdir(parents=True, exist_ok=True)
        (repo / name).write_bytes(raw)
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
    subprocess.run(["git", "-C", str(repo), "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
                    "commit", "-qm", "fixture"], check=True)
    paths = dev.layout(repo, "fixture")
    env = dev.prepare(paths)
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    runner = tmp_path / "runner-temp"
    runner.mkdir()
    env_file = runner / "set-env"
    env_file.touch()
    for key, value in {"GITHUB_ACTIONS": "true", "RUNNER_ENVIRONMENT": "github-hosted",
                       "GITHUB_REPOSITORY": "DTALEX66/ArcheAxis-Knowledge-OS", "GITHUB_WORKSPACE": str(repo),
                       "GITHUB_SHA": dev.git(repo, "rev-parse", "HEAD"), "GITHUB_RUN_ID": "123",
                       "GITHUB_RUN_ATTEMPT": "1", "GITHUB_JOB": "runtime", "RUNNER_TEMP": str(runner),
                       "GITHUB_ENV": str(env_file)}.items():
        monkeypatch.setenv(key, value)
    root = paths["build"] / "venv"
    python = root / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    python.parent.mkdir(parents=True)
    python.write_bytes(b"synthetic interpreter; never executed")
    purelib = root / "Lib/site-packages"
    purelib.mkdir(parents=True)
    (purelib / "fixture.py").write_bytes(b"known installed bytes")
    identity = {"version": [3, 12, 9], "base": str(tmp_path), "architecture": "AMD64", "platform": "win32"}
    installed = {**identity, "purelib": str(purelib), "distributions": [["fixture", "1"]]}
    monkeypatch.setattr(ci, "_interpreter", lambda: copy.deepcopy(identity))
    monkeypatch.setattr(ci.shutil, "which", lambda _: "synthetic-uv")
    calls = []
    original = subprocess.run
    def execute(command, **kwargs):
        if command[0] == "git":
            return original(command, **kwargs)
        calls.append(command)
        if command[1:2] == ["export"]:
            Path(command[-1]).write_bytes(b"fixture==1 --hash=sha256:known\n")
        elif command[1:2] == ["sync"]:
            assert command[2:6] == ["--frozen", "--check", "--offline", "--no-python-downloads"]
        else:
            assert command[1:4] == ["-I", "-B", "-c"]
        return subprocess.CompletedProcess(command, 0, json.dumps(installed), "")
    monkeypatch.setattr(subprocess, "run", execute)
    report = {"schema": "aaos.storage-footprint/v2", "repository": str(repo),
              "measured_at": "2026-11-01T00:00:00+00:00", "readable_bytes": 100,
              "measurement_status": "PASS", "measurement_errors": [], "excluded_private": [],
              "excluded_checkouts": [], "out_of_layout": [],
              "dev_root": [{"name": "runs/", "bytes": 10, "budget_gb": 2.0, "over_budget": False}]}
    monkeypatch.setattr(portable, "REPO", repo)
    monkeypatch.setattr(portable.storage_report, "measure", lambda _: copy.deepcopy(report))
    return {"repo": repo, "paths": paths, "root": root, "purelib": purelib, "calls": calls,
            "report": report, "installed": installed}


def initialize(job):
    return ci.initialize(job["repo"], job["paths"])


def test_sealed_forecast_reuses_observed_install_and_fixed_budget(job):
    path = initialize(job)
    baseline, binding, forecast = ci.load(job["repo"], job["paths"], path)
    assert baseline == job["report"]
    assert forecast["generated_bytes"] == (forecast["installed_bytes"] + 3 * forecast["tracked_source_bytes"]
                                           + forecast["requirements"]["bytes"])
    assert forecast["generated_bytes"] > forecast["installed_bytes"] > 0
    assert "not a hard upper bound" in forecast["limitations"]
    assert binding["identity"]["lock"] == ci._bytes(job["repo"] / "uv.lock")
    assert portable.storage_report.DEV_BUDGET_GB["runs"] == 2.0
    context = {"paths": job["paths"], "purpose": "fixture", "sharing": "same job",
               "retention_reason": "boundary evidence", "ci_checkpoint": path}
    assert growth.generated_bytes(context, None) == forecast["generated_bytes"]
    with growth.batch(job["repo"] / ".project-local/rt", {}, forecast["generated_bytes"],
                      context, unknown_output=True):
        growth.verify_requirements(Path(forecast["requirements"]["path"]))
    receipt = json.loads((job["paths"]["artifacts"] / "portable-storage-receipt.json").read_bytes())
    assert receipt["checkpoint"]["identity"] == binding["identity"]
    assert receipt["projected_storage_class"] == "rt/"


@pytest.mark.parametrize("field", ["forecast", "baseline", "requirements", "descriptor", "installed", "source", "lock", "python"])
def test_changes_are_rejected_before_producer_io(job, field):
    path = initialize(job)
    if field in {"forecast", "baseline", "requirements"}:
        suffix = {"forecast": "forecast.json", "baseline": "baseline.json", "requirements": "requirements.txt"}[field]
        target = job["paths"]["artifacts"] / ("ci-runtime-" + suffix)
        target.write_bytes(target.read_bytes() + b" ")
    elif field == "descriptor":
        value = json.loads(path.read_bytes())
        value["forecast"]["bytes"] = 1
        path.write_text(json.dumps(value))
    elif field == "installed":
        (job["purelib"] / "fixture.py").write_bytes(b"different installed bytes")
    elif field in {"source", "lock"}:
        (job["repo"] / ("module.py" if field == "source" else "uv.lock")).write_bytes(b"changed")
    else:
        job["installed"]["version"] = [3, 13, 0]
    with pytest.raises(ValueError):
        ci.load(job["repo"], job["paths"], path)
    assert not (job["repo"] / ".project-local/rt").exists()


def test_self_consistent_lower_forecast_still_must_match_actual_inputs(job):
    path = initialize(job)
    descriptor = json.loads(path.read_bytes())
    forecast_path = Path(descriptor["forecast"]["path"])
    value = json.loads(forecast_path.read_bytes())
    value["generated_bytes"] = 1
    forecast_path.write_text(json.dumps(value))
    descriptor["forecast"].update(ci._bytes(forecast_path))
    path.write_text(json.dumps(descriptor))
    claim = job["paths"]["dev"] / "task-runtime" / ci.SEAL
    sealed = json.loads(claim.read_bytes())
    sealed["descriptor"].update(ci._bytes(path))
    claim.write_text(json.dumps(sealed))
    with pytest.raises(ValueError, match="actual installed/source"):
        ci.load(job["repo"], job["paths"], path)


@pytest.mark.parametrize("mutation", ["only-ci-env", "foreign-job", "foreign-workspace", "dirty", "old-run", "existing-rt", "linked"])
def test_ci_environment_cannot_adopt_old_or_foreign_checkout(job, monkeypatch, mutation):
    if mutation == "only-ci-env":
        monkeypatch.delenv("RUNNER_ENVIRONMENT")
    elif mutation == "foreign-job":
        monkeypatch.delenv("GITHUB_JOB")
    elif mutation == "foreign-workspace":
        monkeypatch.setenv("GITHUB_WORKSPACE", str(job["repo"].parent))
    elif mutation == "dirty":
        (job["repo"] / "module.py").write_bytes(b"dirty")
    elif mutation == "old-run":
        dev.prepare(dev.layout(job["repo"], "older-run"))
    elif mutation == "existing-rt":
        (job["paths"]["dev"] / "rt").mkdir()
    else:
        subprocess.run(["git", "-C", str(job["repo"]), "worktree", "add", "--detach",
                        str(job["paths"]["dev"] / "worktrees/linked")], check=True, capture_output=True)
    with pytest.raises(ValueError):
        initialize(job)
    assert not (job["paths"]["artifacts"] / ci.NAME).exists()


@pytest.mark.parametrize("failure", ["unsynced", "partial", "layout", "budget"])
def test_failed_initialization_is_reserved_and_cannot_roll(job, monkeypatch, failure):
    if failure == "unsynced":
        original = subprocess.run
        def fail(command, **kwargs):
            if command[1:2] == ["sync"]:
                raise subprocess.CalledProcessError(7, command)
            return original(command, **kwargs)
        monkeypatch.setattr(subprocess, "run", fail)
        error = subprocess.CalledProcessError
    else:
        if failure == "partial":
            job["report"]["measurement_status"] = "PARTIAL"
            job["report"]["measurement_errors"] = [{"path": "unreadable"}]
        elif failure == "layout":
            job["report"]["out_of_layout"] = ["new unknown output"]
        else:
            job["report"]["dev_root"][0]["over_budget"] = True
        error = ValueError
    with pytest.raises(error):
        initialize(job)
    claim = job["paths"]["dev"] / "task-runtime" / ci.CLAIM
    assert claim.exists()
    with pytest.raises(FileExistsError):
        initialize(job)
    fresh = dev.layout(job["repo"], "second")
    dev.prepare(fresh)
    monkeypatch.setenv("ARCHEAXIS_RUN_ROOT", str(fresh["run"]))
    with pytest.raises(ValueError, match="fresh run"):
        ci.initialize(job["repo"], fresh)


def test_checkpoint_is_not_a_portable_or_local_baseline_override(job, monkeypatch):
    path = initialize(job)
    context = {"paths": job["paths"], "purpose": "fixture", "sharing": "same job",
               "retention_reason": "evidence", "ci_checkpoint": path}
    with pytest.raises(ValueError, match="exact formal runtime"):
        portable._storage_pre(job["paths"]["artifacts"] / "portable", 10, context)
    with pytest.raises(ValueError, match="sealed forecast"):
        growth.generated_bytes(context, 1)
    monkeypatch.setenv("GITHUB_RUN_ATTEMPT", "2")
    with pytest.raises(ValueError, match="another job"):
        ci.load(job["repo"], job["paths"], path)


def test_actual_requirements_must_match_before_install(job):
    path = initialize(job)
    context = {"paths": job["paths"], "purpose": "fixture", "sharing": "same job",
               "retention_reason": "evidence", "ci_checkpoint": path}
    projected = growth.generated_bytes(context, None)
    wrong = job["paths"]["tmp"] / "wrong-requirements.txt"
    wrong.write_bytes(b"wrong==1")
    with pytest.raises(ValueError, match="requirements differ"), growth.batch(
            job["repo"] / ".project-local/rt", {}, projected, context, unknown_output=True):
        growth.verify_requirements(wrong)
    receipt = json.loads((job["paths"]["artifacts"] / "portable-storage-receipt.json").read_bytes())
    assert receipt["original_error"]["type"] == "ValueError"
    assert "post_review" in receipt


def test_cold_core_growth_precedes_one_fixed_runtime_baseline(job):
    ci.reserve(job["repo"], job["paths"])
    before = copy.deepcopy(job["report"])
    nested = dev.layout(job["repo"], "core-build")
    dev.prepare(nested)
    # No large files: the synthetic counterexample models a cold compiler's
    # >2GiB prior output, still below the unchanged 22GiB build class ceiling.
    job["report"]["readable_bytes"] += 3 * 1024 ** 3
    job["report"]["dev_root"].append({"name": "build/", "bytes": 3 * 1024 ** 3,
                                     "budget_gb": 22.0, "over_budget": False})
    assert portable.storage_report.growth_review(job["report"], before)["status"] == "REVIEW_REQUIRED"
    path = ci.seal(job["repo"], job["paths"])
    baseline, _, forecast = ci.load(job["repo"], job["paths"], path)
    assert baseline["readable_bytes"] == job["report"]["readable_bytes"]
    context = {"paths": job["paths"], "purpose": "fixture", "sharing": "same job",
               "retention_reason": "evidence", "ci_checkpoint": path}
    with growth.batch(job["repo"] / ".project-local/rt", {}, forecast["generated_bytes"],
                      context, unknown_output=True):
        pass
    with pytest.raises(FileExistsError):
        ci.seal(job["repo"], job["paths"])


def test_seal_rejects_preexisting_run_even_with_matching_source(job):
    old = dev.layout(job["repo"], "old-build")
    dev.prepare(old)
    # Reserve cannot accept this history in the first place.
    with pytest.raises(ValueError, match="fresh run"):
        ci.reserve(job["repo"], job["paths"])


@pytest.mark.parametrize("route", ["batch", "guard"])
def test_ci_total_cannot_omit_sealed_generated_forecast(job, route):
    path = initialize(job)
    context = {"paths": job["paths"], "purpose": "fixture", "sharing": "same job",
               "retention_reason": "evidence", "ci_checkpoint": path}
    with pytest.raises(ValueError, match="sealed.*forecast"):
        if route == "batch":
            with growth.batch(job["repo"] / ".project-local/rt", {}, 1, context, unknown_output=True):
                pytest.fail("understated CI producer started")
        else:
            portable._storage_pre(job["repo"] / ".project-local/rt", 1, context, formal_runtime=True)


def test_retained_giant_docs_are_not_three_wheel_payloads(job, monkeypatch):
    original = ci._bytes
    def measured(path, **kwargs):
        value = original(path, **kwargs)
        if path == job["repo"] / "docs/retained.md":
            return {**value, "bytes": 3 * 1024 ** 3}  # metadata only; no large file is created
        return value
    monkeypatch.setattr(ci, "_bytes", measured)
    path = initialize(job)
    _, _, forecast = ci.load(job["repo"], job["paths"], path)
    assert forecast["generated_bytes"] < 2 * 1024 ** 3
    files = forecast["tracked_source_files"]
    assert "app/module.py" in files and "app/data/payload.json" in files and "README.md" in files
    assert "docs/retained.md" not in files and "app/tests/excluded.py" not in files


@pytest.mark.parametrize("change", ["backend", "package-dir", "manifest", "namespaces"])
def test_unknown_wheel_input_mechanism_requires_adapter_review(job, monkeypatch, change):
    original = ci.tomllib.loads
    def declaration(raw):
        value = original(raw)
        if change == "backend":
            value["build-system"]["build-backend"] = "unknown_backend"
        elif change == "package-dir":
            value["tool"]["setuptools"]["package-dir"] = {"": "src"}
        elif change == "namespaces":
            value["tool"]["setuptools"]["packages"]["find"]["namespaces"] = False
        return value
    monkeypatch.setattr(ci.tomllib, "loads", declaration)
    if change == "manifest":
        original_git = dev.git
        monkeypatch.setattr(dev, "git", lambda repo, *args: original_git(repo, *args) + "MANIFEST.in\0")
    with pytest.raises(ValueError, match="forecast"):
        ci.wheel_inputs(job["repo"])
