from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("resource_boundaries", ROOT / "scripts/maintenance/check_resource_boundaries.py")
assert SPEC and SPEC.loader
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


def _checkout(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    (root / ".git").mkdir(parents=True)
    for name in module.RESOURCE_NAMES.values():
        (tmp_path / name).mkdir()
    return root


def test_indexed_roots_and_purpose_targets_are_fixed(tmp_path: Path):
    report = module.check_resource_boundaries(_checkout(tmp_path), purpose="integration")
    assert report["target"]["id"] == "green_application"
    assert {row["id"] for row in report["resources"]} == set(module.RESOURCE_NAMES)
    assert all(not row["reparse"] for row in report["resources"])
    assert module.check_resource_boundaries(tmp_path / "project", purpose="test")["target"]["id"] == "project_test_corpus"


def test_missing_root_fails_closed(tmp_path: Path):
    root = _checkout(tmp_path)
    (tmp_path / "ceshi").rmdir()
    with pytest.raises(ValueError, match="project_test_corpus"):
        module.check_resource_boundaries(root, purpose="test")


def test_index_drift_fails_closed(tmp_path: Path):
    root = _checkout(tmp_path)
    index = root / module.INDEX_PATH
    index.parent.mkdir(parents=True)
    index.write_text("`project_test_corpus` D:/All projects/wrong-root\n", encoding="utf-8")
    with pytest.raises(ValueError, match="resource index drift"):
        module.check_resource_boundaries(root, purpose="test")
