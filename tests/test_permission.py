"""Tests for permission system."""
from app.core.permissions import check_permission
from app.schemas import TaskPack


def make_task(goal: str = "test", tools: list = None,
              risk_level: str = "low") -> TaskPack:
    return TaskPack(
        id="task_test_001",
        goal=goal,
        steps=[{"step_id": "s1", "action": "test", "tool": (tools or ["echo"])[0]}],
        tools=tools or ["echo"],
        risk_level=risk_level,
    )


class TestPermission:
    def test_low_risk_allowed(self):
        task = make_task(tools=["echo"])
        perm = check_permission(task, "normal task")
        assert perm.requires_human_review is False
        assert "echo" in perm.allowed_tools
        assert perm.blocked_tools == []

    def test_code_exec_blocked(self):
        task = make_task(tools=["code_exec"])
        perm = check_permission(task)
        assert "code_exec" in perm.blocked_tools
        # code_exec is "high" risk → not auto, blocked in executor but not requires_review here
        # Actually: high → auto=False, blocked=False → goes to blocked_tools

    def test_unknown_tool_defaults_medium(self):
        task = make_task(tools=["unknown_tool_xyz"])
        perm = check_permission(task)
        assert "unknown_tool_xyz" in perm.allowed_tools  # medium = auto-execute

    def test_content_risk_keywords_force_review(self):
        task = make_task(tools=["echo"])
        perm = check_permission(task, "use password to access the system")
        assert perm.requires_human_review is True
        assert perm.risk_level == "high"

    def test_mixed_tools_split(self):
        task = make_task(tools=["echo", "code_exec"])
        perm = check_permission(task)
        assert "echo" in perm.allowed_tools
        assert "code_exec" in perm.blocked_tools
