"""Actual authoritative layout with synthetic bytes; no uv, installer, VM or Core execution."""
import hashlib
import json
import os
import subprocess
from pathlib import Path

import pytest

from desktop.scripts import prepare_bundle as producer
from scripts.release import stage_backend_runtime as stager

ORIGINAL_PREPARER = producer.prepare_bundle_runtime


@pytest.fixture
def prepared(tmp_path, monkeypatch):
    for key in list(os.environ):
        if key.startswith("ARCHEAXIS_") or key in {"CARGO_TARGET_DIR", "UV_CACHE_DIR", "UV_PROJECT_ENVIRONMENT"}:
            monkeypatch.delenv(key)
    repo = tmp_path / "repository"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    (repo / ".gitignore").write_text(".project-local/\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", ".gitignore"], check=True)
    subprocess.run(["git", "-C", str(repo), "-c", "user.name=Fixture",
                    "-c", "user.email=fixture@example.invalid", "commit", "-qm", "fixture"], check=True)
    workers = repo / "services/python-workers"
    (workers / "transport").mkdir(parents=True)
    (workers / "transport/text_ndjson.py").write_bytes(b"# synthetic worker\n")
    (repo / "shared").mkdir()
    (repo / "shared/learning_scheduler.py").write_bytes(b"# synthetic scheduler\n")
    (repo / "frontend").mkdir()
    (repo / "frontend/package.json").write_text('{"version":"fixture"}', encoding="utf-8")
    env = producer.runtime_build_environment(repo)
    for key, value in env.items():
        if key.startswith("ARCHEAXIS_"):
            monkeypatch.setenv(key, value)
    base = tmp_path / "synthetic-python"
    (base / "Lib").mkdir(parents=True)
    (base / "python.exe").write_bytes(b"synthetic executable; never run")
    (base / "Lib/os.py").write_bytes(b"# synthetic stdlib\n")
    vc = tmp_path / "synthetic-vc"
    vc.mkdir()
    original, current = {}, {}
    for name in ("vcruntime140.dll", "vcruntime140_1.dll", "msvcp140.dll"):
        new = b"new-" + name.encode()
        old = new if name == "msvcp140.dll" else b"old-" + name.encode()
        (base / name).write_bytes(old)
        (vc / name).write_bytes(new)
        original[name] = {"version": "original", "bytes": len(old), "sha256": hashlib.sha256(old).hexdigest()}
        current[name] = {"version": "current", "bytes": len(new), "sha256": hashlib.sha256(new).hexdigest()}
    monkeypatch.setattr(stager, "APP_LOCAL_VC_RUNTIME",
                        {name: (original[name], current[name]) for name in stager.APP_LOCAL_VC_RUNTIME})
    monkeypatch.setattr(stager, "APP_LOCAL_CPP_COHORTS", (original, current))
    monkeypatch.setattr(stager, "packager_identity", lambda: "synthetic-packager")
    monkeypatch.setattr(producer, "resolve_vc_runtime", lambda *_: vc)
    monkeypatch.setattr(producer, "_backend_stager", lambda _: stager)
    monkeypatch.setattr("desktop.scripts.stage_runtime.sys.base_prefix", str(base))
    core = tmp_path / "synthetic-core.exe"
    core.write_bytes(b"synthetic Core; never run")
    output = Path(env["ARCHEAXIS_RUN_ROOT"]) / "artifacts/backend"
    observed = []
    copies = []
    original_copytree = producer.shutil.copytree
    def measured_copytree(source, target, *args, **kwargs):
        copies.append((stager.ordinary_path(Path(os.fspath(source))), stager.ordinary_path(Path(os.fspath(target)))))
        return original_copytree(source, target, *args, **kwargs)
    monkeypatch.setattr(producer.shutil, "copytree", measured_copytree)
    def prepare(*, repository, destination, _backend_in_place=False, _environment=None):
        assert _backend_in_place is True
        for key in ("ARCHEAXIS_RUN_ROOT", "ARCHEAXIS_WORKTREE_ROOT", "ARCHEAXIS_SOURCE_COMMIT", "ARCHEAXIS_SOURCE_PATCH_SHA256"):
            assert _environment[key] == env[key]
        observed.append(destination)
        python = producer.stage_runtime(repository=repository, destination=destination, _backend_in_place=True)
        packages = python.parent / "Lib/site-packages"
        (packages / "fastapi/.agents").mkdir(parents=True)
        (packages / "fastapi/.agents/upstream.md").write_bytes(b"public fixture")
        (packages / "fastapi-1.0.dist-info").mkdir()
        (packages / "fastapi-1.0.dist-info/RECORD").write_text("fastapi/.agents/upstream.md,,\n", encoding="utf-8")
        return python
    monkeypatch.setattr(producer, "prepare_bundle_runtime", prepare)
    real_run = subprocess.run
    def no_executable(command, **kwargs):
        if command and str(command[0]) == "git":
            return real_run(command, **kwargs)
        if (command and str(command[0]).endswith("python.exe")
                and command[1:4] == ["-I", "-B", "-c"]
                and command[4] == "import sys;print(sys.version.split()[0])"):
            return subprocess.CompletedProcess(command, 0, "3.12.9\n", "")
        pytest.fail("No actual build/install/runtime command permitted: " + str(command[:3]))
    monkeypatch.setattr(subprocess, "run", no_executable)
    monkeypatch.delenv("CARGO_TARGET_DIR", raising=False)
    argv = ["--core", str(core), "--runtime", str(output / "runtime"),
            "--workers", str(workers), "--shared", str(repo / "shared/learning_scheduler.py"),
            "--out", str(output), "--version", "fixture", "--source-commit", env["ARCHEAXIS_SOURCE_COMMIT"],
            "--source-tree", env["ARCHEAXIS_SOURCE_TREE"], "--vc-runtime", str(vc)]
    return dict(repo=repo, env=env, core=core, output=output, base=base, vc=vc,
                observed=observed, argv=argv, prepare=prepare, copies=copies)


def run_stager(case, callback=None, environment=None, extra=()):
    return stager.main(case["argv"] + list(extra), _runtime_environment=environment or case["env"],
                       _runtime_preparer=callback or (lambda root: case["prepare"](
                           repository=case["repo"], destination=root, _backend_in_place=True,
                           _environment=case["env"])))


def test_producer_prepares_one_final_runtime_and_real_stager_keeps_formal_contract(prepared):
    c = prepared
    python = producer.prepare_backend_candidate(repository=c["repo"], destination=c["output"], core=c["core"])
    assert python == c["output"] / "runtime/python.exe"
    assert c["observed"] == [c["output"]]
    assert c["copies"].count((c["base"], c["output"] / "runtime")) == 1
    assert not any(source == c["output"] / "runtime" for source, target in c["copies"])
    assert python.read_bytes() == (c["base"] / "python.exe").read_bytes()
    assert not c["output"].with_name("backend-python-input").exists()
    assert not (c["output"] / "runtime/python").exists()
    assert (c["output"] / "runtime/Lib/site-packages/fastapi/.agents/upstream.md").read_bytes() == b"public fixture"
    manifest = json.loads((c["output"] / "backend-runtime-manifest.json").read_text(encoding="utf-8"))
    assert manifest["runtime_preparation"]["intermediate_runtime_tree_copies"] == 0
    assert manifest["runtime_preparation"]["run_root"] == c["env"]["ARCHEAXIS_RUN_ROOT"]
    assert manifest["files"]["runtime/python.exe"]["sha256"] == hashlib.sha256(python.read_bytes()).hexdigest()
    assert manifest["files"]["core/archeaxis-api.exe"]["sha256"] == hashlib.sha256(c["core"].read_bytes()).hexdigest()
    profile = json.loads((c["output"] / "worker-profile.json").read_text(encoding="utf-8"))
    assert profile["python"] == "runtime/python.exe"
    assert profile["script"] == "workers/transport/text_ndjson.py"
    for name in ("core/archeaxis-api.exe", "workers/transport/text_ndjson.py", "shared/learning_scheduler.py",
                 "shared/safe_http.py", "shared/llm_adapter.py", "start-backend.py", "start-backend.cmd",
                 "vcruntime140.dll", "vcruntime140_1.dll"):
        assert (c["output"] / name).is_file(), name
    for name in ("vcruntime140.dll", "vcruntime140_1.dll", "msvcp140.dll"):
        assert (c["output"] / "runtime" / name).read_bytes() == (c["vc"] / name).read_bytes()


def test_default_cli_mode_still_copies_and_does_not_consume_donor(prepared):
    c = prepared
    donor = c["repo"] / ".project-local/default-donor"
    donor.mkdir()
    for path in c["base"].rglob("*"):
        if path.is_file():
            target = donor / path.relative_to(c["base"])
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(path.read_bytes())
    argv = list(c["argv"])
    argv[argv.index("--runtime")+1] = str(donor)
    before = stager.prepared_runtime_snapshot(donor)
    assert stager.main(argv) == 0
    assert stager.prepared_runtime_snapshot(donor) == before
    assert os.stat(donor / "python.exe").st_ino != os.stat(c["output"] / "runtime/python.exe").st_ino
    assert c["observed"] == []
    assert c["copies"].count((donor, c["output"] / "runtime")) == 1
    assert "runtime_preparation" not in json.loads((c["output"] / "backend-runtime-manifest.json").read_text(encoding="utf-8"))
    with pytest.raises(ValueError, match="overwrite"):
        stager.main(argv)


def test_existing_destination_is_not_adopted_or_modified(prepared):
    c = prepared
    c["output"].mkdir()
    sentinel = c["output"] / "keep.txt"
    sentinel.write_bytes(b"keep")
    with pytest.raises(ValueError, match="overwrite"):
        run_stager(c, callback=lambda _: pytest.fail("Existing output must not reach callback"))
    assert sentinel.read_bytes() == b"keep"


@pytest.mark.parametrize("change", ["run", "owner", "source", "layout", "outside"])
def test_foreign_or_changed_ownership_rejected_before_preparation(prepared, change):
    c = prepared
    env = dict(c["env"])
    if change == "run":
        env["ARCHEAXIS_RUN_ROOT"] = str(Path(env["ARCHEAXIS_RUN_ROOT"]).with_name("foreign"))
    elif change in {"owner", "source"}:
        path = Path(env["ARCHEAXIS_RUN_ROOT"]) / "run-metadata.json"
        meta = json.loads(path.read_text(encoding="utf-8"))
        meta["owner" if change == "owner" else "source_patch_sha256"] = "foreign"
        path.write_text(json.dumps(meta), encoding="utf-8")
    elif change == "layout":
        c["argv"][c["argv"].index("--runtime")+1] = str(c["output"] / "wrong")
    else:
        c["argv"][c["argv"].index("--out")+1] = str(c["repo"] / ".project-local/other")
    with pytest.raises(ValueError):
        run_stager(c, callback=lambda _: pytest.fail("Ownership/layout failure before callback"), environment=env)
    assert not c["output"].exists()


@pytest.mark.parametrize("extra", ["extra-root", "wrong-return", "hardlink", "junction"])
def test_callback_extras_aliases_and_links_are_rejected_and_preserved(prepared, extra):
    c = prepared
    def callback(root):
        python = c["prepare"](repository=c["repo"], destination=root, _backend_in_place=True, _environment=c["env"])
        if extra == "extra-root":
            (root / "extra.txt").write_bytes(b"preserve")
        elif extra == "wrong-return":
            return python.parent / "alias.exe"
        elif extra == "hardlink":
            os.link(python, python.parent / "alias.exe")
        else:
            link = python.parent / "linked"
            if os.name == "nt":
                # The only child process in this counterexample creates an owned fixture junction.
                # It neither reads nor executes its target.
                original = getattr(subprocess.run, "_fixture_original", None)
                if original is None:
                    original = subprocess.Popen
                    child = original(["cmd", "/c", "mklink", "/J", str(link), str(c["base"])], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    out, err = child.communicate()
                    assert child.returncode == 0, (out, err)
                else:
                    original(["cmd", "/c", "mklink", "/J", str(link), str(c["base"])], check=True, capture_output=True)
            else:
                link.symlink_to(c["base"], target_is_directory=True)
        return python
    with pytest.raises(ValueError):
        run_stager(c, callback=callback)
    assert (c["output"] / "runtime/python.exe").exists()
    assert not (c["output"] / "backend-runtime-manifest.json").exists()


@pytest.mark.parametrize("change", ["member", "new-runtime-member", "new-root-member", "run-metadata"])
def test_mid_stage_drift_fails_without_manifest_or_cleanup(prepared, monkeypatch, change):
    c = prepared
    original = stager.stage_app_local_vc_runtime
    def alter(runtime, root, vc_runtime=None, **kwargs):
        result = original(runtime, root, vc_runtime, **kwargs)
        if change == "member":
            (runtime / "Lib/os.py").write_bytes(b"changed after pin")
        elif change == "new-runtime-member":
            (runtime / "unexpected.py").write_bytes(b"changed after pin")
        elif change == "new-root-member":
            (root / "unexpected.txt").write_bytes(b"changed after pin")
        else:
            p = Path(c["env"]["ARCHEAXIS_RUN_ROOT"]) / "run-metadata.json"
            p.write_bytes(p.read_bytes() + b"\n")
        return result
    monkeypatch.setattr(stager, "stage_app_local_vc_runtime", alter)
    with pytest.raises(ValueError, match="changed|unexpected"):
        run_stager(c)
    assert (c["output"] / "runtime/python.exe").exists()
    assert not (c["output"] / "backend-runtime-manifest.json").exists()


def test_preparation_exception_retains_partial_bytes_and_real_failure_timing(prepared, monkeypatch):
    c = prepared
    def fail(**kwargs):
        c["prepare"](**kwargs)
        raise RuntimeError("synthetic dependency failure")
    monkeypatch.setattr(producer, "prepare_bundle_runtime", fail)
    with pytest.raises(RuntimeError, match="synthetic dependency"):
        producer.prepare_backend_candidate(repository=c["repo"], destination=c["output"], core=c["core"])
    assert (c["output"] / "runtime/python.exe").exists()
    reports = [json.loads(p.read_text(encoding="utf-8")) for p in
               (Path(c["env"]["ARCHEAXIS_RUN_ROOT"]) / "artifacts").glob("bt-*.json")]
    assert any(any(s["name"] == "backend-runtime-in-place" and s["status"] == "FAIL"
                   for s in r["stages"]) for r in reports)


@pytest.mark.parametrize("drift", ["none", "donor", "copy"])
def test_synthetic_asr_exact_path_additions_are_pinned_not_prefix_exempt(prepared, monkeypatch, drift):
    c = prepared
    model = c["repo"] / ".project-local/model-fixture"
    model.mkdir()
    (model / "model.bin").write_bytes(b"synthetic bytes; never infer")
    (model / "config.json").write_bytes(b"{}")
    original = stager.stage_asr_model
    def stage(*args, **kwargs):
        result = original(*args, **kwargs)
        if drift == "donor":
            (model / "config.json").write_bytes(b"changed")
        elif drift == "copy":
            (c["output"] / "runtime/models/asr/fixture/config.json").write_bytes(b"changed")
        return result
    monkeypatch.setattr(stager, "stage_asr_model", stage)
    if drift == "none":
        assert run_stager(c, extra=["--asr-model", str(model), "--asr-model-name", "fixture"]) == 0
        manifest = json.loads((c["output"] / "backend-runtime-manifest.json").read_text(encoding="utf-8"))
        assert manifest["asr_model"]["status"] == "BUNDLED"
    else:
        with pytest.raises(ValueError, match="changed"):
            run_stager(c, extra=["--asr-model", str(model), "--asr-model-name", "fixture"])
        assert not (c["output"] / "backend-runtime-manifest.json").exists()


def test_actual_runtime_preparer_uses_copy_link_mode_and_separate_metadata(prepared, monkeypatch):
    c = prepared
    original_preparer = ORIGINAL_PREPARER
    destination = Path(c["env"]["ARCHEAXIS_RUN_ROOT"]) / "artifacts/actual-preparer"
    destination.mkdir()
    calls = []
    monkeypatch.setattr(producer.sys, "version_info", (3, 12, 9))
    monkeypatch.setattr(producer.shutil, "which", lambda _: "synthetic-uv")
    def execute(command, *, env, stage, **kwargs):
        calls.append((command, dict(env), stage))
        assert env["UV_LINK_MODE"] == "copy"
        if stage == "dependency-export":
            Path(command[-1]).write_bytes(b"# synthetic requirements")
        elif stage == "wheel-build":
            wheels = Path(command[command.index("--out-dir")+1])
            wheels.mkdir()
            (wheels / "archeaxis_workspace-fixture.whl").write_bytes(b"synthetic wheel; never installed")
    monkeypatch.setattr(producer, "_run", execute)
    before = os.environ.get("UV_LINK_MODE")
    python = original_preparer(repository=c["repo"], destination=destination, _backend_in_place=True, _environment=c["env"])
    assert python == destination / "runtime/python.exe"
    assert not (destination / "runtime/python").exists()
    assert not (destination / "requirements.locked.txt").exists()
    assert not (destination / "wheels").exists()
    evidence = Path(c["env"]["ARCHEAXIS_RUN_ROOT"]) / "artifacts/python-preparation"
    assert (evidence / "requirements.locked.txt").is_file()
    assert (evidence / "wheels/archeaxis_workspace-fixture.whl").is_file()
    assert calls[-1][0][1:4] == ["-I", "-B", "-c"]
    assert os.environ.get("UV_LINK_MODE") == before


def owned_junction(link, target):
    if os.name == "nt":
        child = subprocess.Popen(["cmd", "/c", "mklink", "/J", str(link), str(target)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        output, error = child.communicate()
        assert child.returncode == 0, (output, error)
    else:
        link.symlink_to(target, target_is_directory=True)


def test_internal_preparer_rejects_junction_before_any_copy_or_dependency_lookup(prepared, monkeypatch):
    c = prepared
    target = c["repo"] / ".project-local/empty-target"
    target.mkdir()
    link = Path(c["env"]["ARCHEAXIS_RUN_ROOT"]) / "artifacts/redirect"
    owned_junction(link, target)
    monkeypatch.setattr(producer.sys, "version_info", (3, 12, 9))
    monkeypatch.setattr(producer.shutil, "which", lambda _: pytest.fail("Reject link before dependency lookup"))
    with pytest.raises(ValueError, match="linked"):
        ORIGINAL_PREPARER(repository=c["repo"], destination=link,
                          _backend_in_place=True, _environment=c["env"])
    assert list(target.iterdir()) == []


@pytest.mark.parametrize("field", ["output", "core", "asr"])
def test_producer_rejects_linked_explicit_paths_before_preparation(prepared, monkeypatch, field):
    c = prepared
    target = c["repo"] / ".project-local/path-target"
    target.mkdir()
    (target / "core.exe").write_bytes(b"preserve linked fixture")
    model = target / "model"
    model.mkdir()
    (model / "model.bin").write_bytes(b"synthetic; never infer")
    link = Path(c["env"]["ARCHEAXIS_RUN_ROOT"]) / "artifacts/input-alias"
    owned_junction(link, target)
    destination = link / "output" if field == "output" else c["output"]
    core = link / "core.exe" if field == "core" else c["core"]
    asr = link / "model" if field == "asr" else None
    monkeypatch.setattr(producer, "runtime_build_environment", lambda _: pytest.fail("Reject link before allocating"))
    with pytest.raises(ValueError, match="linked"):
        producer.prepare_backend_candidate(repository=c["repo"], destination=destination, core=core, asr_model=asr)
    assert (target / "core.exe").read_bytes() == b"preserve linked fixture"
    assert not (target / "output").exists()
    assert not c["output"].exists()
