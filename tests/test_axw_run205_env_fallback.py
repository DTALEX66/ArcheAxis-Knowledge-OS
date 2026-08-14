"""AXW-RUN-205 — canonical environment variable fallback tests.

Proves resolve_runtime_path prefers canonical ARCHEAXIS_DATA_DIR, falls
back to legacy COGNITIVE_DATA_DIR (with a one-time stderr hint guarded
by an env sentinel), and uses the project-root default when both are
unset.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from shared.config import _LEGACY_MIGRATION_HINT_SENTINEL, resolve_runtime_path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_archeaxis_wins_over_cognitive(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ARCHEAXIS_DATA_DIR", "C:/canonical/data")
    monkeypatch.setenv("COGNITIVE_DATA_DIR", "C:/legacy/data")
    monkeypatch.delenv(_LEGACY_MIGRATION_HINT_SENTINEL, raising=False)
    resolved = resolve_runtime_path("data/x")
    assert resolved == Path("C:/canonical/data") / "x"


def test_cognitive_fallback_when_archeaxis_unset(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv("ARCHEAXIS_DATA_DIR", raising=False)
    monkeypatch.setenv("COGNITIVE_DATA_DIR", "C:/legacy/data")
    monkeypatch.delenv(_LEGACY_MIGRATION_HINT_SENTINEL, raising=False)
    resolved = resolve_runtime_path("data/x")
    assert resolved == Path("C:/legacy/data") / "x"
    err = capsys.readouterr().err
    assert "[migration]" in err
    assert "COGNITIVE_DATA_DIR" in err
    assert "ARCHEAXIS_DATA_DIR" in err


def test_migration_hint_printed_only_once(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv("ARCHEAXIS_DATA_DIR", raising=False)
    monkeypatch.setenv("COGNITIVE_DATA_DIR", "C:/legacy/data")
    monkeypatch.delenv(_LEGACY_MIGRATION_HINT_SENTINEL, raising=False)
    resolve_runtime_path("data/a")
    resolve_runtime_path("data/b")
    resolve_runtime_path("config/c")
    err = capsys.readouterr().err
    assert err.count("[migration]") == 1


def test_hint_re_arms_when_sentinel_unset(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv("ARCHEAXIS_DATA_DIR", raising=False)
    monkeypatch.setenv("COGNITIVE_DATA_DIR", "C:/legacy/data")
    monkeypatch.delenv(_LEGACY_MIGRATION_HINT_SENTINEL, raising=False)
    resolve_runtime_path("data/a")
    assert capsys.readouterr().err.count("[migration]") == 1
    # Sentinel unset -> the next fallback may hint again (fresh process
    # semantics); sentinel set -> silence.
    monkeypatch.setenv(_LEGACY_MIGRATION_HINT_SENTINEL, "1")
    resolve_runtime_path("data/b")
    assert capsys.readouterr().err.count("[migration]") == 0


def test_project_root_default_when_both_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ARCHEAXIS_DATA_DIR", raising=False)
    monkeypatch.delenv("COGNITIVE_DATA_DIR", raising=False)
    monkeypatch.delenv(_LEGACY_MIGRATION_HINT_SENTINEL, raising=False)
    resolved = resolve_runtime_path("data/x")
    assert resolved == _PROJECT_ROOT / "data" / "x"
