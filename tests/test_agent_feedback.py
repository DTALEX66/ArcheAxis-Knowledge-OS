"""Tests for execution feedback (loop gap D)."""
from __future__ import annotations

import pytest

from app.agent.feedback import FeedbackError, record_execution_feedback
from app.memory.reasoning_memory import retrieve_principles
from app.knowledge.skill_evolution import evaluate_skill


def _trace(task_id="t1", *, success=True, events=None, reason=None):
    return {
        "task_id": task_id,
        "success": success,
        "events": events or [
            {"step": {"tool": "preflight", "type": "tool"}},
            {"step": {"tool": "export", "type": "tool"}},
        ],
        "result": {"reason": reason} if reason else {},
    }


def test_success_trace_harvests_principle(tmp_path):
    db = tmp_path / "fb.sqlite"
    out = record_execution_feedback(db, _trace(success=True))
    assert out["principle_id"]
    assert "preflight" in out["principle"]
    found = retrieve_principles(db, "preflight", top_k=5)
    assert found and found[0]["principle_id"] == out["principle_id"]


def test_failure_trace_carries_error(tmp_path):
    db = tmp_path / "fb2.sqlite"
    out = record_execution_feedback(db, _trace(success=False, reason="字体未嵌入"))
    assert out["principle_id"]
    found = retrieve_principles(db, "字体", top_k=5)
    assert found and "字体" in found[0]["statement"] or "未嵌入" in found[0]["statement"]


def test_skill_usage_recorded(tmp_path):
    db = tmp_path / "fb3.sqlite"
    out = record_execution_feedback(db, _trace(success=True), skill_id="sk-print")
    assert out["usage_id"]
    ev = evaluate_skill(db, "sk-print")
    assert ev.total_usages == 1
    assert ev.verdict == "insufficient_data"


def test_trace_without_events_rejected(tmp_path):
    db = tmp_path / "fb4.sqlite"
    with pytest.raises(FeedbackError, match="events"):
        record_execution_feedback(db, {"task_id": "t", "success": True, "events": []})
