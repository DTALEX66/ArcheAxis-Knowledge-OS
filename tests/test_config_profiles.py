from __future__ import annotations

from pathlib import Path

import pytest

from shared.config import Config

CONFIG_DIR = Path(__file__).resolve().parents[1] / "config"


@pytest.mark.parametrize("profile", ["desktop", "development", "test", "production"])
def test_supported_profiles_are_declared(profile: str) -> None:
    assert (CONFIG_DIR / "profiles" / f"{profile}.yaml").is_file()


def test_defaults_file_is_a_public_base_layer() -> None:
    assert (CONFIG_DIR / "defaults.yaml").is_file()
    assert "COGNITIVE_PROFILE" not in (CONFIG_DIR / "defaults.yaml").read_text(encoding="utf-8")
    pyproject = (CONFIG_DIR.parent / "pyproject.toml").read_text(encoding="utf-8")
    assert 'config = ["*.yaml", "profiles/*.yaml"]' in pyproject


def test_profile_overrides_legacy_settings_without_replacing_them() -> None:
    current = Config(profile="test")

    assert current.get("app.environment") == "test"
    assert current.get("database.path") == "data/test/cognitive_os.sqlite"
    assert current.get("pipeline.default_actions") == ["extract", "tag", "summarize", "index"]


def test_profile_can_be_selected_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COGNITIVE_PROFILE", "desktop")

    current = Config()

    assert current.get("app.environment") == "desktop"
    assert current.get("app.host") == "127.0.0.1"


def test_explicit_profile_takes_precedence_over_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COGNITIVE_PROFILE", "test")

    current = Config(profile="development")

    assert current.get("app.environment") == "development"
    assert current.get("database.path") == "data/cognitive_os.sqlite"


def test_unknown_profile_fails_closed() -> None:
    with pytest.raises(ValueError, match="unknown configuration profile"):
        Config(profile="staging")
