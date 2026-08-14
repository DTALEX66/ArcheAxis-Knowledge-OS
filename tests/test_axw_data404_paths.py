"""AXW-DATA-404 four-form path policy tests.

Proves the four deployment forms resolve the expected roots, portable mode
refuses to run without ARCHEAXIS_PORTABLE_ROOT and never leaks the user's
LOCALAPPDATA, installed mode marks the program directory read-only, and
path resolution is fail-closed against traversal escapes.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from shared.path_policy import PathPolicyError, resolve_paths


def test_installed_stable_uses_localappdata(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "LocalAppData"))
    policy = resolve_paths("installed-stable")
    assert policy.mode == "installed-stable"
    assert policy.data_root == tmp_path / "LocalAppData" / "ArcheAxis" / "Workspace"
    assert policy.program_readonly is True
    assert policy.allowed_roots == (policy.data_root,)
    # program dir is the executable's directory
    assert policy.program_dir == Path(sys.executable).resolve().parent


def test_installed_stable_requires_localappdata(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LOCALAPPDATA", raising=False)
    monkeypatch.delenv("LOCAL_APP_DATA", raising=False)
    with pytest.raises(PathPolicyError, match="LOCALAPPDATA"):
        resolve_paths("installed-stable")


def test_green_stable_defaults_to_localappdata(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "LocalAppData"))
    monkeypatch.delenv("ARCHEAXIS_DATA_DIR", raising=False)
    monkeypatch.delenv("COGNITIVE_DATA_DIR", raising=False)
    policy = resolve_paths("green-stable")
    assert policy.data_root == tmp_path / "LocalAppData" / "ArcheAxis" / "Workspace"
    assert policy.program_readonly is True


def test_green_stable_honors_data_dir_override(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "LocalAppData"))
    monkeypatch.setenv("ARCHEAXIS_DATA_DIR", str(tmp_path / "custom-data"))
    policy = resolve_paths("green-stable")
    assert policy.data_root == tmp_path / "custom-data"


def test_portable_stable_requires_portable_root(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ARCHEAXIS_PORTABLE_ROOT", raising=False)
    monkeypatch.setenv("LOCALAPPDATA", "C:/Users/someone/AppData/Local")
    with pytest.raises(PathPolicyError, match="ARCHEAXIS_PORTABLE_ROOT"):
        resolve_paths("portable-stable")


def test_portable_stable_never_leaks_user_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Portable resolution must not fall back to LOCALAPPDATA even when the
    user directory exists and looks like a valid target."""
    local_app_data = tmp_path / "LocalAppData"
    local_app_data.mkdir(parents=True)
    monkeypatch.setenv("LOCALAPPDATA", str(local_app_data))
    monkeypatch.setenv("ARCHEAXIS_PORTABLE_ROOT", str(tmp_path / "portable"))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "Users" / "someone"))

    policy = resolve_paths("portable-stable")
    assert policy.data_root == (tmp_path / "portable" / "data")
    assert policy.program_readonly is False
    # no allowed root may sit inside the user's LOCALAPPDATA
    local_app_data_resolved = local_app_data.resolve()
    for root in policy.allowed_roots:
        assert not root.resolve().is_relative_to(local_app_data_resolved)
    assert str(local_app_data_resolved).casefold() not in str(policy.data_root).casefold()


def test_portable_resolve_data_stays_inside_portable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ARCHEAXIS_PORTABLE_ROOT", str(tmp_path / "portable"))
    policy = resolve_paths("portable-stable")
    resolved = policy.resolve_data("vault/notes.md")
    assert resolved == (tmp_path / "portable" / "data" / "vault" / "notes.md")
    assert policy.is_within_data(resolved)

    # traversal escapes are refused, not silently redirected
    with pytest.raises(PathPolicyError, match="escapes data root"):
        policy.resolve_data("../../outside.txt")
    with pytest.raises(PathPolicyError, match="absolute"):
        policy.resolve_data(str(tmp_path / "portable" / "data" / "abs.txt"))


def test_external_dev_requires_test_workspace_root(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ARCHEAXIS_TEST_WORKSPACE_ROOT", raising=False)
    with pytest.raises(PathPolicyError, match="ARCHEAXIS_TEST_WORKSPACE_ROOT"):
        resolve_paths("external-dev")


def test_external_dev_confines_to_test_workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ARCHEAXIS_TEST_WORKSPACE_ROOT", str(tmp_path / "test-ws"))
    policy = resolve_paths("external-dev")
    assert policy.data_root == (tmp_path / "test-ws")
    assert policy.program_readonly is False
    resolved = policy.resolve_data("fixtures/raw.txt")
    assert resolved == (tmp_path / "test-ws" / "fixtures" / "raw.txt")
    with pytest.raises(PathPolicyError):
        policy.resolve_data("../escape.txt")


def test_unknown_mode_rejected() -> None:
    with pytest.raises(PathPolicyError, match="unknown deployment mode"):
        resolve_paths("mystery-stable")  # type: ignore[arg-type]
