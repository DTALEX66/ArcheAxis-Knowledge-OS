"""AXW-RUN-202 — Runtime Profile v1 (Python side) tests.

Proves the four profile YAMLs parse and validate, unknown profiles fail
closed, and ARCHEAXIS_RUNTIME_PROFILE drives the runtime mode.
"""

from __future__ import annotations

import pytest

from shared import runtime_profile
from shared.runtime_profile import (
    DEFAULT_RUNTIME_MODE,
    load_profile,
    resolve_runtime_mode,
)

EXPECTED = {
    "installed-stable": {
        "backend": "bundled",
        "data_policy": "installed-user-data",
        "reload": False,
    },
    "green-stable": {
        "backend": "bundled",
        "data_policy": "selected-user-data",
        "reload": True,
    },
    "portable-stable": {
        "backend": "bundled",
        "data_policy": "portable-root-only",
        "reload": False,
    },
    "external-dev": {
        "backend": "external-source",
        "data_policy": "isolated-test-workspace",
        "reload": True,
    },
}


def test_all_four_profiles_parse_and_validate() -> None:
    for name, expected in EXPECTED.items():
        profile = load_profile(name)
        assert profile.name == name
        assert profile.backend == expected["backend"]
        assert profile.data_policy == expected["data_policy"]
        assert profile.reload is expected["reload"]


def test_external_dev_carries_local_source_root_example() -> None:
    profile = load_profile("external-dev")
    assert profile.source_root is not None
    assert profile.source_root.startswith("D:/All projects/")


def test_unknown_profile_fails_closed() -> None:
    with pytest.raises(ValueError, match="unknown runtime profile"):
        load_profile("not-a-profile")


def test_missing_profile_file_fails_closed(tmp_path: object, monkeypatch: pytest.MonkeyPatch) -> None:
    """A supported name with no backing file must also fail closed."""
    monkeypatch.setattr(runtime_profile, "_PROFILES_DIR", tmp_path)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="profile file not found"):
        load_profile("installed-stable")


def test_resolve_runtime_mode_defaults_to_installed_stable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ARCHEAXIS_RUNTIME_PROFILE", raising=False)
    assert DEFAULT_RUNTIME_MODE == "installed-stable"
    assert resolve_runtime_mode() == "installed-stable"


def test_resolve_runtime_mode_env_driven(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in EXPECTED:
        monkeypatch.setenv("ARCHEAXIS_RUNTIME_PROFILE", name)
        assert resolve_runtime_mode() == name


def test_resolve_runtime_mode_invalid_value_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ARCHEAXIS_RUNTIME_PROFILE", "bogus-mode")
    with pytest.raises(ValueError, match="ARCHEAXIS_RUNTIME_PROFILE"):
        resolve_runtime_mode()
