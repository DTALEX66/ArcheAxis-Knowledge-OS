"""A staged runtime must declare exactly the routes it can actually serve.

Round 3 gave the Core an optional `routes` declaration; round 4 taught
`backend_launcher.load_profile` to read one. This pins the producing side: the
stager declares a capability only when its worker script is present in the staged
tree, so a candidate never advertises a route that will fail at job time, and never
advertises one whose script is absent (which the Core refuses outright).

The profile the stager writes must also load through the launcher's own reader, so
the two halves cannot drift apart.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from io import StringIO
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


stager = module("stage_backend_runtime_routes", ROOT / "scripts" / "release" / "stage_backend_runtime.py")
launcher = module("backend_launcher_stager_routes", ROOT / "scripts" / "release" / "backend_launcher.py")


def fixed_webview_fixture(tmp_path, monkeypatch):
    source = tmp_path / "official-webview2"
    source.mkdir()
    rows = []
    for name in ("msedgewebview2.exe", "msedge.dll", "locales/zh-CN.pak"):
        p = source / name
        p.parent.mkdir(exist_ok=True)
        p.write_bytes(("synthetic " + name).encode())
        rows.append({"path": name, "bytes": p.stat().st_size, "sha256": stager.sha256(p)})
    manifest = tmp_path / "fixed-manifest.json"
    manifest.write_text(json.dumps({"schema": "archeaxis.official-fixed-runtime-files/v1",
        "version": "synthetic", "architecture": "x64", "files": rows}), encoding="utf-8")
    monkeypatch.setattr(stager, "FIXED_WEBVIEW2", {"version": "synthetic", "architecture": "x64",
        "manifest_sha256": stager.sha256(manifest), "cab_sha256": "a" * 64})
    return source, manifest


@pytest.mark.parametrize("mutation", ["changed", "extra", "missing", "manifest", "hardlink"])
def test_fixed_webview2_rejects_unqualified_input_before_copy(tmp_path, monkeypatch, mutation):
    source, manifest = fixed_webview_fixture(tmp_path, monkeypatch)
    if mutation == "changed":
        (source / "msedge.dll").write_bytes(b"changed")
    elif mutation == "extra":
        (source / "extra.bin").write_bytes(b"extra")
    elif mutation == "missing":
        (source / "msedge.dll").unlink()
    elif mutation == "manifest":
        manifest.write_bytes(b"resealed but unapproved manifest")
    else:
        import os
        os.link(source / "msedge.dll", tmp_path / "outside-alias.dll")
    target = tmp_path / "new-runtime"
    (target / "runtime").mkdir(parents=True)
    with pytest.raises((ValueError, FileNotFoundError)):
        stager.stage_fixed_webview2(source, manifest, target)
    assert not (target / "runtime/webview2").exists()


def test_fixed_webview2_is_separate_exact_copy_and_cannot_overwrite(tmp_path, monkeypatch):
    source, manifest = fixed_webview_fixture(tmp_path, monkeypatch)
    target = tmp_path / "new-runtime"
    (target / "runtime").mkdir(parents=True)
    result = stager.stage_fixed_webview2(source, manifest, target)
    assert result["path"] == "runtime/webview2"
    assert result["files"] == 3
    assert (target / "runtime/webview2/aaos-fixed-runtime-manifest.json").read_bytes() == manifest.read_bytes()
    assert not (source / "aaos-fixed-runtime-manifest.json").exists()
    with pytest.raises(ValueError, match="overwrite"):
        stager.stage_fixed_webview2(source, manifest, target)


def synthetic_vc(runtime, monkeypatch):
    import hashlib
    identities = {}
    for name in stager.APP_LOCAL_VC_RUNTIME:
        payload = ("synthetic " + name).encode()
        (runtime / name).write_bytes(payload)
        identities[name] = ({"version": "synthetic", "bytes": len(payload),
                             "sha256": hashlib.sha256(payload).hexdigest()},)
    monkeypatch.setattr(stager, "APP_LOCAL_VC_RUNTIME", identities)
    cpp = {name: rows[0] for name, rows in identities.items()}
    payload = b"synthetic msvcp140.dll"
    (runtime / "msvcp140.dll").write_bytes(payload)
    cpp["msvcp140.dll"] = {"version": "synthetic", "bytes": len(payload),
                           "sha256": hashlib.sha256(payload).hexdigest()}
    monkeypatch.setattr(stager, "APP_LOCAL_CPP_COHORTS", (cpp,))


def test_no_worker_present_declares_no_routes(tmp_path):
    assert stager.present_routes(tmp_path) == []


def test_only_present_workers_are_declared(tmp_path):
    for name in ("worker_pdf.py", "worker_ocr.py"):
        target = tmp_path / "workers" / "document" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"stub")
    ocr = tmp_path / "workers" / "vision" / "worker_ocr.py"
    ocr.parent.mkdir(parents=True, exist_ok=True)
    ocr.write_bytes(b"stub")

    declared = {entry["capability"]: entry["script"] for entry in stager.present_routes(tmp_path)}
    assert declared == {
        "image.ocr": "workers/vision/worker_ocr.py",
        "pdf.extract": "workers/document/worker_pdf.py",
    }


def test_every_declared_script_resolves_to_a_real_file(tmp_path):
    for relative in {path for paths in stager.ROUTE_SCRIPTS.values() for path in paths}:
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"stub")
    for entry in stager.present_routes(tmp_path):
        assert (tmp_path / entry["script"]).is_file(), entry


def test_the_declared_script_is_the_preferred_one(tmp_path):
    """When several scripts could serve a capability, the first present one wins."""
    for capability, paths in stager.ROUTE_SCRIPTS.items():
        if len(paths) < 2:
            continue
        target = tmp_path / paths[1]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"stub")
        declared = {e["capability"]: e["script"] for e in stager.present_routes(tmp_path)}
        assert declared[capability] == paths[1]


def test_a_written_profile_loads_through_the_launcher(tmp_path):
    """The producer and the consumer must agree on the profile shape."""
    (tmp_path / "runtime").mkdir(parents=True)
    (tmp_path / "runtime" / "python.exe").write_bytes(b"stub")
    (tmp_path / "workers" / "transport").mkdir(parents=True)
    (tmp_path / "workers" / "transport" / "text_ndjson.py").write_bytes(b"stub")
    (tmp_path / "workers" / "document").mkdir(parents=True)
    (tmp_path / "workers" / "document" / "worker_pdf.py").write_bytes(b"stub")

    profile = {
        "schema": stager.PROFILE_SCHEMA,
        "python": "runtime/python.exe",
        "script": stager.TEXT_WORKER_RELATIVE,
        "staging": "data/worker-staging",
        "routes": stager.present_routes(tmp_path),
    }
    (tmp_path / "worker-profile.json").write_text(json.dumps(profile), encoding="utf-8")

    resolved = launcher.load_profile(tmp_path)
    assert resolved["routes"] == [
        {"capability": "pdf.extract", "script": (tmp_path / "workers" / "document" / "worker_pdf.py").resolve()}
    ]


def test_version_probe_cannot_add_unmanifested_bytecode(tmp_path, monkeypatch):
    """Reproduce the late version probe that invalidated the real Tauri build."""
    donor = tmp_path / "donor"
    (donor / "runtime").mkdir(parents=True)
    (donor / "runtime/python.exe").write_bytes(b"synthetic interpreter")
    synthetic_vc(donor / "runtime", monkeypatch)
    (donor / "workers/transport").mkdir(parents=True)
    (donor / "workers/transport/text_ndjson.py").write_text("# fixture", encoding="utf-8")
    (donor / "core.exe").write_bytes(b"synthetic Core")
    (donor / "scheduler.py").write_text("# fixture", encoding="utf-8")
    out = tmp_path / "中文 runtime & spaces"
    cache = out / "runtime/Lib/__pycache__/startup.pyc"

    def startup(writes_bytecode):
        if writes_bytecode:
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_bytes(b"startup side effect")

    def old_shell_probe(_command):
        startup(True)
        return StringIO("3.13.14\n")

    def version_probe(command, **kwargs):
        assert command[0] == str(out / "runtime/python.exe")
        assert "-I" in command and not kwargs.get("shell", False)
        assert kwargs["check"] and kwargs["timeout"] <= 30
        startup("-B" not in command)
        return subprocess.CompletedProcess(command, 0, "3.13.14\n", "")

    monkeypatch.setattr(stager, "packager_identity", lambda: "1" * 40)
    monkeypatch.setattr(stager, "stage_capability_manifest", lambda *_: {})
    monkeypatch.setattr(stager.os, "popen", old_shell_probe)
    monkeypatch.setattr(stager.subprocess, "run", version_probe)
    monkeypatch.setattr(sys, "argv", ["stage", "--core", str(donor / "core.exe"),
        "--runtime", str(donor / "runtime"), "--workers", str(donor / "workers"),
        "--shared", str(donor / "scheduler.py"), "--out", str(out), "--version", "fixture",
        "--source-commit", "1" * 40, "--source-tree", "2" * 40])
    assert stager.main() == 0
    manifest = json.loads((out / "backend-runtime-manifest.json").read_text(encoding="utf-8"))
    assert not cache.exists(), "version inspection must not mutate the packaged runtime"
    observed = {p.relative_to(out).as_posix() for p in out.rglob("*") if p.is_file()}
    assert observed == set(manifest["files"]) | {"backend-runtime-manifest.json"}
    assert manifest["components"][1]["version"] == "3.13.14"


@pytest.mark.parametrize("bad", ["missing", "changed", "directory"])
def test_app_local_donor_refusal_precedes_output(tmp_path, monkeypatch, bad):
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    synthetic_vc(runtime, monkeypatch)
    victim = runtime / "vcruntime140_1.dll"
    victim.unlink()
    if bad == "changed":
        victim.write_bytes(b"tampered")
    elif bad == "directory":
        victim.mkdir()
    root = tmp_path / "out"
    with pytest.raises(ValueError, match="app-local VC runtime"):
        stager.stage_app_local_vc_runtime(runtime, root)
    assert not root.exists()


def test_app_local_copy_identity_and_corruption_refusal(tmp_path, monkeypatch):
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    synthetic_vc(runtime, monkeypatch)
    root = tmp_path / "out"
    (root / "core").mkdir(parents=True)
    stager.stage_app_local_vc_runtime(runtime, root)
    for name in stager.APP_LOCAL_VC_RUNTIME:
        assert (root / name).read_bytes() == (root / "core" / name).read_bytes() == (runtime / name).read_bytes()
    with pytest.raises(ValueError, match="overwrite"):
        stager.stage_app_local_vc_runtime(runtime, root)
    broken = tmp_path / "broken"
    (broken / "core").mkdir(parents=True)
    copy = stager.shutil.copy2
    def corrupt(source, target):
        copy(source, target)
        Path(target).write_bytes(b"tampered copy")
    monkeypatch.setattr(stager.shutil, "copy2", corrupt)
    with pytest.raises(ValueError, match="copy mismatch"):
        stager.stage_app_local_vc_runtime(runtime, broken)


def test_app_local_link_refused_before_hash_or_copy(tmp_path, monkeypatch):
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    synthetic_vc(runtime, monkeypatch)
    original = stager.filesystem_path
    class Linked:
        def lstat(self):
            import stat
            from types import SimpleNamespace
            return SimpleNamespace(st_mode=stat.S_IFREG, st_file_attributes=0x400)
    monkeypatch.setattr(stager, "filesystem_path", lambda p: Linked() if Path(p).name == "vcruntime140.dll" else original(p))
    with pytest.raises(ValueError, match="linked staging path"):
        stager.validate_app_local_vc_runtime(runtime)
