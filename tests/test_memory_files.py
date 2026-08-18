"""Tests for memory-as-files export/import (ReMe absorption)."""
from __future__ import annotations

import pytest

from app.memory.memory_layers import MemoryLayer, recall, store
from app.memory.memory_files import MemoryFilesError, export_markdown, import_markdown


def test_export_import_roundtrip(tmp_path):
    db = tmp_path / "mem.sqlite"
    store(db, content="Photoshop 蒙版是非破坏性编辑", layer=MemoryLayer.L3_PROFESSIONAL)
    store(db, content="我习惯上午做设计", layer=MemoryLayer.L4_PERSONA, tags=["persona"])

    out = tmp_path / "out"
    counts = export_markdown(db, out)
    assert counts["L3_professional"] == 1
    assert counts["L4_persona"] == 1
    assert (out / "L4_persona.md").exists()

    # edit the exported file (simulate human edit): append a new entry
    f = out / "L3_professional.md"
    with f.open("a", encoding="utf-8") as fh:
        fh.write("## [2026-08-18T00:00:00+00:00] L3_professional | tags: manual | importance: 0.5\n人工补充的知识条目\n---\n")

    db2 = tmp_path / "mem2.sqlite"
    imported = import_markdown(db2, out)
    assert imported["L3_professional"] == 2
    hits = recall(db2, query="人工补充", layers=[MemoryLayer.L3_PROFESSIONAL])
    assert hits and "人工补充" in hits[0]["content"]


def test_export_creates_principles_file(tmp_path):
    db = tmp_path / "mem3.sqlite"
    from app.memory.reasoning_memory import reflect, save_trajectory
    t = save_trajectory(db, goal="导出", steps=["preflight"], outcome="success")
    reflect(db, t.trajectory_id)
    out = tmp_path / "out2"
    counts = export_markdown(db, out)
    assert counts["principles"] == 1
    assert (out / "principles.md").exists()


def test_import_invalid_dir(tmp_path):
    with pytest.raises(MemoryFilesError):
        import_markdown(tmp_path / "x.sqlite", tmp_path / "missing")
