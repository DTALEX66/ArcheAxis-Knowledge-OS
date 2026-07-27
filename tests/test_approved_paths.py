from __future__ import annotations

import os
import subprocess
from dataclasses import replace

import pytest

from shared.approved_paths import ApprovedRoots, ApprovedRootsError
from shared.obsidian_projection import render_taskpack, write_projection


def test_requires_explicit_source_and_output_roots(tmp_path):
    (tmp_path / "source").mkdir()
    (tmp_path / "output").mkdir()
    with pytest.raises(ApprovedRootsError):
        ApprovedRoots()

    roots = ApprovedRoots(source_roots=[tmp_path / "source"], output_roots=[tmp_path / "output"])
    assert roots.resolve_source(tmp_path / "source") == (tmp_path / "source").resolve()


def test_rejects_source_traversal_and_output_outside(tmp_path):
    source = tmp_path / "source"
    output = tmp_path / "output"
    source.mkdir()
    output.mkdir()
    roots = ApprovedRoots(source_roots=[source], output_roots=[output])

    with pytest.raises(ApprovedRootsError):
        roots.resolve_source(source / ".." / "outside.txt")
    with pytest.raises(ApprovedRootsError):
        roots.resolve_output(tmp_path / "outside.txt")


def test_rejects_symlink_escape_for_source_and_output(tmp_path):
    source = tmp_path / "source"
    output = tmp_path / "output"
    outside = tmp_path / "outside"
    source.mkdir()
    output.mkdir()
    outside.mkdir()
    (outside / "secret.txt").write_text("secret", encoding="utf-8")

    link = source / "link"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"directory symlink unavailable: {exc}")

    roots = ApprovedRoots(source_roots=[source], output_roots=[output])
    with pytest.raises(ApprovedRootsError):
        roots.resolve_source(link / "secret.txt")
    with pytest.raises(ApprovedRootsError):
        roots.resolve_output(link / "new.txt")


def test_rejects_windows_junction_escape_when_supported(tmp_path):
    if os.name != "nt":
        pytest.skip("junction evidence is Windows-specific")
    source = tmp_path / "source"
    outside = tmp_path / "outside"
    source.mkdir()
    outside.mkdir()
    (tmp_path / "output").mkdir()
    junction = source / "junction"
    completed = subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(junction), str(outside)],
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        pytest.skip("junction unavailable")

    roots = ApprovedRoots(source_roots=[source], output_roots=[tmp_path / "output"])
    with pytest.raises(ApprovedRootsError):
        roots.resolve_source(junction / "escape.txt")


def test_projection_requires_approved_vault_for_real_writes(tmp_path):
    projection = render_taskpack({"id": "task-1", "goal": "safe"})
    projection = replace(projection, write_policy="apply")

    assert write_projection(projection, dry_run=False)["status"] == "blocked"

    vault = tmp_path / "vault"
    vault.mkdir()
    projection = replace(projection, path="../escape.md")
    result = write_projection(projection, vault_root=str(vault), dry_run=False)
    assert result["status"] == "blocked"
    assert not (tmp_path / "escape.md").exists()
