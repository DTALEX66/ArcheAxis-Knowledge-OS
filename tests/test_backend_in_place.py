"""Actual authoritative layout with synthetic bytes; no uv, installer, VM or Core execution."""
import hashlib
import json
import os
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from desktop.scripts import prepare_bundle as producer
from scripts.release import stage_backend_runtime as stager
from tests.test_runtime_growth import mock_file_alias, storage_fixture

ORIGINAL_PREPARER = producer.prepare_bundle_runtime


@pytest.fixture
def prepared(tmp_path, monkeypatch):
    # The production bundle preparer imports the canonical growth module before
    # it loads the stager. A different pytest collection order may have loaded
    # the standalone stager first, creating a separate module instance. Bind
    # the fixture to the same real growth implementation used by the preparer so
    # its synthetic repository and the nested copy plan share one guard state.
    monkeypatch.setattr(stager, "growth", producer.growth)
    for key in list(os.environ):
        if key.startswith("ARCHEAXIS_") or key in {"CARGO_TARGET_DIR", "UV_CACHE_DIR", "UV_PROJECT_ENVIRONMENT"}:
            monkeypatch.delenv(key)
    repo = tmp_path / "repository"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    (repo / ".gitignore").write_text(".project-local/\ndocs/\n", encoding="utf-8")
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
    context, storage_report, storage_calls = storage_fixture(repo, Path(env["ARCHEAXIS_RUN_ROOT"]), monkeypatch)
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
        # The generated run path can exceed MAX_PATH on Windows. Use the same
        # extended-path helper as the stager for these synthetic fixture files.
        packages = stager.filesystem_path(python.parent / "Lib/site-packages")
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
    argv += ["--run-id", context["paths"]["run"].name, "--storage-purpose", context["purpose"],
             "--storage-sharing", context["sharing"], "--storage-retention-reason", context["retention_reason"],
             "--storage-generated-bytes", "256"]  # Explicit bound for this tiny synthetic callback only.
    return dict(repo=repo, env=env, core=core, output=output, base=base, vc=vc,
                observed=observed, argv=argv, prepare=prepare, copies=copies, context=context,
                storage_report=storage_report, storage_calls=storage_calls)


def run_stager(case, callback=None, environment=None, extra=()):
    return stager.main(case["argv"] + list(extra), _runtime_environment=environment or case["env"],
                       _runtime_preparer=callback or (lambda root: case["prepare"](
                           repository=case["repo"], destination=root, _backend_in_place=True,
                           _environment=case["env"])))


def test_synthetic_repository_still_rejects_foreign_dev_root(prepared, monkeypatch):
    case = prepared
    monkeypatch.setenv("ARCHEAXIS_DEV_ROOT", str(case["repo"].parent / "foreign/.project-local"))
    with pytest.raises(ValueError, match="ARCHEAXIS_DEV_ROOT must equal"):
        run_stager(case)
    assert not case["output"].exists()


def test_in_place_core_pair_is_bounded_materialized_and_observed_not_build_qualified(prepared, monkeypatch):
    from scripts.runtime import runtime_resources
    c = prepared
    source = c["repo"] / ".project-local/build/cargo/release/archeaxis-api.exe"
    pair = source.parent / "deps/archeaxis_api.exe"
    pair.parent.mkdir(parents=True)
    source.write_bytes(b"tiny current build output; never executed")
    os.link(source, pair)
    if os.name != "nt":
        monkeypatch.setattr(runtime_resources, "_core_link_paths", lambda path: {
            "paths": [source, pair], "raw_names": [str(source), str(pair)], "method": "SYNTHETIC_NAMES_REAL_POSIX_INODES"})
    c["argv"][c["argv"].index("--core") + 1] = str(source)
    assert run_stager(c) == 0
    staged = c["output"] / "core/archeaxis-api.exe"
    assert staged.read_bytes() == source.read_bytes()
    assert staged.stat().st_nlink == 1 and source.stat().st_nlink == pair.stat().st_nlink == 2
    manifest = json.loads((c["output"] / "backend-runtime-manifest.json").read_bytes())
    assert manifest["core_input"]["cargo_core"]["qualification"] == "OBSERVED_CARGO_OUTPUT_NOT_QUALIFIED_BUILD"


@pytest.mark.parametrize("mode", ["tiny_estimate", "pre", "projected", "post", "original_and_post"])
def test_in_place_shared_growth_review_and_original_errors(prepared, monkeypatch, mode):
    c = prepared
    report, calls = c["storage_report"], c["storage_calls"]
    if mode == "tiny_estimate":
        c["argv"][c["argv"].index("--storage-generated-bytes") + 1] = "1"
        assert run_stager(c) == 0
        assert len(calls) == 2  # A small declared estimate never bypasses unknown-output review.
    else:
        if mode == "pre":
            report["dev_root"][0]["bytes"] += 2 * 1024 ** 3 + 1
        elif mode == "projected":
            args = SimpleNamespace(runtime=c["output"] / "runtime", workers=c["repo"] / "services/python-workers",
                core=c["core"], shared=c["repo"] / "shared/learning_scheduler.py", vc_runtime=c["vc"],
                asr_model=None, webview2_runtime=None, dep=[])
            _, total = stager.runtime_copy_plan(args, True)
            report["dev_root"][0]["bytes"] += 2 * 1024 ** 3 - total - 256 + 1
        else:
            measure = stager.growth.portable.storage_report.measure
            def changed(root):
                if calls:
                    if mode == "original_and_post":
                        raise OSError("synthetic post storage failure")
                    report["dev_root"][0]["bytes"] += 2 * 1024 ** 3 + 1
                return measure(root)
            monkeypatch.setattr(stager.growth.portable.storage_report, "measure", changed)
        original = RuntimeError("original runtime preparation failure")
        def callback(root):
            (root / "partial").write_bytes(b"preserve original bytes")
            raise original
        if mode == "original_and_post":
            with pytest.raises(RuntimeError) as caught:
                run_stager(c, callback=callback)
            assert caught.value is original
            assert (c["output"] / "partial").read_bytes() == b"preserve original bytes"
        else:
            with pytest.raises(stager.growth.portable.GrowthReviewRequiredError):
                run_stager(c)
        if mode in {"pre", "projected"}:
            assert not c["output"].exists() and len(calls) == 2
    receipt = json.loads((c["output"].parent / "portable-storage-receipt.json").read_bytes())
    assert receipt["measurement_status"] == "PARTIAL"
    if mode == "original_and_post":
        assert receipt["original_error"]["message"] == str(original)
        assert receipt["post_error"]["message"] == "synthetic post storage failure"


def test_unknown_callback_requires_positive_estimate_before_root_creation(prepared):
    c = prepared
    c["argv"][c["argv"].index("--storage-generated-bytes") + 1] = "0"
    with pytest.raises(ValueError, match="positive"):
        run_stager(c)
    assert not c["output"].exists() and not c["storage_calls"]


@pytest.mark.parametrize("target", ["rt", "rt-other"])
def test_only_exact_formal_runtime_root_uses_existing_rt_storage_class(prepared, target):
    c = prepared
    output = c["repo"] / ".project-local" / target
    c["argv"][c["argv"].index("--out") + 1] = str(output)
    c["argv"][c["argv"].index("--runtime") + 1] = str(output / "runtime")
    if target != "rt":
        with pytest.raises(ValueError, match="canonical allocated run artifacts"):
            run_stager(c)
        assert not output.exists()
        return
    assert run_stager(c) == 0
    receipt = json.loads((c["context"]["paths"]["artifacts"] / "portable-storage-receipt.json").read_bytes())
    assert receipt["projected_storage_class"] == "rt/"
    assert receipt["projected_class_bytes_before"] == 0
    assert receipt["projected_class_bytes_after"] == receipt["planned_payload_bytes"]
    assert receipt["projected_review"]["status"] == "NO_NEW_GROWTH_TRIGGER"
    assert receipt["measurement_status"] == "PARTIAL"


@pytest.mark.parametrize("ci_context", [False, True])
def test_producer_prepares_one_final_runtime_and_real_stager_keeps_formal_contract(prepared, monkeypatch, ci_context):
    c = prepared
    if ci_context:
        from scripts.release import ci_runtime_checkpoint
        c["output"] = c["repo"] / ".project-local/rt"
        c["context"]["ci_checkpoint"] = c["context"]["paths"]["artifacts"] / ci_runtime_checkpoint.NAME
        def sealed(repo, paths, path):
            assert repo == c["repo"] and paths == c["context"]["paths"]
            assert path == c["context"]["ci_checkpoint"]
            return c["storage_report"], {"contract_fixture": "CI loader independently verified"}, {"generated_bytes": 256}
        monkeypatch.setattr(ci_runtime_checkpoint, "load", sealed)
    python = producer.prepare_backend_candidate(repository=c["repo"], destination=c["output"], core=c["core"],
        storage_context=c["context"], storage_generated_bytes=256)
    assert python == c["output"] / "runtime/python.exe"
    assert c["observed"] == [c["output"]]
    assert c["copies"].count((c["base"], c["output"] / "runtime")) == 1
    assert not any(source == c["output"] / "runtime" for source, target in c["copies"])
    assert stager.filesystem_path(python).read_bytes() == stager.filesystem_path(c["base"] / "python.exe").read_bytes()
    assert not stager.filesystem_path(c["output"].with_name("backend-python-input")).exists()
    assert not stager.filesystem_path(c["output"] / "runtime/python").exists()
    assert stager.filesystem_path(c["output"] / "runtime/Lib/site-packages/fastapi/.agents/upstream.md").read_bytes() == b"public fixture"
    manifest = json.loads(stager.filesystem_path(c["output"] / "backend-runtime-manifest.json").read_text(encoding="utf-8"))
    assert manifest["runtime_preparation"]["intermediate_runtime_tree_copies"] == 0
    assert manifest["runtime_preparation"]["run_root"] == c["env"]["ARCHEAXIS_RUN_ROOT"]
    assert manifest["files"]["runtime/python.exe"]["sha256"] == hashlib.sha256(stager.filesystem_path(python).read_bytes()).hexdigest()
    assert manifest["files"]["core/archeaxis-api.exe"]["sha256"] == hashlib.sha256(c["core"].read_bytes()).hexdigest()
    profile = json.loads(stager.filesystem_path(c["output"] / "worker-profile.json").read_text(encoding="utf-8"))
    assert profile["python"] == "runtime/python.exe"
    assert profile["script"] == "workers/transport/text_ndjson.py"
    for name in ("core/archeaxis-api.exe", "workers/transport/text_ndjson.py", "shared/learning_scheduler.py",
                 "shared/safe_http.py", "shared/llm_adapter.py", "start-backend.py", "start-backend.cmd",
                 "vcruntime140.dll", "vcruntime140_1.dll"):
        assert stager.filesystem_path(c["output"] / name).is_file(), name
    for name in ("vcruntime140.dll", "vcruntime140_1.dll", "msvcp140.dll"):
        assert stager.filesystem_path(c["output"] / "runtime" / name).read_bytes() == stager.filesystem_path(c["vc"] / name).read_bytes()


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
        producer.prepare_backend_candidate(repository=c["repo"], destination=c["output"], core=c["core"],
            storage_context=c["context"], storage_generated_bytes=256)
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
            stager.filesystem_path(c["output"] / "runtime/models/asr/fixture/config.json").write_bytes(b"changed")
        return result
    monkeypatch.setattr(stager, "stage_asr_model", stage)
    if drift == "none":
        assert run_stager(c, extra=["--asr-model", str(model), "--asr-model-name", "fixture"]) == 0
        manifest = json.loads(stager.filesystem_path(c["output"] / "backend-runtime-manifest.json").read_text(encoding="utf-8"))
        assert manifest["asr_model"]["status"] == "BUNDLED"
    else:
        with pytest.raises(ValueError, match="changed"):
            run_stager(c, extra=["--asr-model", str(model), "--asr-model-name", "fixture"])
        assert not stager.filesystem_path(c["output"] / "backend-runtime-manifest.json").exists()


def test_asr_identity_and_copy_work_at_deep_paths_without_overwrite(tmp_path):
    base = tmp_path.joinpath(*(["long-asr-component-1234567890"] * 5))
    donor, output = base / "donor", base / "output"
    stager.filesystem_path(donor).mkdir(parents=True)
    stager.filesystem_path(output).mkdir(parents=True)
    for name, data in (("model.bin", b"synthetic model"), ("config.json", b"{}")):
        stager.filesystem_path(donor / name).write_bytes(data)
    if os.name == "nt":
        assert len(str(output / "runtime/models/asr/fixture/aaos-model.json")) > 260
    inputs = {stager.growth.plain(donor / name): stager.growth.row(donor / name)
              for name in ("model.bin", "config.json")}
    with stager.growth.batch(output, inputs, sum(row["bytes"] for row in inputs.values())):
        receipt = stager.stage_asr_model(donor, output, "fixture")
    identity = json.loads(stager.filesystem_path(output / "runtime/models/asr/fixture/aaos-model.json")
                          .read_text(encoding="utf-8"))
    assert receipt["files"] == identity["files"]
    assert identity["files"]["model.bin"] == inputs[stager.growth.plain(donor / "model.bin")]
    with pytest.raises(ValueError, match="overwrite"):
        stager.stage_asr_model(donor, output, "fixture")


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
            stager.filesystem_path(Path(command[-1])).write_bytes(b"# synthetic requirements")
        elif stage == "wheel-build":
            wheels = stager.filesystem_path(Path(command[command.index("--out-dir")+1]))
            wheels.mkdir()
            (wheels / "archeaxis_workspace-fixture.whl").write_bytes(b"synthetic wheel; never installed")
    monkeypatch.setattr(producer, "_run", execute)
    before = os.environ.get("UV_LINK_MODE")
    python = original_preparer(repository=c["repo"], destination=destination, _backend_in_place=True,
        _environment=c["env"], storage_context=c["context"], storage_generated_bytes=256)
    assert python == destination / "runtime/python.exe"
    assert not stager.filesystem_path(destination / "runtime/python").exists()
    assert not stager.filesystem_path(destination / "requirements.locked.txt").exists()
    assert not stager.filesystem_path(destination / "wheels").exists()
    evidence = Path(c["env"]["ARCHEAXIS_RUN_ROOT"]) / "artifacts/python-preparation"
    assert stager.filesystem_path(evidence / "requirements.locked.txt").is_file()
    assert stager.filesystem_path(evidence / "wheels/archeaxis_workspace-fixture.whl").is_file()
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


def test_cli_rejects_explicit_repository_alias_before_donor_lookup(prepared, monkeypatch):
    c = prepared
    alias = c["repo"] / ".project-local/repository-alias"
    owned_junction(alias, c["repo"])
    monkeypatch.setattr(producer.sys, "argv", ["prepare_bundle", "--backend-candidate",
        "--repository", str(alias), "--destination", str(c["output"]), "--core", str(c["core"])])
    monkeypatch.setattr(producer, "declared_asr_model", lambda _: pytest.fail("Reject repository link before donor lookup"))
    with pytest.raises(ValueError, match="linked"):
        producer.main()


def test_cli_forwards_same_storage_context_to_following_core_copy(prepared, monkeypatch):
    c = prepared
    run_id = Path(c["env"]["ARCHEAXIS_RUN_ROOT"]).name
    monkeypatch.setattr(producer.sys, "argv", ["prepare_bundle", "--repository", str(c["repo"]),
        "--destination", str(c["output"]), "--core", str(c["core"]), "--run-id", run_id,
        "--storage-purpose", "fixture", "--storage-sharing", "shared", "--storage-retention-reason", "evidence",
        "--storage-generated-bytes", "256"])
    observed = []
    monkeypatch.setattr(producer, "prepare_bundle_runtime", lambda **kwargs: observed.append(kwargs))
    monkeypatch.setattr(producer, "install_core", lambda **kwargs: observed.append(kwargs))
    assert producer.main() == 0
    assert observed[0]["storage_context"] is observed[1]["storage_context"]
    assert observed[1]["storage_context"]["purpose"] == "fixture"


def test_implicit_interpreter_alias_is_bound_once_and_recorded(prepared, monkeypatch):
    c = prepared
    alias = c["repo"] / ".project-local/implicit-python"
    owned_junction(alias, c["base"])
    mock_file_alias(monkeypatch, c["base"] / "python3.exe", "python.exe")
    monkeypatch.setattr(stager.growth.sys, "base_prefix", str(alias))
    original = Path.resolve
    resolved = []
    def resolve(path, *args, **kwargs):
        if path == alias:
            resolved.append(path)
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, "resolve", resolve)
    binding = stager.growth.interpreter_source()
    assert binding["logical_root"] == str(alias)
    assert binding["physical_root"] == str(c["base"].resolve())
    assert binding["source_python"]["sha256"] == stager.sha256(c["base"] / "python.exe")
    inputs = producer.runtime_inputs(c["base"], interpreter_binding=binding)
    with stager.growth.batch(c["output"], inputs, sum(r["bytes"] for r in inputs.values()),
                             interpreter_binding=binding):
        python = producer.stage_runtime(repository=c["repo"], destination=c["output"])
    assert python.read_bytes() == (c["base"] / "python.exe").read_bytes()
    assert len(resolved) == 1
    assert json.loads((c["output"] / "python-source-binding.json").read_bytes()) == binding
    with pytest.raises(ValueError, match="linked"):
        stager.growth.snapshot(alias)  # The same path supplied explicitly remains forbidden.


def test_in_place_python3_alias_uses_same_outer_plan_binding_and_real_copy(prepared, monkeypatch):
    c = prepared
    alias = c["base"] / "python3.exe"
    mock_file_alias(monkeypatch, alias, "python.exe")
    args = SimpleNamespace(runtime=c["output"] / "runtime", workers=c["repo"] / "services/python-workers",
        core=c["core"], shared=c["repo"] / "shared/learning_scheduler.py", vc_runtime=c["vc"],
        asr_model=None, webview2_runtime=None, dep=[])
    inputs, total = stager.runtime_copy_plan(args, True)
    assert inputs[alias]["bytes"] == (c["base"] / "python.exe").stat().st_size
    assert total >= 2 * inputs[alias]["bytes"]
    assert run_stager(c) == 0
    copied = c["output"] / "runtime/python3.exe"
    assert copied.read_bytes() == (c["base"] / "python.exe").read_bytes()
    assert not copied.is_symlink() and copied.stat().st_nlink == 1
    manifest = json.loads((c["output"] / "backend-runtime-manifest.json").read_bytes())
    assert manifest["runtime_preparation"]["interpreter_binding"]["executable_aliases"][str(alias)]["target"] == str(c["base"] / "python.exe")


def test_implicit_alias_does_not_approve_a_redirected_child(prepared, monkeypatch):
    c = prepared
    alias = c["repo"] / ".project-local/implicit-python"
    owned_junction(alias, c["base"])
    child_target = c["repo"] / ".project-local/child-target"
    child_target.mkdir()
    (child_target / "preserve").write_bytes(b"preserve")
    owned_junction(c["base"] / "Lib/redirect", child_target)
    monkeypatch.setattr(stager.growth.sys, "base_prefix", str(alias))
    with pytest.raises(ValueError, match="linked"):
        producer.stage_runtime(repository=c["repo"], destination=c["output"])
    assert not c["output"].exists()
    assert (child_target / "preserve").read_bytes() == b"preserve"


@pytest.mark.parametrize("in_place", [False, True])
@pytest.mark.parametrize("field", ["repository", "destination", "destination-parent", "dangling-destination"])
def test_internal_preparer_rejects_junction_before_any_copy_or_dependency_lookup(prepared, monkeypatch, in_place, field):
    c = prepared
    target = c["repo"] / ".project-local/empty-target"
    target.mkdir()
    link = Path(c["env"]["ARCHEAXIS_RUN_ROOT"]) / "artifacts/redirect"
    if field == "dangling-destination":
        target.rmdir()
    owned_junction(link, target)
    repository = link if field == "repository" else c["repo"]
    destination = link / "child" if field == "destination-parent" else link
    if field == "repository":
        destination = c["output"]
    monkeypatch.setattr(producer.sys, "version_info", (3, 12, 9))
    monkeypatch.setattr(producer.shutil, "which", lambda _: pytest.fail("Reject link before dependency lookup"))
    with pytest.raises(ValueError, match="linked"):
        ORIGINAL_PREPARER(repository=repository, destination=destination,
                          _backend_in_place=in_place, _environment=c["env"])
    assert not target.exists() if field == "dangling-destination" else list(target.iterdir()) == []


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


@pytest.mark.skipif(os.name != "nt", reason="the unprefixed MAX_PATH failure is a Windows-specific observation")
def test_stage_capability_manifest_handles_windows_long_path(tmp_path):
    """A real existing parent and working extended-path control isolate this write."""
    root = tmp_path
    while len(str(root / "workers/capability-requirements.yaml")) <= 260:
        root = root / ("synthetic-component-" + "x" * 12)
    workers = root / "workers"
    target = workers / "capability-requirements.yaml"
    assert len(str(target)) > 260

    try:
        stager.filesystem_path(workers).mkdir(parents=True)
        control = workers / ("c" * len(target.name))
        stager.filesystem_path(control).write_bytes(b"synthetic extended-path control")
    except OSError as error:
        pytest.skip(f"cannot establish extended-path fixture: {type(error).__name__}")
    assert stager.filesystem_path(workers).is_dir()
    assert len(str(control)) == len(str(target))
    assert stager.filesystem_path(control).read_bytes() == b"synthetic extended-path control"

    # Test the host's actual unprefixed behavior at the same length, without
    # touching the manifest target. A long-path-aware host cannot reproduce the
    # observed failure; preserve that limitation instead of claiming RED.
    plain_control = workers / ("p" * len(target.name))
    try:
        plain_control.write_bytes(b"synthetic plain-path control")
    except OSError as error:
        if (getattr(error, "winerror", None) not in (3, 206)
                and not (isinstance(error, FileNotFoundError) and error.errno == 2)):
            pytest.skip(f"unprefixed control failed for a different reason: {type(error).__name__}")
    else:
        pytest.skip("this host permits the same-length unprefixed path")

    source = Path(stager.__file__).resolve().parents[2] / "config/environment/capability-requirements.yaml"
    expected = source.read_text(encoding="utf-8").encode("utf-8")
    receipt = stager.stage_capability_manifest(root, None)
    assert stager.filesystem_path(target).read_bytes() == expected
    assert receipt["artifact_path"] == "workers/capability-requirements.yaml"
    assert receipt["source_sha256"] == stager.sha256(source)
    assert receipt["artifact_sha256"] == hashlib.sha256(expected).hexdigest()


def test_synthetic_stager_copies_current_member_transfer_and_records_its_digest(prepared):
    """Copy the reviewed helper as bytes; neither it nor synthetic Core is run."""
    c = prepared
    source = Path(__file__).resolve().parents[1] / "services/python-workers/document/member_transfer.py"
    expected = source.read_bytes()
    assert expected
    fixture_helper = c["repo"] / "services/python-workers/document/member_transfer.py"
    stager.filesystem_path(fixture_helper.parent).mkdir(parents=True)
    stager.filesystem_path(fixture_helper).write_bytes(expected)

    assert run_stager(c) == 0

    relative = "workers/document/member_transfer.py"
    staged = stager.filesystem_path(c["output"] / relative)
    assert staged.read_bytes() == expected
    manifest = json.loads(stager.filesystem_path(c["output"] / "backend-runtime-manifest.json").read_bytes())
    assert manifest["files"][relative] == {"bytes": len(expected), "sha256": hashlib.sha256(expected).hexdigest()}
