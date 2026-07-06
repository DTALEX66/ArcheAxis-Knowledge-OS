"""Tests for Knowledge-Base taskpack module."""
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_PROJECT_ROOT))
sys.path.insert(0, str(_PROJECT_ROOT / "Knowledge-Base"))

from taskpack import build_taskpack


class TestTaskPack:
    def test_build_basic_taskpack(self):
        task = build_taskpack(
            goal="Test taskpack generation",
            steps=[
                {"step_id": "s1", "action": "read", "tool": "echo"},
                {"step_id": "s2", "action": "write", "tool": "echo"},
            ],
            allowed_tools=["echo", "file_read"],
            risk_level="low",
        )
        assert task.goal == "Test taskpack generation"
        assert len(task.steps) == 2
        assert task.steps[0]["step_id"] == "s1"
        assert task.allowed_tools == ["echo", "file_read"]
        assert task.risk_level == "low"
        assert task.task_id.startswith("task_")

    def test_taskpack_empty_steps(self):
        task = build_taskpack(
            goal="Empty steps test",
            steps=[],
            allowed_tools=["echo"],
            risk_level="low",
        )
        assert task.steps == []

    def test_taskpack_to_dict(self):
        task = build_taskpack(
            goal="Dict test",
            steps=[{"step_id": "s1", "action": "test", "tool": "echo"}],
            allowed_tools=["echo"],
            risk_level="low",
        )
        d = task.to_dict()
        assert d["task_id"].startswith("task_")
        assert d["goal"] == "Dict test"
        assert len(d["steps"]) == 1

    def test_taskpack_high_risk(self):
        task = build_taskpack(
            goal="High risk task",
            steps=[{"step_id": "s1", "action": "deploy", "tool": "echo"}],
            allowed_tools=["echo"],
            risk_level="high",
        )
        assert task.risk_level == "high"
