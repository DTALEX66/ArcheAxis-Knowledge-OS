"""Per-worktree size must mean bytes that worktree owns, not bytes it can reach.

`frontend/node_modules` is a link to one shared install that several worktrees point at. While the
walker followed links, every such worktree reported the same ~190 MB as its own, so the report's
central question - which bytes are duplicated and which are shared once - could not be answered
from it. The junction here is created for real, because the defect only exists for real reparse
points: `Path.is_symlink()` says False and `is_dir(follow_symlinks=False)` says True for one.
"""
from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "storage_report_under_test", ROOT / "scripts" / "runtime" / "storage_report.py")
assert SPEC and SPEC.loader
report = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = report
SPEC.loader.exec_module(report)


def make_junction(link: Path, target: Path) -> None:
    if os.name != "nt":
        pytest.skip("junctions are a Windows reparse-point concept")
    result = subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(target)],
                            capture_output=True, text=True)
    if result.returncode != 0:
        pytest.skip(f"could not create a junction here: {result.stdout.strip()[-160:]}")


@pytest.fixture()
def tree(tmp_path: Path) -> Path:
    shared = tmp_path / "shared-install"
    shared.mkdir()
    (shared / "big.js").write_bytes(b"x" * 5000)
    worktree = tmp_path / "worktree"
    frontend = worktree / "frontend"
    frontend.mkdir(parents=True)
    (frontend / "app.ts").write_bytes(b"y" * 1000)
    make_junction(frontend / "node_modules", shared)
    return worktree


def test_a_linked_directory_is_not_counted_as_owned_bytes(tree: Path) -> None:
    assert report.directory_size(tree) == 1000, "the shared install was counted into the worktree"
    assert report.directory_size(tree / "frontend" / "node_modules") == 0


def test_ordinary_directories_are_still_walked(tmp_path: Path) -> None:
    """The companion assertion that keeps the previous test from passing by measuring nothing."""
    nested = tmp_path / "a" / "b"
    nested.mkdir(parents=True)
    (nested / "file").write_bytes(b"z" * 4096)
    (tmp_path / "sibling").write_bytes(b"w" * 64)
    assert report.directory_size(tmp_path) == 4096 + 64


def test_links_are_reported_with_their_target_so_shared_bytes_have_one_owner(tree: Path) -> None:
    links = report.links_under(tree)
    assert len(links) == 1, links
    assert links[0]["link"].endswith("node_modules")
    assert (Path(links[0]["link"]) / "big.js").read_bytes() == b"x" * 5000, "target is wrong"


def test_is_link_distinguishes_a_junction_from_a_real_directory(tree: Path, tmp_path: Path) -> None:
    entries = {Path(entry.path).name: entry
               for entry in os.scandir(tree / "frontend")}
    assert report.is_link(entries["node_modules"]) is True
    assert report.is_link(entries["app.ts"]) is False
    plain = tmp_path / "plain-dir"
    plain.mkdir()
    with os.scandir(tmp_path) as scanned:
        found = {entry.name: entry for entry in scanned}
    assert report.is_link(found["plain-dir"]) is False
