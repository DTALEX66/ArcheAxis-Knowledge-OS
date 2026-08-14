"""AXW-DATA-403 acceptance: long-path (>260) workspace operations on Windows.

Task pack §19 #15: 旧数据库升级、回滚和长路径验证通过.

Windows reality (validated 2026-08-15 on this host): plain paths >260 chars
fail at os.mkdir with WinError 3 unless the registry LongPathsEnabled flag
is on. NTFS itself supports long paths via the ``\\\\?\\`` extended prefix.
These tests exercise the deterministic form: ``\\\\?\\``-prefixed absolute
paths for workspace creation and migration round-trip. The plain-path
requirement is documented (docs/design/AXW-DATA-403-migration.md): products
that must support >260-char paths ship longPathAware manifests and document
the registry flag; anything else fails closed (no truncation).
"""
from __future__ import annotations

import os
import platform
import sqlite3
from pathlib import Path

import pytest

from app.workspace.migrate import backup, dry_run, migrate, rollback_readback
from shared.workspace_manifest import create_workspace

pytestmark = pytest.mark.skipif(
    platform.system() != "Windows",
    reason="long-path semantics are Windows-specific (NTFS + \\\\?\\ handling)",
)


def _unc_long_path(base: Path, leaf: str = "ws") -> str:
    """\\\\?\\-prefixed absolute path whose length exceeds 260 chars."""
    segment = "segment-" + "x" * 40
    parts = [str(base)] + [segment] * 6 + [leaf]
    plain = "\\".join(parts)
    assert len(plain) > 260, f"path too short: {len(plain)}"
    return "\\\\?\\" + plain


def test_workspace_create_on_unc_long_path(tmp_path: Path) -> None:
    parent = _unc_long_path(tmp_path)
    created = create_workspace(parent, "long-path-ws")
    assert created is not None
    # os.path keeps the \\?\ prefix (pathlib normalizes it to //?/ which is
    # not a valid filesystem path form for stat).
    assert os.path.exists(os.path.join(parent, "long-path-ws", "manifest.json"))


def test_migration_roundtrip_on_unc_long_path(tmp_path: Path) -> None:
    parent = _unc_long_path(tmp_path)
    src = os.path.join(parent, "legacy.sqlite")
    os.makedirs(os.path.dirname(src), exist_ok=True)
    con = sqlite3.connect(src)
    con.execute("CREATE TABLE documents (id INTEGER PRIMARY KEY, content TEXT)")
    con.execute("INSERT INTO documents (content) VALUES ('long-path payload')")
    con.commit()
    con.close()

    ws_dir = os.path.join(parent, "workspace")
    create_workspace(ws_dir, "ws")
    backups = Path(os.path.join(ws_dir, "ws", "backups"))

    backup_result = backup(src, backups)
    backup_path = Path(backup_result["backup_path"])
    assert os.path.exists(str(backup_path))
    plan = dry_run(src, os.path.join(ws_dir, "ws"))
    assert plan is not None and len(plan) > 0

    result = migrate(src, os.path.join(ws_dir, "ws"))
    assert result.get("status") == "ok"
    assert result.get("already_migrated") in (True, False)

    rb = rollback_readback(backup_path)
    assert rb.get("status") == "ok"
    assert rb.get("integrity") == "ok"
    assert os.path.exists(src), "legacy DB must be kept after migration"
