"""Tests for experience harvesting (Meta Knowledge Graph absorption)."""
from __future__ import annotations

import pytest

from app.agent.experience_harvest import (
    HarvestError,
    LifecycleEvent,
    capture,
    events_to_trajectory,
)
from app.memory.reasoning_memory import retrieve_principles


def test_events_to_trajectory_success():
    draft = events_to_trajectory([
        LifecycleEvent.started("导出 PDF", "t1"),
        LifecycleEvent.tool_called("preflight", "t2"),
        LifecycleEvent.tool_called("export", "t3"),
        LifecycleEvent.ended("success", "t4"),
    ])
    assert draft.goal == "导出 PDF"
    assert draft.steps == ["preflight", "export"]
    assert draft.outcome == "success"


def test_events_to_trajectory_failure_carries_error():
    draft = events_to_trajectory([
        LifecycleEvent.started("导出 PDF", "t1"),
        LifecycleEvent.ended("failure", "t2", error="字体未嵌入"),
    ])
    assert draft.outcome == "failure"
    assert draft.error_pattern == "字体未嵌入"


def test_missing_goal_rejected():
    with pytest.raises(HarvestError, match="task_started"):
        events_to_trajectory([LifecycleEvent.ended("success", "t1")])


def test_capture_success_harvests_principle(tmp_path):
    db = tmp_path / "eh.sqlite"
    principles = capture(db, [
        LifecycleEvent.started("部署服务", "t1"),
        LifecycleEvent.tool_called("build", "t2"),
        LifecycleEvent.ended("success", "t3"),
    ])
    assert len(principles) == 1
    assert principles[0].category == "success_pattern"
    found = retrieve_principles(db, "部署", top_k=5)
    assert found and found[0]["principle_id"] == principles[0].principle_id


def test_capture_failure_requires_error(tmp_path):
    db = tmp_path / "eh2.sqlite"
    with pytest.raises(HarvestError, match="error"):
        capture(db, [
            LifecycleEvent.started("g", "t1"),
            LifecycleEvent.ended("failure", "t2"),
        ])
