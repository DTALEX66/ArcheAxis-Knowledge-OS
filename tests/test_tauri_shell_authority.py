"""The recovery shell must never collide with the canonical product installer."""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_recovery_shell_has_distinct_identity_and_no_release_bundle():
    primary = json.loads((ROOT / "src-tauri/tauri.conf.json").read_text(encoding="utf-8"))
    recovery = json.loads(
        (ROOT / "desktop/src-tauri/tauri.conf.json").read_text(encoding="utf-8")
    )

    assert primary["productName"] == "ArcheAxis Knowledge"
    assert primary["identifier"] == "com.archeaxis.workspace"
    assert primary["bundle"]["active"] is True
    assert recovery["productName"] == "ArcheAxis Knowledge Recovery"
    assert recovery["identifier"] == "com.archeaxis.workspace.recovery"
    assert recovery["bundle"]["active"] is False
    assert primary["identifier"] != recovery["identifier"]


def load_probe(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "scripts/probes"))
    spec = importlib.util.spec_from_file_location("native_probe_test", ROOT / "scripts/probes/aaos01_tauri_webdriver_loop.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_native_observer_excludes_recycled_parent_pid_and_unrelated_processes(monkeypatch):
    probe = load_probe(monkeypatch)
    rows = [
        {"pid": 1, "parent_pid": 0, "created": 100},
        {"pid": 2, "parent_pid": 1, "created": 110},
        {"pid": 3, "parent_pid": 2, "created": 120},
        {"pid": 4, "parent_pid": 2, "created": 105},
        {"pid": 5, "parent_pid": 99, "created": 130},
    ]
    assert [row["pid"] for row in probe.owned_process_rows(rows, 1)] == [1, 2, 3]
    with pytest.raises(RuntimeError, match="identity unavailable"):
        probe.owned_process_rows(rows, 99)


def test_native_profile_observer_does_not_read_profile_contents(monkeypatch, tmp_path):
    probe = load_probe(monkeypatch)
    profile = tmp_path / "profile"
    (profile / "EBWebView").mkdir(parents=True)
    (profile / "DevToolsActivePort").write_bytes(b"not read")
    monkeypatch.setattr(Path, "read_bytes", lambda _path: pytest.fail("Profile content read"))
    monkeypatch.setattr(Path, "read_text", lambda _path, **_kwargs: pytest.fail("Profile content read"))
    assert probe.profile_metadata([profile])[0] == {
        "path": str(profile), "exists": True, "ebwebview_exists": True,
        "devtools_active_port_exists": True, "ebwebview_devtools_active_port_exists": False,
    }


@pytest.mark.skipif(os.name != "nt", reason="Win32 process metadata API")
def test_native_process_observer_reads_current_owned_identity(monkeypatch):
    probe = load_probe(monkeypatch)
    rows = probe.native_process_rows()
    owned = probe.owned_process_rows(rows, os.getpid())
    assert any(row["pid"] == os.getpid() and row["created"] > 0 for row in owned)
    assert all(set(row) == {"pid", "parent_pid", "name", "created"} for row in owned)
    elevation = probe.process_elevation(os.getpid())
    assert elevation["elevation_verified"] is True
    assert isinstance(elevation["elevated"], bool)
