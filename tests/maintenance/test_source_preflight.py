"""Tests for the pipeline source-root safety gate."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "pipeline" / "source_preflight.py"
SPEC = importlib.util.spec_from_file_location("source_preflight", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


def test_preflight_reports_metadata_without_opening_files(tmp_path: Path) -> None:
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(MODULE, "ROOT", tmp_path / "repo")
    source = MODULE.ROOT / ".project-local" / "fixture"
    (source / "nested").mkdir(parents=True)
    (source / "a.md").write_text("fixture", encoding="utf-8")
    (source / "nested" / "b").write_bytes(b"fixture")

    report = MODULE.preflight(source)

    assert report["status"] == "APPROVED_READ_ONLY_SOURCE"
    assert report["file_count"] == 2
    assert report["source_files_opened"] is False
    assert report["source_files_modified"] is False
    assert report["extensions"] == {"<none>": 1, ".md": 1}
    monkeypatch.undo()


def test_real_library_is_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    real = tmp_path / "real"
    (real / "nested").mkdir(parents=True)
    monkeypatch.setattr(MODULE, "REAL_LIBRARY", real)
    with pytest.raises(ValueError, match="real library"):
        MODULE.validate_source(real / "nested")


def test_unapproved_root_is_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(MODULE, "ROOT", tmp_path / "repo")
    with pytest.raises(ValueError, match="under approved"):
        MODULE.validate_source(tmp_path)


def test_shared_roots_are_derived_without_machine_absolute_literals() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    assert "D:/All projects" not in source
    assert MODULE.CESHI == MODULE.ROOT.parent / "ceshi"
    assert MODULE.REAL_LIBRARY == MODULE.ROOT.parent / "资料库"
    assert MODULE.GREEN_DATA == MODULE.ROOT.parent / "ArcheAxis.Knowledge.Green-x64" / "data"
