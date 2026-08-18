"""Tests for reasoning memory (ReasoningBank absorption)."""
from __future__ import annotations

import pytest

from app.memory.reasoning_memory import (
    ReasoningMemoryError,
    record_application,
    reflect,
    retrieve_principles,
    save_trajectory,
)


def test_failure_trajectory_needs_error_pattern(tmp_path):
    db = tmp_path / "rm.sqlite"
    with pytest.raises(ReasoningMemoryError, match="error_pattern"):
        save_trajectory(db, goal="g", steps=["s"], outcome="failure")


def test_success_and_failure_reflection(tmp_path):
    db = tmp_path / "rm.sqlite"
    ok = save_trajectory(db, goal="导出 PDF", steps=["preflight", "export"],
                         outcome="success", importance=0.8)
    bad = save_trajectory(db, goal="导出 PDF", steps=["export"],
                          outcome="failure", error_pattern="未嵌入字体导致乱码", importance=0.9)
    p_ok = reflect(db, ok.trajectory_id)
    p_bad = reflect(db, bad.trajectory_id)
    assert p_ok.category == "success_pattern"
    assert p_bad.category == "failure_pattern"
    assert "嵌入字体" in p_bad.statement or "未嵌入字体" in p_bad.statement


def test_retrieval_ranks_relevant_higher(tmp_path):
    db = tmp_path / "rm.sqlite"
    t1 = save_trajectory(db, goal="颜色管理", steps=["设置配置文件"], outcome="success", importance=0.7)
    t2 = save_trajectory(db, goal="字体嵌入", steps=["嵌入字体"], outcome="success", importance=0.7)
    reflect(db, t1.trajectory_id)
    reflect(db, t2.trajectory_id)
    results = retrieve_principles(db, "字体", top_k=5)
    assert results
    assert results[0]["score"] > 0
    assert "字体" in results[0]["statement"]


def test_usage_establishes_principle(tmp_path):
    db = tmp_path / "rm.sqlite"
    t = save_trajectory(db, goal="验证输出", steps=["校验"], outcome="success", importance=0.9)
    p = reflect(db, t.trajectory_id)
    confidence = p.confidence
    for _ in range(3):
        confidence = record_application(db, p.principle_id, outcome="success")
    row = __import__("sqlite3").connect(str(db)).execute(
        "SELECT status FROM reasoning_principles WHERE principle_id=?", (p.principle_id,)
    ).fetchone()
    assert row[0] == "established"
    assert confidence >= 0.6


def test_failure_application_lowers_confidence(tmp_path):
    db = tmp_path / "rm.sqlite"
    t = save_trajectory(db, goal="g", steps=["s"], outcome="success", importance=0.5)
    p = reflect(db, t.trajectory_id)
    c1 = record_application(db, p.principle_id, outcome="success")
    c2 = record_application(db, p.principle_id, outcome="failure")
    assert c2 < c1


def test_validation(tmp_path):
    db = tmp_path / "rm.sqlite"
    with pytest.raises(ReasoningMemoryError):
        save_trajectory(db, goal="", steps=["s"], outcome="success")
    with pytest.raises(ReasoningMemoryError):
        retrieve_principles(db, "x", top_k=0)
