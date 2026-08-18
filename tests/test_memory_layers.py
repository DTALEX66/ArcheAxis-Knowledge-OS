"""Tests for the layered memory (MemoryOS/MemOS/Hermes Memory OS absorption)."""
from __future__ import annotations

import pytest

from app.memory.memory_layers import (
    MemoryLayer,
    MemoryLayerError,
    WORKING_MEMORY_CAPACITY,
    classify_content,
    recall,
    recent_working,
    store,
)


def test_classify_defaults_to_professional():
    assert classify_content("贝叶斯推断是一种统计方法") == MemoryLayer.L3_PROFESSIONAL


def test_classify_project_markers():
    assert classify_content("WORK-LAB 的 CI 门禁又红了") == MemoryLayer.L2_PROJECT


def test_classify_persona_markers():
    assert classify_content("我习惯在下午做深度设计") == MemoryLayer.L4_PERSONA


def test_explicit_layer_wins():
    assert classify_content("随便一句话", explicit_layer=MemoryLayer.L1_WORKING)         == MemoryLayer.L1_WORKING


def test_persona_requires_tag(tmp_path):
    db = tmp_path / "ml.sqlite"
    with pytest.raises(MemoryLayerError, match="persona tag"):
        store(db, content="我习惯用双屏工作", layer=MemoryLayer.L4_PERSONA)


def test_l4_store_and_recall(tmp_path):
    db = tmp_path / "ml.sqlite"
    store(db, content="我习惯在上午处理需要创造力的任务", layer=MemoryLayer.L4_PERSONA,
          tags=["persona", "workflow"])
    results = recall(db, query="创造力", layers=[MemoryLayer.L4_PERSONA])
    assert results and results[0]["layer"] == MemoryLayer.L4_PERSONA.value


def test_working_memory_ring_buffer(tmp_path):
    db = tmp_path / "ml.sqlite"
    for i in range(WORKING_MEMORY_CAPACITY + 10):
        store(db, content=f"task-{i}", layer=MemoryLayer.L1_WORKING)
    recent = recent_working(db, top_k=1000)
    assert len(recent) == WORKING_MEMORY_CAPACITY
    contents = [r["content"] for r in recent]
    assert "task-0" not in contents
    assert "task-59" in contents


def test_validation(tmp_path):
    db = tmp_path / "ml.sqlite"
    with pytest.raises(MemoryLayerError):
        store(db, content="", layer=MemoryLayer.L3_PROFESSIONAL)
    with pytest.raises(MemoryLayerError):
        store(db, content="x", layer=MemoryLayer.L3_PROFESSIONAL, importance=2.0)
    with pytest.raises(MemoryLayerError):
        recall(db, query="x", top_k=0)
