"""Real Git routing with controlled compiler processes; actual npm build is separately run."""
import importlib.util
import json
import os
import subprocess
import sys
import shutil
import hashlib
from pathlib import Path

import pytest

RUNTIME = Path(__file__).resolve().parents[2] / "scripts/runtime"
sys.path.insert(0, str(RUNTIME))
spec = importlib.util.spec_from_file_location("frontend_router", RUNTIME / "frontend.py")
router = importlib.util.module_from_spec(spec)
spec.loader.exec_module(router)
sys.path.pop(0)


def successful_compiler(*args, **kwargs):
    dist = Path(kwargs["env"]["ARCHEAXIS_FRONTEND_DIST"])
    dist.mkdir(parents=True, exist_ok=True)
    (dist / "index.html").write_text("synthetic compiler fixture", encoding="utf-8")
    return 0


@pytest.fixture
def project(tmp_path, monkeypatch):
    for name in list(os.environ):
        if name.startswith("ARCHEAXIS_") or name in {"TAURI_CONFIG", "CARGO_TARGET_DIR"}:
            monkeypatch.delenv(name)
    root = tmp_path / "项目 with spaces"
    root.mkdir()
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    (root / ".gitignore").write_text(".project-local/\n", encoding="utf-8")
    resources = ("runtime", "core", "workers", "shared", "worker-profile.json",
                 "start-backend.py", "start-backend.cmd", "backend-runtime-manifest.json",
                 "vcruntime140.dll", "vcruntime140_1.dll")
    (root / "src-tauri").mkdir()
    (root / "src-tauri/tauri.conf.json").write_text(json.dumps({"bundle": {"resources": {
        "../.project-local/rt/" + name: name for name in resources}}}), encoding="utf-8")
    subprocess.run(["git", "-C", str(root), "add", ".gitignore", "src-tauri/tauri.conf.json"], check=True)
    subprocess.run(["git", "-C", str(root), "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-qm", "fixture"], check=True)
    return root


def test_default_builds_allocate_distinct_runs_and_preserve_outputs(project, monkeypatch):
    commands = []
    def compiler(command, cwd, env):
        commands.append((command, env))
        if "vite.js" in command[1]:
            dist = Path(env["ARCHEAXIS_FRONTEND_DIST"])
            dist.mkdir()
            (dist / "index.html").write_text(dist.parent.parent.name)
        return 0
    monkeypatch.setattr(router.subprocess, "call", compiler)
    assert router.build(project, "node", "build", []) == 0
    assert router.build(project, "node", "build", []) == 0
    receipts = sorted((project / ".project-local/runs").glob("*/*/artifacts/frontend-build.json"))
    assert len(receipts) == 2
    values = [json.loads(p.read_text()) for p in receipts]
    assert values[0]["frontend_dist"] != values[1]["frontend_dist"]
    for value in values:
        assert Path(value["frontend_dist"]).is_relative_to(Path(value["run_root"]))
        assert (Path(value["frontend_dist"]) / "index.html").exists()
        configured = json.loads(Path(value["tauri_config"]).read_text())["build"]["frontendDist"]
        assert ":" not in configured and not Path(configured).is_absolute()
        assert (project / "src-tauri" / configured).resolve() == Path(value["frontend_dist"])
    assert not (project / ".project-local/build/frontend-dist").exists()


def test_tauri_overlay_is_last_config_before_runner_arguments_and_hook_reuses_run(project, monkeypatch):
    parent_env = {}
    def compiler(command, cwd, env):
        parent_env.update(env)
        assert command[-5:] == ["--config", env["ARCHEAXIS_TAURI_CONFIG"], "--", "--offline", "--locked"]
        with monkeypatch.context() as inner:
            inner.setattr(router.subprocess, "call", successful_compiler)
            for name, value in env.items():
                inner.setenv(name, value)
            assert router.build(project, "node", "build", []) == 0
        return 0
    monkeypatch.setattr(router.subprocess, "call", compiler)
    assert router.build(project, "node", "tauri", ["build", "--config", "custom.json", "--", "--offline", "--locked"]) == 0
    assert len(list((project / ".project-local/runs").glob("*/*"))) == 1
    assert Path(parent_env["ARCHEAXIS_FRONTEND_DIST"]).parent.name == "artifacts"


def test_foreign_inherited_paths_fail_before_allocating_run(project, monkeypatch):
    monkeypatch.setenv("ARCHEAXIS_WORKTREE_ROOT", str(project.parent / "other"))
    with pytest.raises(ValueError, match="foreign inherited"):
        router.build(project, "node", "build", [])
    assert not (project / ".project-local").exists()


def test_two_builds_inherited_from_one_existing_run_still_allocate_separately(project, monkeypatch):
    parent = router.dev.layout(project, "parent")
    env = router.dev.prepare(parent)
    for name, value in env.items():
        monkeypatch.setenv(name, value)
    monkeypatch.setattr(router.subprocess, "call", successful_compiler)
    assert router.build(project, "node", "build", []) == 0
    assert router.build(project, "node", "build", []) == 0
    receipts = list((project / ".project-local/runs").glob("*/*/artifacts/frontend-build.json"))
    values = [json.loads(path.read_text()) for path in receipts]
    assert len(values) == 2
    assert len({value["frontend_dist"] for value in values}) == 2
    assert all(value["run_root"] != str(parent["run"]) for value in values)


def test_ci_cargo_target_is_preserved_but_foreign_target_is_refused(project, monkeypatch):
    paths = router.dev.layout(project, "parent")
    target = paths["dev"] / "build" / "tauri"
    monkeypatch.setenv("CARGO_TARGET_DIR", str(target))
    observed = []
    monkeypatch.setattr(router.subprocess, "call", lambda *args, **kwargs: observed.append(kwargs["env"]["CARGO_TARGET_DIR"]) or successful_compiler(*args, **kwargs))
    assert router.build(project, "node", "tauri", ["build"]) == 0
    assert observed == [str(target)]
    monkeypatch.setenv("CARGO_TARGET_DIR", str(project.parent / "foreign"))
    with pytest.raises(ValueError, match="foreign inherited CARGO_TARGET_DIR"):
        router.build(project, "node", "tauri", ["build"])


def test_tauri_build_uses_its_own_target_when_parent_routes_core(project, monkeypatch):
    paths = router.dev.layout(project, "parent-core")
    monkeypatch.setenv("CARGO_TARGET_DIR", str(paths["cargo_build"]))
    observed = []
    monkeypatch.setattr(router.subprocess, "call", lambda *args, **kwargs: observed.append(kwargs["env"]["CARGO_TARGET_DIR"]) or successful_compiler(*args, **kwargs))
    assert router.build(project, "node", "tauri", ["build"]) == 0
    assert observed == [str(paths["tauri_build"])]
    assert paths["cargo_build"] != paths["tauri_build"]


def qualified_core(project, monkeypatch, compiler_exit=0, write_output=True):
    """Actual runner receipt generation around a synthetic compiler process."""
    import io
    class Compiler:
        stdout = io.StringIO("synthetic Core compiler\n")
        def wait(self):
            return compiler_exit
    real_popen = router.dev.subprocess.Popen
    def launch(*args, **kwargs):
        if not any("cargo_test.bat" in str(part) for part in args[0]):
            return real_popen(*args, **kwargs)
        path = Path(kwargs["env"]["CARGO_TARGET_DIR"]) / "release/archeaxis-api.exe"
        if write_output:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"synthetic-core")
        return Compiler()
    with monkeypatch.context() as child:
        child.setattr(router.dev.subprocess, "Popen", launch)
        child.setattr(sys, "argv", ["dev.py", "--root", str(project), "--run-id", "core",
                                  "--qualify-core-build", "--", *router.dev.core_build_command(project)])
        assert router.dev.main() == (compiler_exit or (0 if write_output else 2))
    return router.dev.layout(project, "core")["artifacts"] / "execution.json"


def staged_runtime(project):
    """Complete synthetic resource contract; it is never an executable runtime."""
    staged = project / ".project-local/rt"
    payloads = {
        "runtime/python.exe": b"synthetic-interpreter",
        "core/archeaxis-api.exe": b"synthetic-core",
        "workers/transport/text_ndjson.py": b"synthetic transport",
        "workers/document/worker.py": b"synthetic worker",
        "shared/learning_scheduler.py": b"synthetic scheduler",
        "start-backend.py": b"synthetic launcher",
        "start-backend.cmd": b"synthetic launcher cmd",
        "vcruntime140.dll": b"synthetic vcruntime",
        "core/vcruntime140.dll": b"synthetic vcruntime",
        "runtime/vcruntime140.dll": b"synthetic vcruntime",
        "vcruntime140_1.dll": b"synthetic vcruntime one",
        "core/vcruntime140_1.dll": b"synthetic vcruntime one",
        "runtime/vcruntime140_1.dll": b"synthetic vcruntime one",
        "workers/routes.json": json.dumps({"schema": "archeaxis.worker-routes/v1", "routes": {
            "document.detect": ["document/worker.py"]}}).encode(),
        "worker-profile.json": json.dumps({"schema": "archeaxis.worker-profile/v1",
            "python": "runtime/python.exe", "script": "workers/transport/text_ndjson.py",
            "staging": "data/worker-staging", "routes": [{"capability": "document.detect",
                "script": "workers/document/worker.py"}]}).encode(),
    }
    members = {}
    for name, content in payloads.items():
        path = staged / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        members[name] = {"bytes": len(content), "sha256": hashlib.sha256(content).hexdigest()}
    (staged / "backend-runtime-manifest.json").write_text(json.dumps({
        "schema": "archeaxis.backend-runtime/v1", "files": members,
        "runtime_source": {"evidence": "SYNTHETIC_NOT_RUNTIME_QUALIFIED"}}), encoding="utf-8")
    return staged


def test_canonical_builder_receipt_connects_actual_tauri_target_to_portable(project, monkeypatch):
    from scripts.release import tauri_portable_candidate as portable
    monkeypatch.setattr(portable.runtime_resources, "verify_fixed_webview2",
                        lambda root: {"version": "synthetic", "path": "runtime/webview2",
                                      "manifest_sha256": "0" * 64, "executable_sha256": "0" * 64})
    core_receipt = qualified_core(project, monkeypatch)
    core = json.loads(core_receipt.read_text(encoding="utf-8"))
    assert core["core_build"]["artifact"]["sha256"] == __import__("hashlib").sha256(b"synthetic-core").hexdigest()
    staged = staged_runtime(project)
    monkeypatch.setattr(router.runtime_resources, "verify_fixed_webview2",
                        lambda root: {"version": "synthetic", "path": "runtime/webview2",
                                      "manifest_sha256": "0" * 64, "executable_sha256": "0" * 64})
    def compiler(*args, **kwargs):
        successful_compiler(*args, **kwargs)
        target = Path(kwargs["env"]["CARGO_TARGET_DIR"]) / "release"
        target.mkdir(parents=True, exist_ok=True)
        (target / "ArcheAxis.exe").write_bytes(b"synthetic-host")
        shutil.copytree(staged, target, dirs_exist_ok=True)
        return 0
    monkeypatch.setattr(router.subprocess, "call", compiler)
    assert router.build(project, "node", "tauri", ["build", "--no-bundle", "--", "--offline", "--locked"],
                        core_build_receipt=core_receipt) == 0
    receipt_path = next((project / ".project-local/runs").glob("*/*/artifacts/frontend-build.json"))
    build = json.loads(receipt_path.read_text(encoding="utf-8"))
    paths = router.dev.layout(project, "check")
    env = router.dev.environment(paths)
    host = portable.qualified_host(receipt_path, build, paths, env)
    assert host == paths["tauri_build"] / "release/ArcheAxis.exe"
    assert host != paths["cargo_build"] / "release/ArcheAxis.exe"
    assert portable.plan(host, build, portable.RESOURCES)["status"] == "PLAN"
    for key, value in [("host", str(paths["cargo_build"] / "release/ArcheAxis.exe")),
                       ("host_sha256", "0" * 64), ("source_patch_sha256", "0" * 64),
                       ("exit_code", 1), ("mode", "build"), ("status", "RUNNING"),
                       ("portable_build_arguments", ["build", "--help"])]:
        altered = {**build, key: value}
        with pytest.raises(ValueError):
            portable.qualified_host(receipt_path, altered, paths, env)
    with pytest.raises(ValueError):
        portable.qualified_host(receipt_path, {"status": "PASS", "host": str(host),
                                "host_sha256": build["host_sha256"]}, paths, env)
    timing_path = Path(build["build_timings"]["path"])
    timing = json.loads(timing_path.read_text(encoding="utf-8"))
    timing["stages"][0]["status"] = "RUNNING"
    timing_path.write_text(json.dumps(timing), encoding="utf-8")
    unfinished = {**build, "build_timings": router.dev.build_file_identity(timing_path)}
    with pytest.raises(ValueError, match="stages are incomplete"):
        portable.qualified_host(receipt_path, unfinished, paths, env)
    (host.parent / "core/archeaxis-api.exe").write_bytes(b"changed-after-build")
    with pytest.raises(ValueError):
        portable.qualified_host(receipt_path, build, paths, env)


@pytest.mark.parametrize("change", ["extra", "missing", "corrupt", "worker_contract"])
def test_qualified_builder_rejects_incomplete_resource_namespace(project, monkeypatch, change):
    from scripts.release import tauri_portable_candidate as portable
    monkeypatch.setattr(portable.runtime_resources, "verify_fixed_webview2",
                        lambda root: {"version": "synthetic", "path": "runtime/webview2",
                                      "manifest_sha256": "0" * 64, "executable_sha256": "0" * 64})
    core_receipt = qualified_core(project, monkeypatch)
    staged = staged_runtime(project)
    monkeypatch.setattr(router.runtime_resources, "verify_fixed_webview2",
                        lambda root: {"version": "synthetic", "path": "runtime/webview2",
                                      "manifest_sha256": "0" * 64, "executable_sha256": "0" * 64})
    if change == "worker_contract":
        path = staged / "worker-profile.json"
        profile = json.loads(path.read_text())
        profile["routes"] = []
        path.write_text(json.dumps(profile), encoding="utf-8")
        manifest = staged / "backend-runtime-manifest.json"
        value = json.loads(manifest.read_text())
        value["files"]["worker-profile.json"] = {"bytes": path.stat().st_size,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
        manifest.write_text(json.dumps(value), encoding="utf-8")
    output = None
    def compiler(*args, **kwargs):
        nonlocal output
        successful_compiler(*args, **kwargs)
        output = Path(kwargs["env"]["CARGO_TARGET_DIR"]) / "release"
        output.mkdir(parents=True, exist_ok=True)
        (output / "ArcheAxis.exe").write_bytes(b"synthetic-host")
        shutil.copytree(staged, output, dirs_exist_ok=True)
        if change == "extra":
            stale = output / "runtime/Lib/site-packages/certifi-old.dist-info/METADATA"
            Path(portable.native(stale.parent)).mkdir(parents=True)
            Path(portable.native(stale)).write_bytes(b"owned synthetic stale distribution metadata")
        elif change == "missing":
            Path(portable.native(output / "workers/document/worker.py")).unlink()
        elif change == "corrupt":
            Path(portable.native(output / "runtime/python.exe")).write_bytes(b"corrupted-interpreter")
        return 0
    monkeypatch.setattr(router.subprocess, "call", compiler)
    with pytest.raises((ValueError, FileNotFoundError)):
        router.build(project, "node", "tauri", ["build", "--no-bundle", "--", "--offline", "--locked"],
                     core_build_receipt=core_receipt)
    receipt_path = next((project / ".project-local/runs").glob("*/*/artifacts/frontend-build.json"))
    value = json.loads(receipt_path.read_text())
    assert value["exit_code"] != 0 and value.get("status") != "PASS"
    assert "host_sha256" not in value
    assert value["source_consistent"] is True
    assert output is not None
    if change == "extra":
        assert Path(portable.native(output / "runtime/Lib/site-packages/certifi-old.dist-info/METADATA")).read_bytes() == b"owned synthetic stale distribution metadata"


@pytest.mark.parametrize("change", ["missing_hash", "other_crate", "debug", "changed_source", "failed"])
def test_core_qualification_rejects_incomplete_or_unrelated_receipts(project, monkeypatch, change):
    path = qualified_core(project, monkeypatch)
    value = json.loads(path.read_text(encoding="utf-8"))
    if change == "missing_hash":
        value.pop("core_build")
    elif change == "other_crate":
        value["command"][-1] = "archeaxis-domain"
    elif change == "debug":
        value["command"].remove("--release")
    elif change == "changed_source":
        value["source_patch_sha256_after"] = "0" * 64
    else:
        value["child_exit_code"] = 1
    path.write_text(json.dumps(value), encoding="utf-8")
    paths = router.dev.layout(project, "verify")
    with pytest.raises(ValueError):
        router.dev.read_core_build(path, paths, router.dev.environment(paths))


@pytest.mark.parametrize("exit_code,output", [(23, True), (0, False)])
def test_failed_or_outputless_core_build_never_acquires_qualification(project, monkeypatch, exit_code, output):
    path = qualified_core(project, monkeypatch, exit_code, output)
    value = json.loads(path.read_text(encoding="utf-8"))
    assert value["status"] == "FAIL"
    assert value["exit_code"] != 0
    assert "core_build" not in value


def test_separate_nsis_bundle_retains_config_features_and_failure(project, monkeypatch):
    commands = []
    def execute(command, **kwargs):
        commands.append(command)
        successful_compiler(command, **kwargs)
        return 23 if command[2] == "bundle" else 0
    monkeypatch.setattr(router.subprocess, "call", execute)
    arguments = ["build", "--config", "src-tauri/tauri.conf.json", "--bundles", "nsis", "--features", "custom-protocol"]
    assert router.build(project, "node", "tauri", arguments, separate_bundle=True) == 23
    assert [command[2] for command in commands] == ["build", "bundle"]
    assert "--no-bundle" in commands[0] and "--bundles" not in commands[0]
    assert "--bundles" in commands[1] and commands[1][-1] == "nsis"
    for command in commands:
        assert "custom-protocol" in command and "src-tauri/tauri.conf.json" in command
    assert commands[0][commands[0].index("--config", 5) + 1] == commands[1][commands[1].index("--config", 5) + 1]
    reports = [json.loads(path.read_text()) for path in (project / ".project-local/runs").glob("*/*/artifacts/bt-*.json")]
    assert [(stage["name"], stage["status"]) for stage in reports[0]["stages"]] == [("tauri-compile-with-frontend-hook", "PASS"), ("nsis-bundle", "FAIL")]
    receipt = next((project / ".project-local/runs").glob("*/*/artifacts/frontend-build.json"))
    assert json.loads(receipt.read_text())["exit_code"] == 23


def test_separate_bundling_never_runs_after_compilation_failure(project, monkeypatch):
    commands = []
    monkeypatch.setattr(router.subprocess, "call", lambda command, **_: commands.append(command) or 17)
    assert router.build(project, "node", "tauri", ["build", "--bundles", "nsis"], separate_bundle=True) == 17
    assert len(commands) == 1 and commands[0][2] == "build"
    with pytest.raises(ValueError, match="raw Cargo arguments"):
        router.tauri_commands("node", "cli", ["build", "--", "--locked"], "overlay", True)


def test_foreign_dist_or_injected_nested_context_is_refused(project, monkeypatch):
    paths = router.dev.layout(project, "fixture")
    env = router.dev.prepare(paths)
    for name, value in env.items():
        monkeypatch.setenv(name, value)
    monkeypatch.setenv("ARCHEAXIS_FRONTEND_DIST", str(project / "foreign"))
    with pytest.raises(ValueError, match="foreign inherited"):
        router.build(project, "node", "build", [])
    monkeypatch.setenv("ARCHEAXIS_FRONTEND_DIST", env["ARCHEAXIS_FRONTEND_DIST"])
    monkeypatch.setenv("ARCHEAXIS_FRONTEND_BUILD_CONTEXT", "foreign")
    with pytest.raises(ValueError, match="invalid nested"):
        router.build(project, "node", "build", [])


def test_build_failures_are_recorded_and_outdir_override_is_refused(project, monkeypatch):
    monkeypatch.setattr(router.subprocess, "call", lambda *args, **kwargs: 17)
    assert router.build(project, "node", "build", []) == 17
    receipt = next((project / ".project-local/runs").glob("*/*/artifacts/frontend-build.json"))
    assert json.loads(receipt.read_text())["exit_code"] == 17
    with pytest.raises(ValueError, match="owned by the run"):
        router.build(project, "node", "build", ["--outDir", "foreign"])


def test_source_mutation_cannot_return_success_or_a_consistent_receipt(project, monkeypatch):
    def compiler(*args, **kwargs):
        (project / "mutated-source.txt").write_text("fixture change")
        return 0
    monkeypatch.setattr(router.subprocess, "call", compiler)
    with pytest.raises(ValueError, match="source changed during build"):
        router.build(project, "node", "build", [])
    receipt = next((project / ".project-local/runs").glob("*/*/artifacts/frontend-build.json"))
    value = json.loads(receipt.read_text())
    assert value["exit_code"] == 2
    assert value["source_consistent"] is False
    assert value["source_patch_sha256"] != value["source_patch_sha256_after"]


def test_linked_worktree_uses_owner_with_different_identity(project, monkeypatch):
    linked = project / ".project-local/worktrees/linked"
    subprocess.run(["git", "-C", str(project), "worktree", "add", "--detach", str(linked)], check=True, capture_output=True)
    monkeypatch.setattr(router.subprocess, "call", successful_compiler)
    assert router.build(linked, "node", "build", []) == 0
    receipt = next((project / ".project-local/runs").glob("*/*/artifacts/frontend-build.json"))
    value = json.loads(receipt.read_text())
    assert value["worktree_root"] == str(linked)
    assert not (linked / ".project-local").exists()


def test_reparse_run_is_refused_before_overlay_read(project, monkeypatch):
    paths = router.dev.layout(project, "fixture")
    paths["run"].parent.mkdir(parents=True)
    target = project.parent / "outside"
    target.mkdir()
    try:
        paths["run"].symlink_to(target, target_is_directory=True)
    except OSError:
        pytest.skip("directory symlink unavailable")
    monkeypatch.setenv("ARCHEAXIS_RUN_ROOT", str(paths["run"]))
    with pytest.raises(ValueError, match="linked"):
        router.build(project, "node", "build", [])


def test_raw_tauri_hook_cannot_silently_build_into_an_unconsumed_path(project, monkeypatch):
    monkeypatch.setenv("TAURI_CONFIG", '{"build":{"frontendDist":"old"}}')
    with pytest.raises(ValueError, match="raw Tauri hook"):
        router.build(project, "node", "build", [])
    assert not (project / ".project-local").exists()


def test_help_exit_without_frontend_artifact_cannot_issue_a_success_receipt(project, monkeypatch):
    monkeypatch.setattr(router.subprocess, "call", lambda *args, **kwargs: 0)
    with pytest.raises(ValueError, match="without this run's index"):
        router.build(project, "node", "tauri", ["build", "--help"])
    receipt = next((project / ".project-local/runs").glob("*/*/artifacts/frontend-build.json"))
    assert json.loads(receipt.read_text())["exit_code"] == 2


def node_binary():
    found = shutil.which("node")
    if found:
        return found
    index = json.loads((RUNTIME.parents[1] / "config/environment/external-resources-index.json").read_text(encoding="utf-8"))
    for row in index.get("entries", []):
        if row.get("resource_id", row.get("id")) == "ext.toolchains.nodejs-lts":
            found = row.get("resolved_absolute")
            if found and Path(found).is_file():
                return found
    pytest.skip("declared Node unavailable")


def test_node_protected_paths_rejected_before_filesystem_probe():
    node = node_binary()
    module = (RUNTIME / "frontend_paths.mjs").as_uri()
    script = f'import {{safePath}} from {json.dumps(module)}; import fs from "node:fs"; import {{syncBuiltinESMExports}} from "node:module"; fs.lstatSync=()=>{{throw Error("unexpected filesystem probe")}};syncBuiltinESMExports(); for(const path of ["E:/protected","F:/protected","//server/share"]){{try{{safePath(path);process.exit(3)}}catch(error){{if(!error.message.includes("protected drive or UNC"))throw error;}}}}'
    result = subprocess.run([node, "--input-type=module", "-e", script], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_node_explicit_python_precedes_stale_managed_environment():
    node = node_binary()
    module = (RUNTIME / "frontend_paths.mjs").as_uri()
    root = RUNTIME.parents[1]
    script = f'import {{projectPython}} from {json.dumps(module)}; console.log(projectPython({json.dumps(str(root))}));'
    interpreter = Path(sys.executable).resolve()
    env = dict(os.environ, ARCHEAXIS_PYTHON=str(interpreter))
    # An explicit interpreter must not depend on Git/PATH or a managed .venv.
    env["PATH"] = ""
    result = subprocess.run([node, "--input-type=module", "-e", script], env=env,
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert Path(result.stdout.strip()) == interpreter


def test_node_explicit_python_keeps_protected_path_guard():
    node = node_binary()
    module = (RUNTIME / "frontend_paths.mjs").as_uri()
    script = f'import {{projectPython}} from {json.dumps(module)}; try{{projectPython({json.dumps(str(RUNTIME.parents[1]))});process.exit(3)}}catch(error){{if(!error.message.includes("protected drive or UNC"))throw error;}}'
    result = subprocess.run([node, "--input-type=module", "-e", script],
                            env=dict(os.environ, ARCHEAXIS_PYTHON="E:/protected/python.exe"),
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("override", ["environment", "cli"])
def test_direct_vite_rejects_foreign_environment_or_cli_output_before_clear(tmp_path, monkeypatch, override):
    node = node_binary()
    for name in list(os.environ):
        if name.startswith("ARCHEAXIS_") or name == "TAURI_CONFIG":
            monkeypatch.delenv(name)
    root = RUNTIME.parents[1]
    paths = router.dev.layout(root)
    env = dict(os.environ)
    env.update(router.dev.prepare(paths))
    foreign = tmp_path / "foreign-output"
    foreign.mkdir()
    marker = foreign / "keep.txt"
    marker.write_text("unique fixture")
    command = [node, str(root / "frontend/node_modules/vite/bin/vite.js"), "build"]
    if override == "environment":
        env["ARCHEAXIS_FRONTEND_DIST"] = str(foreign)
    else:
        command += ["--outDir", str(foreign)]
    result = subprocess.run(command, cwd=root / "frontend", env=env, capture_output=True, text=True, encoding="utf-8")
    assert result.returncode != 0, result.stdout
    assert marker.read_text() == "unique fixture"
    assert not (foreign / "index.html").exists()


def test_node_reparse_ancestor_rejected(tmp_path):
    node = node_binary()
    outside = tmp_path / "outside"
    outside.mkdir()
    link = tmp_path / "linked"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("directory symlink unavailable")
    module = (RUNTIME / "frontend_paths.mjs").as_uri()
    script = f'import {{safePath}} from {json.dumps(module)};try{{safePath({json.dumps(str(link / "new-output"))});process.exit(3)}}catch(error){{if(!error.message.includes("linked frontend path"))throw error;}}'
    result = subprocess.run([node, "--input-type=module", "-e", script], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


@pytest.mark.skipif(os.name != "nt", reason="official Windows compiler environment")
@pytest.mark.parametrize("inherited_path", ["long", "missing-system32"])
def test_official_msvc_discovers_sdk_despite_broken_inherited_path(project, inherited_path):
    tools = router.dev.external_toolchain(RUNTIME.parents[1])
    if not tools.get("ARCHEAXIS_MSVC_VCVARS"):
        pytest.skip("declared MSVC unavailable")
    paths = router.dev.layout(project)
    router.dev.prepare(paths)
    env = {k: v for k, v in os.environ.items() if k.casefold() != "path"}
    env.update(tools)
    git = shutil.which("git")
    assert git
    env["PATH"] = str(Path(git).parent)
    if inherited_path == "long":
        env["PATH"] += os.pathsep + (str(paths["tmp"] / "unavailable-tool-directory") + os.pathsep) * 150
        assert len(env["PATH"]) > 8191
    result = router.msvc_environment(env, paths, node_binary())
    assert len(result["PATH"]) < 8191
    assert str(Path(env.get("SystemRoot", "C:/Windows")) / "System32").casefold() in result["PATH"].casefold()
    assert all(any((Path(folder) / name).is_file() for folder in result["LIB"].split(os.pathsep))
               for name in ("kernel32.lib", "ucrt.lib"))
    assert all(any((Path(folder) / name).is_file() for folder in result["INCLUDE"].split(os.pathsep))
               for name in ("Windows.h", "corecrt.h"))
    assert env["PATH"] != result["PATH"]


@pytest.mark.skipif(os.name != "nt", reason="cmd compiler fixture")
def test_msvc_exit_zero_without_sdk_is_rejected(project):
    paths = router.dev.layout(project)
    router.dev.prepare(paths)
    compiler = paths["tmp"] / "fixture-vcvars.cmd"
    compiler.write_text('@echo off\nset "LIB="\nset "INCLUDE="\nset "LIBPATH="\nexit /b 0\n', encoding="utf-8")
    env = dict(os.environ)
    env["ARCHEAXIS_MSVC_VCVARS"] = str(compiler)
    with pytest.raises(ValueError, match="lacks SDK kernel32.lib"):
        router.msvc_environment(env, paths)
