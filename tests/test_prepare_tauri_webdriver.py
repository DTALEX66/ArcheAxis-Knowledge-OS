"""Executable-bound tool preparation; tool/network calls are isolated test doubles."""

from __future__ import annotations

import hashlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import zipfile

import pytest


SCRIPT = Path(__file__).with_name("prepare_tauri_webdriver.py")
if not SCRIPT.is_file():
    SCRIPT = Path(__file__).resolve().parents[1] / "scripts/ci/prepare_tauri_webdriver.py"
SPEC = importlib.util.spec_from_file_location("prepare_tauri_webdriver_under_test", SCRIPT)
assert SPEC and SPEC.loader
prepare = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(prepare)


def pe_file(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    header = bytearray(64)
    header[:2] = b"MZ"
    header[60:64] = (64).to_bytes(4, "little")
    path.write_bytes(header + b"PE\x00\x00" + bytes(20))
    return path


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fake_tools(monkeypatch, runtime, *, version="156.0.4314.42", native_version=None, mutate=None):
    calls = []
    payload = io.BytesIO()
    with zipfile.ZipFile(payload, "w") as archive:
        archive.writestr("msedgedriver.exe", b"isolated-native-driver")

    def run(command, **kwargs):
        calls.append(command)
        if command[0] == "powershell.exe":
            assert "-NoProfile" in command and "Get-Item -LiteralPath" in command[-1]
            if mutate == "version":
                runtime.write_bytes(runtime.read_bytes() + b"changed")
            return subprocess.CompletedProcess(command, 0, stdout=version + "\n", stderr="")
        if command[1:3] == ["install", "tauri-driver"]:
            assert command[3:6] == ["--version", "2.1.0", "--locked"]
            install = Path(command[-1])
            binary = install / "bin/tauri-driver.exe"
            binary.parent.mkdir(parents=True)
            binary.write_bytes(b"isolated-tauri-driver")
            cargo = Path(kwargs["env"]["CARGO_HOME"])
            assert cargo.parent == install.parent
            assert Path(kwargs["env"]["CARGO_TARGET_DIR"]) == install.parent / "target"
            lock = cargo / "registry/src/test-official/tauri-driver-2.1.0/Cargo.lock"
            lock.parent.mkdir(parents=True)
            lock.write_text("locked-test-input\n")
            if mutate == "cargo":
                runtime.write_bytes(runtime.read_bytes() + b"changed")
            return subprocess.CompletedProcess(command, 0)
        assert command[0].endswith("msedgedriver.exe") and command[1:] == ["--version"]
        if mutate == "native":
            runtime.write_bytes(runtime.read_bytes() + b"changed")
        actual = native_version or version
        return subprocess.CompletedProcess(command, 0, stdout=f"Microsoft Edge WebDriver {actual} (test)\n", stderr="")

    def urlopen(url, **kwargs):
        calls.append(url)
        assert url == f"https://msedgedriver.microsoft.com/{version}/edgedriver_win64.zip"
        assert kwargs["timeout"] == 60
        return io.BytesIO(payload.getvalue())

    monkeypatch.setattr(prepare.subprocess, "run", run)
    monkeypatch.setattr(prepare.urllib.request, "urlopen", urlopen)
    return calls


def invoke(monkeypatch, root, runtime=None):
    argv = [str(SCRIPT), "--root", str(root), "--cargo", "test-cargo"]
    if runtime is not None:
        argv += ["--webview-executable", str(runtime)]
    monkeypatch.setattr(sys, "argv", argv)
    code = prepare.main()
    return code, json.loads((root / "receipt.json").read_text())


def test_explicit_packaged_runtime_uses_actual_version_and_binds_hash_without_system_env(tmp_path, monkeypatch):
    runtime = pe_file(tmp_path / "fixed-155-folder's/msedgewebview2.exe")
    monkeypatch.delenv("PROGRAMFILES(X86)", raising=False)
    calls = fake_tools(monkeypatch, runtime)
    code, receipt = invoke(monkeypatch, tmp_path / "tools", runtime)
    assert code == 0 and receipt["ok"] is True
    assert receipt["webview_selection"] == "explicit"
    assert receipt["webview_path"] == str(runtime.resolve())
    assert receipt["webview_sha256"] == sha(runtime)
    assert receipt["preparation_script_sha256"] == sha(SCRIPT)
    assert receipt["webview_version"] == "156.0.4314.42"
    assert receipt["edge_source"] == "https://msedgedriver.microsoft.com/156.0.4314.42/edgedriver_win64.zip"
    assert receipt["tauri_version"] == "2.1.0" and receipt["locked"] is True
    assert receipt["driver_sha256"] == sha(Path(receipt["driver"]))
    assert receipt["edge_sha256"] == sha(Path(receipt["native_driver"]))
    assert str(runtime).replace("'", "''") in calls[0][-1]
    assert not any(isinstance(call, list) and call[0] == str(runtime) for call in calls)


def test_default_ci_selection_uses_highest_system_runtime_and_same_receipt(tmp_path, monkeypatch):
    system = tmp_path / "Program Files (x86)"
    base = system / "Microsoft/EdgeWebView/Application"
    pe_file(base / "99.0.9999.99/msedgewebview2.exe")
    selected = pe_file(base / "155.0.4283.62/msedgewebview2.exe")
    pe_file(base / "999.0.0.invalid/msedgewebview2.exe")
    monkeypatch.setenv("PROGRAMFILES(X86)", str(system))
    fake_tools(monkeypatch, selected, version="155.0.4283.62")
    code, receipt = invoke(monkeypatch, tmp_path / "tools")
    assert code == 0 and receipt["ok"] is True
    assert receipt["webview_selection"] == "system"
    assert receipt["webview_path"] == str(selected.resolve())
    assert receipt["webview_version"] == "155.0.4283.62"
    assert receipt["webview_sha256"] == sha(selected)


@pytest.mark.parametrize("kind", ["missing", "directory", "wrong-name", "text", "relative", "unc", "bad-offset", "bad-signature"])
def test_invalid_explicit_path_fails_before_tool_build_or_network(tmp_path, monkeypatch, kind):
    runtime = tmp_path / "msedgewebview2.exe"
    if kind == "directory":
        runtime.mkdir()
    elif kind == "wrong-name":
        runtime = pe_file(tmp_path / "msedge.exe")
    elif kind == "text":
        runtime.write_text("not a PE")
    elif kind == "relative":
        runtime = Path("relative/msedgewebview2.exe")
    elif kind == "unc":
        runtime = Path("\\\\example.invalid\\share\\msedgewebview2.exe")
    elif kind in {"bad-offset", "bad-signature"}:
        pe_file(runtime)
        content = bytearray(runtime.read_bytes())
        if kind == "bad-offset":
            content[60:64] = (2**31).to_bytes(4, "little")
        else:
            content[64:68] = b"text"
        runtime.write_bytes(content)
    monkeypatch.setattr(prepare.subprocess, "run", lambda *a, **k: pytest.fail("unexpected process"))
    monkeypatch.setattr(prepare.urllib.request, "urlopen", lambda *a, **k: pytest.fail("unexpected network"))
    code, receipt = invoke(monkeypatch, tmp_path / "tools", runtime)
    assert code == 1 and receipt["ok"] is False and receipt["error"]
    assert not (tmp_path / "tools/cargo-install.log").exists()


@pytest.mark.parametrize("stage", ["version", "cargo", "native"])
def test_changed_runtime_never_produces_success_receipt(tmp_path, monkeypatch, stage):
    runtime = pe_file(tmp_path / "runtime/msedgewebview2.exe")
    fake_tools(monkeypatch, runtime, mutate=stage)
    code, receipt = invoke(monkeypatch, tmp_path / "tools", runtime)
    assert code == 1 and receipt["ok"] is False
    assert "WebView2 executable changed" in receipt["error"]


def test_missing_system_env_preserves_fail_closed_default(tmp_path, monkeypatch):
    monkeypatch.delenv("PROGRAMFILES(X86)", raising=False)
    code, receipt = invoke(monkeypatch, tmp_path / "tools")
    assert code == 1 and receipt["ok"] is False
    assert "PROGRAMFILES(X86)" in receipt["error"]


def test_invalid_actual_pe_version_does_not_download_or_install(tmp_path, monkeypatch):
    runtime = pe_file(tmp_path / "runtime/msedgewebview2.exe")
    calls = fake_tools(monkeypatch, runtime, version="")
    code, receipt = invoke(monkeypatch, tmp_path / "tools", runtime)
    assert code == 1 and "actual executable version missing" in receipt["error"]
    assert len(calls) == 1


def test_wrong_native_driver_version_is_a_failure(tmp_path, monkeypatch):
    runtime = pe_file(tmp_path / "runtime/msedgewebview2.exe")
    fake_tools(monkeypatch, runtime, native_version="155.0.4283.62")
    code, receipt = invoke(monkeypatch, tmp_path / "tools", runtime)
    assert code == 1 and receipt["ok"] is False
    assert "EdgeDriver executable version differs" in receipt["error"]
