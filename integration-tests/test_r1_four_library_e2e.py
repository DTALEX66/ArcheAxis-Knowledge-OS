"""R1 E2E: four-library first-run initialization + restart readback."""
from __future__ import annotations

from pathlib import Path

import pytest

from shared.workspace_manifest import ASSET_DOMAINS, create_workspace, load


@pytest.fixture()
def workspace_root(tmp_path):
    root = tmp_path / "workspaces"
    root.mkdir()
    return root


def test_r1_four_library_initialize_and_restart_readback(workspace_root: Path):
    manifest = create_workspace(workspace_root, name="星环知识平台测试工作区")

    # four asset domains created on disk (canonical order)
    assert set(manifest.domains) == set(ASSET_DOMAINS)
    for domain in manifest.domains.values():
        assert Path(domain.path).is_dir()

    # restart readback: fresh load from persisted manifest.json
    manifest_path = workspace_root / "星环知识平台测试工作区" / "manifest.json"
    assert manifest_path.is_file()
    reloaded = load(manifest_path)
    assert reloaded.workspace_id == manifest.workspace_id
    assert set(reloaded.domains) == set(ASSET_DOMAINS)
    assert reloaded.domains["source_archive"].path == manifest.domains["source_archive"].path
    # derived/logs/backups persisted
    assert reloaded.derived_cache_path == manifest.derived_cache_path
    assert reloaded.backup is not None and reloaded.backup.location == manifest.backup.location
