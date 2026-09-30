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
    _write_index(root, tmp_path)
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
    index.parent.mkdir(parents=True, exist_ok=True)
    index.write_text("`project_test_corpus` D:/All projects/wrong-root\n", encoding="utf-8")
    with pytest.raises(ValueError, match="resource index drift"):
        module.check_resource_boundaries(root, purpose="test")


def test_e_drive_project_root_is_rejected():
    with pytest.raises(ValueError, match="outside E:"):
        module.check_resource_boundaries(Path("E:/ArcheAxis-Knowledge-OS"), purpose="test")


def test_f_drive_is_rejected_without_metadata_access():
    with pytest.raises(ValueError, match="outside E:/F:"):
        module.check_resource_boundaries(Path("F:/ArcheAxis-Knowledge-OS"), purpose="test")


def _write_index(root: Path, shared_root: Path) -> Path:
    index = root / module.INDEX_PATH
    index.parent.mkdir(parents=True, exist_ok=True)
    index.write_text("\n".join(
        f"| `{key}` | `{shared_root / name}` | fixture |"
        for key, name in module.RESOURCE_NAMES.items()
    ), encoding="utf-8")
    return index


def test_nested_checkout_uses_registered_absolute_roots(tmp_path: Path):
    _checkout(tmp_path)
    nested = tmp_path / "task-trees" / "verification"
    (nested / ".git").mkdir(parents=True)
    _write_index(nested, tmp_path)
    report = module.check_resource_boundaries(nested, purpose="integration")
    assert report["target"]["canonical_path"] == str(tmp_path / "ArcheAxis.Knowledge.Green-x64")


@pytest.mark.parametrize("replacement", ["E:/Model library", "F:/Model library", "relative/Model library"])
def test_registered_root_rejected_before_resource_metadata(tmp_path: Path, monkeypatch, replacement: str):
    root = _checkout(tmp_path)
    index = _write_index(root, tmp_path)
    index.write_text(index.read_text(encoding="utf-8").replace(str(tmp_path / "Model library"), replacement), encoding="utf-8")
    original = module._is_reparse
    monkeypatch.setattr(module, "_is_reparse", lambda path: original(path) if path in {index, root / ".git"} else pytest.fail("resource metadata must not be accessed"))
    with pytest.raises(ValueError, match="resource index"):
        module.check_resource_boundaries(root)


def test_duplicate_resource_registration_fails_closed(tmp_path: Path):
    root = _checkout(tmp_path)
    index = _write_index(root, tmp_path)
    index.write_text(index.read_text(encoding="utf-8") + f"\n| `shared_models` | `{tmp_path / 'Model library'}` | duplicate |", encoding="utf-8")
    with pytest.raises(ValueError, match="resource index"):
        module.check_resource_boundaries(root)


def test_resource_ancestor_reparse_fails_closed(tmp_path: Path, monkeypatch):
    root = _checkout(tmp_path)
    _write_index(root, tmp_path)
    original = module._is_reparse
    monkeypatch.setattr(module, "_is_reparse", lambda path: path == tmp_path or original(path))
    with pytest.raises(ValueError, match="reparse ancestor"):
        module.check_resource_boundaries(root)


def test_registered_paths_with_different_parents_fail_closed(tmp_path: Path):
    root = _checkout(tmp_path)
    index = _write_index(root, tmp_path)
    index.write_text(index.read_text(encoding="utf-8").replace(str(tmp_path / "Model library"), str(tmp_path / "other" / "Model library")), encoding="utf-8")
    with pytest.raises(ValueError, match="registered parent"):
        module.check_resource_boundaries(root)


def test_missing_index_fails_closed_in_any_checkout(tmp_path: Path):
    root = _checkout(tmp_path)
    (root / module.INDEX_PATH).unlink()
    with pytest.raises(ValueError, match="resource index is missing"):
        module.check_resource_boundaries(root)


def test_relative_checkout_in_protected_cwd_rejected_before_metadata(monkeypatch):
    monkeypatch.setattr(module.os.path, "abspath", lambda path: "F:/project")
    with pytest.raises(ValueError, match="outside E:/F:"):
        module.check_resource_boundaries(Path("."))


def test_report_output_reparse_ancestor_rejected(tmp_path: Path, monkeypatch):
    root = _checkout(tmp_path)
    local = root / ".project-local"
    local.mkdir()
    original = module._is_reparse
    monkeypatch.setattr(module, "_is_reparse", lambda path: path == local or original(path))
    with pytest.raises(ValueError, match="reparse ancestor"):
        module._write_report(root, local / "report.json", {})
    assert not (local / "report.json").exists()


def test_report_output_written_only_inside_project_local(tmp_path: Path):
    root = _checkout(tmp_path)
    output = root / ".project-local" / "nested" / "report.json"
    module._write_report(root, output, {"test": True})
    assert '"test": true' in output.read_text(encoding="utf-8")
    with pytest.raises(ValueError):
        module._write_report(root, tmp_path / "outside.json", {})


def test_git_marker_reparse_rejected(tmp_path: Path, monkeypatch):
    root = _checkout(tmp_path)
    original = module._is_reparse
    monkeypatch.setattr(module, "_is_reparse", lambda path: path == root / ".git" or original(path))
    with pytest.raises(ValueError, match="Git marker is a reparse"):
        module.check_resource_boundaries(root)


def test_final_index_reparse_rejected_before_read(tmp_path: Path, monkeypatch):
    root = _checkout(tmp_path)
    index = root / module.INDEX_PATH
    original = module._is_reparse
    monkeypatch.setattr(module, "_is_reparse", lambda path: path == index or original(path))
    with pytest.raises(ValueError, match="resource index is a reparse"):
        module.check_resource_boundaries(root)


def test_final_report_reparse_rejected_without_overwrite(tmp_path: Path, monkeypatch):
    root = _checkout(tmp_path)
    output = root / ".project-local" / "report.json"
    output.parent.mkdir()
    output.write_text("preserve", encoding="utf-8")
    original = module._is_reparse
    monkeypatch.setattr(module, "_is_reparse", lambda path: path == output or original(path))
    with pytest.raises(ValueError, match="reparse ancestor"):
        module._write_report(root, output, {})
    assert output.read_text(encoding="utf-8") == "preserve"
