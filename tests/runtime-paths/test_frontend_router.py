"""Real Git routing with controlled compiler processes; actual npm build is separately run."""
import importlib.util
import json
import os
import subprocess
import sys
import shutil
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
    subprocess.run(["git", "-C", str(root), "add", ".gitignore"], check=True)
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
