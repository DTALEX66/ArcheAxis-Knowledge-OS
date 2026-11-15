"""Physical-stage admission and hook binding; compiler/runtime bytes are synthetic.

No Node, Cargo, model, installer, or previously qualified runtime is executed.
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts.runtime import frontend as router


COMMAND = ["build", "--no-bundle", "--", "--offline", "--locked"]


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(value if isinstance(value, bytes) else json.dumps(value).encode())
    return {"bytes": path.stat().st_size, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


@pytest.fixture
def candidate(tmp_path, monkeypatch):
    for name in list(os.environ):
        if name.startswith("ARCHEAXIS_") or name in {"TAURI_CONFIG", "CARGO_TARGET_DIR"}:
            monkeypatch.delenv(name)
    root = tmp_path / "p"
    root.mkdir()
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    (root / ".gitignore").write_text(".project-local/\n", encoding="utf-8")
    old = {"../.project-local/rt/" + name: name for name in router.runtime_resources.RESOURCES}
    write(root / "src-tauri/tauri.conf.json", {"build": {"beforeBuildCommand": "npm run build"},
                                               "bundle": {"resources": old}})
    subprocess.run(["git", "-C", str(root), "add", ".gitignore", "src-tauri/tauri.conf.json"], check=True)
    subprocess.run(["git", "-C", str(root), "-c", "user.name=Fixture", "-c",
                    "user.email=fixture@example.invalid", "commit", "-qm", "synthetic"], check=True)
    paths = router.dev.layout(root, "c")
    env = router.dev.prepare(paths)
    core = paths["cargo_build"] / "release/archeaxis-api.exe"
    write(core, b"synthetic Core, not executable")
    receipt = paths["artifacts"] / "execution.json"
    write(receipt, {"status": "LOCAL_PASS", "exit_code": 0, "child_exit_code": 0,
                    "source_consistent": True, "worktree_root": str(root), "run_root": str(paths["run"]),
                    "command": router.dev.core_build_command(root),
                    "source_commit": env["ARCHEAXIS_SOURCE_COMMIT"],
                    "source_commit_after": env["ARCHEAXIS_SOURCE_COMMIT"],
                    "source_tree": env["ARCHEAXIS_SOURCE_TREE"],
                    "source_patch_sha256": env["ARCHEAXIS_SOURCE_PATCH_SHA256"],
                    "source_patch_sha256_after": env["ARCHEAXIS_SOURCE_PATCH_SHA256"],
                    "core_build": {"schema": "archeaxis.core-build/v1", "artifact": router.dev.build_file_identity(core)}})
    stage = router.dev.layout(root, "s")["artifacts"] / "rt"
    payloads = {
        "core/archeaxis-api.exe": core.read_bytes(), "runtime/python.exe": b"synthetic Python",
        "workers/transport/text_ndjson.py": b"synthetic transport", "workers/document/worker.py": b"synthetic worker",
        "shared/learning_scheduler.py": b"synthetic shared", "start-backend.py": b"synthetic launcher",
        "start-backend.cmd": b"synthetic launcher cmd",
        "workers/routes.json": {"schema": "archeaxis.worker-routes/v1", "routes": {"document.detect": ["document/worker.py"]}},
        "worker-profile.json": {"schema": "archeaxis.worker-profile/v1", "python": "runtime/python.exe",
                                "script": "workers/transport/text_ndjson.py", "staging": "data/worker-staging",
                                "routes": [{"capability": "document.detect", "script": "workers/document/worker.py"}]},
    }
    for name in ("vcruntime140.dll", "vcruntime140_1.dll"):
        for prefix in ("", "core/", "runtime/"):
            payloads[prefix + name] = b"synthetic VC " + name.encode()
    webview = {name: write(stage / "runtime/webview2" / name, b"synthetic " + name.encode())
               for name in ("msedgewebview2.exe", "msedge.dll")}
    payloads["runtime/webview2/aaos-fixed-runtime-manifest.json"] = {
        "schema": "archeaxis.official-fixed-runtime-files/v1", "version": "synthetic",
        "files": [{"path": name, **row} for name, row in webview.items()]}
    members = {name: write(stage / name, value) for name, value in payloads.items()}
    members.update({"runtime/webview2/" + name: row for name, row in webview.items()})
    monkeypatch.setattr(router.runtime_resources, "FIXED_WEBVIEW2_MANIFEST_SHA256",
                        members["runtime/webview2/aaos-fixed-runtime-manifest.json"]["sha256"])
    pin = write(stage / "backend-runtime-manifest.json", {"schema": "archeaxis.backend-runtime/v1", "files": members})["sha256"]
    # The mutable legacy alias tree must not be read or changed by this route.
    write(root / ".project-local/rt/unchanged", b"legacy alias fixture")
    return root, stage, pin, receipt, old


def invoke(candidate, **changes):
    root, stage, pin, receipt, _ = candidate
    kwargs = {"core_build_receipt": receipt, "runtime_root": stage, "runtime_manifest_sha256": pin}
    kwargs.update(changes)
    return router.build(root, "synthetic-node", "tauri", COMMAND, **kwargs)


def output_fixture(env, stage):
    dist = Path(env["ARCHEAXIS_FRONTEND_DIST"])
    write(dist / "index.html", b"synthetic frontend")
    target = Path(env["CARGO_TARGET_DIR"]) / "release"
    write(target / "ArcheAxis.exe", b"synthetic Host")
    shutil.copytree(stage, target, dirs_exist_ok=True)
    return target


def test_physical_stage_maps_exactly_ten_resources_and_nested_hook_and_verify(candidate, monkeypatch):
    root, stage, pin, _, old = candidate
    def compiler(command, cwd, env):
        overlay = json.loads(Path(env["ARCHEAXIS_TAURI_CONFIG"]).read_text())
        resources = overlay["bundle"]["resources"]
        assert {key for key, value in resources.items() if value is None} == set(old)
        # Apply JSON Merge Patch map semantics, matching Tauri's pinned CLI.
        merged = dict(old)
        for key, value in resources.items():
            if value is None:
                merged.pop(key, None)
            else:
                merged[key] = value
        assert merged == {str(stage / name): name for name in router.runtime_resources.RESOURCES}
        assert "beforeBuildCommand" not in overlay["build"]
        with monkeypatch.context() as nested:
            for name, value in env.items():
                nested.setenv(name, value)
            nested.setattr(router, "ROOT", root)
            nested.setattr(sys, "argv", ["frontend.py", "--node", "synthetic-node", "verify"])
            assert router.main() == 0
            nested.setattr(router.subprocess, "call", lambda *a, **kw: write(
                Path(kw["env"]["ARCHEAXIS_FRONTEND_DIST"]) / "index.html", b"synthetic nested") and 0)
            assert router.build(root, "synthetic-node", "build", []) == 0
        output_fixture(env, stage)
        return 0
    monkeypatch.setattr(router.subprocess, "call", compiler)
    assert invoke(candidate) == 0
    receipts = list((root / ".project-local/runs").glob("*/*/artifacts/frontend-build.json"))
    assert len(receipts) == 1
    result = json.loads(receipts[0].read_text())
    assert result["status"] == "PASS" and result["source_consistent"] is True
    assert result["runtime_input"]["root"] == str(stage)
    assert result["runtime_input"]["manifest"]["sha256"] == pin
    assert (root / ".project-local/rt/unchanged").read_bytes() == b"legacy alias fixture"
    assert (stage / "backend-runtime-manifest.json").stat().st_nlink == 1


@pytest.mark.parametrize("change", ["missing_root", "missing_pin", "missing_core", "raw_config"])
def test_physical_binding_rejects_incomplete_or_overriding_arguments_before_compiler(candidate, monkeypatch, change):
    called = []
    monkeypatch.setattr(router.subprocess, "call", lambda *a, **kw: called.append(True))
    kwargs = {"runtime_root": None} if change == "missing_root" else {"runtime_manifest_sha256": None}
    if change == "missing_core":
        kwargs = {"core_build_receipt": None}
    with pytest.raises(ValueError, match="paired root/pin"):
        if change == "raw_config":
            root, stage, pin, receipt, _ = candidate
            router.build(root, "node", "tauri", [*COMMAND[:2], "--config", "foreign.json", *COMMAND[2:]],
                         core_build_receipt=receipt, runtime_root=stage, runtime_manifest_sha256=pin)
        else:
            invoke(candidate, **kwargs)
    assert not called


@pytest.mark.parametrize("change", ["pin", "core", "namespace", "foreign_root", "hardlink"])
def test_physical_stage_rejects_unbound_input_before_compiler(candidate, monkeypatch, change):
    root, stage, _, _, _ = candidate
    kwargs = {}
    if change == "pin":
        kwargs["runtime_manifest_sha256"] = "0" * 64
    elif change == "core":
        (stage / "core/archeaxis-api.exe").write_bytes(b"different Core")
    elif change == "namespace":
        write(stage / "runtime/unmanifested", b"extra")
    elif change == "foreign_root":
        kwargs["runtime_root"] = root / ".project-local/rt"
    elif change == "hardlink":
        # SIMULATED metadata only: this verifies that the frontend consumes the
        # existing independent-file guard, not Windows hardlink creation rights.
        real_lstat = os.lstat
        profile = os.path.normcase(os.path.abspath(stage / "worker-profile.json"))
        def observed_lstat(path, *args, **kwargs):
            info = real_lstat(path, *args, **kwargs)
            if os.path.normcase(os.path.abspath(os.fspath(path).removeprefix("\\\\?\\"))) == profile:
                values = {name: getattr(info, name) for name in dir(info) if name.startswith("st_")}
                values["st_nlink"] = 2
                return SimpleNamespace(**values)
            return info
        monkeypatch.setattr(router.runtime_resources.os, "lstat", observed_lstat)
    called = []
    monkeypatch.setattr(router.subprocess, "call", lambda *a, **kw: called.append(True))
    with pytest.raises(ValueError):
        invoke(candidate, **kwargs)
    assert not called


@pytest.mark.parametrize("change", ["overlay", "manifest_pin"])
def test_nested_hook_and_verify_reject_drift_in_the_same_binding(candidate, monkeypatch, change):
    root, stage, _, _, _ = candidate
    def compiler(command, cwd, env):
        if change == "overlay":
            path = Path(env["ARCHEAXIS_TAURI_CONFIG"])
            value = json.loads(path.read_text())
            value["bundle"]["resources"]["foreign"] = "core"
            write(path, value)
        else:
            env[router.RUNTIME_ENV[1]] = "0" * 64
        with monkeypatch.context() as nested:
            for name, value in env.items():
                nested.setenv(name, value)
            nested.setattr(router, "ROOT", root)
            nested.setattr(sys, "argv", ["frontend.py", "--node", "synthetic-node", "verify"])
            assert router.main() == 2
            nested.setattr(router.subprocess, "call", lambda *a, **kw: pytest.fail("must not compile"))
            with pytest.raises(ValueError):
                router.build(root, "synthetic-node", "build", [])
        return 19
    monkeypatch.setattr(router.subprocess, "call", compiler)
    assert invoke(candidate) == 19


@pytest.mark.parametrize("change", ["staged_member", "output_member", "manifest"])
def test_successful_compiler_cannot_qualify_changed_input_or_stale_output(candidate, monkeypatch, change):
    root, stage, _, _, _ = candidate
    def compiler(command, cwd, env):
        output = output_fixture(env, stage)
        if change == "manifest":
            (stage / "backend-runtime-manifest.json").write_bytes(b"{}")
        else:
            changed = stage if change == "staged_member" else output
            (changed / "workers/document/worker.py").write_bytes(b"changed worker")
        return 0
    monkeypatch.setattr(router.subprocess, "call", compiler)
    with pytest.raises(ValueError):
        invoke(candidate)
    receipt = next((root / ".project-local/runs").glob("*/*/artifacts/frontend-build.json"))
    result = json.loads(receipt.read_text())
    assert result["exit_code"] == 2 and result.get("status") != "PASS"
    assert "host_sha256" not in result
