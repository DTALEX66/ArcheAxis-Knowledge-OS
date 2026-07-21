"""Tests for agent executor module."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.agent.executor import execute
from app.schemas import ExecutionTrace, PermissionDecision, TaskPack


def make_task(tools=None, steps=None, risk="low"):
    return TaskPack(
        id="task_test_001",
        goal="test task",
        steps=steps or [{"step_id": "s1", "action": "echo test", "tool": "echo"}],
        tools=tools or ["echo"],
        risk_level=risk,
    )


def make_perm(allowed=None, blocked=None, review=False):
    return PermissionDecision(
        task_id="task_test_001",
        risk_level="low",
        allowed_tools=allowed or ["echo"],
        blocked_tools=blocked or [],
        requires_human_review=review,
        reason="test",
    )


class TestExecutor:
    def test_basic_execution(self):
        task = make_task()
        perm = make_perm()
        trace = execute(task, perm)
        assert isinstance(trace, ExecutionTrace) or hasattr(trace, "success")
        assert len(trace.events) > 0

    def test_execution_multiple_steps(self):
        task = make_task(steps=[
            {"step_id": "s1", "action": "step one", "tool": "echo"},
            {"step_id": "s2", "action": "step two", "tool": "echo"},
            {"step_id": "s3", "action": "step three", "tool": "echo"},
        ])
        perm = make_perm(allowed=["echo"])
        trace = execute(task, perm)
        assert len(trace.events) == 3

    def test_trace_contains_step_results(self):
        task = make_task()
        perm = make_perm()
        trace = execute(task, perm)
        for event in trace.events:
            # Events have 'step' dict containing step details
            assert "step" in event or "result" in event

    def test_step_tool_must_be_explicitly_allowed(self, monkeypatch):
        task = TaskPack(
            id="task_test_001",
            goal="reject an undeclared write",
            steps=[{"step_id": "s1", "tool": "safe_write", "dry_run": False}],
            tools=["safe_write"],
        )
        permission = PermissionDecision(
            task_id=task.id,
            risk_level="low",
            allowed_tools=[],
            blocked_tools=[],
            reason="test",
        )
        monkeypatch.setattr(
            "app.agent.executor.run_tool",
            lambda *args, **kwargs: (_ for _ in ()).throw(
                AssertionError("an unauthorized tool must not execute")
            ),
        )

        trace = execute(task, permission)

        assert trace.success is False
        assert trace.events[0]["result"]["status"] == "blocked"

    def test_medium_risk_forces_dry_run_even_when_step_requests_real_run(self, monkeypatch):
        task = TaskPack(
            id="task_test_001",
            goal="preview a write",
            steps=[{"step_id": "s1", "tool": "safe_write", "dry_run": False}],
            tools=["safe_write"],
        )
        permission = PermissionDecision(
            task_id=task.id,
            risk_level="medium",
            allowed_tools=["safe_write"],
            reason="medium-risk tools are dry-run only",
        )
        calls = []

        def tracked(tool_name, step, *, dry_run):
            calls.append((tool_name, dry_run))
            return {
                "tool": tool_name,
                "risk_level": "medium",
                "dry_run": dry_run,
                "status": "ok",
            }

        monkeypatch.setattr("app.agent.executor.run_tool", tracked)

        trace = execute(task, permission)

        assert trace.success is True
        assert calls == [("safe_write", True)]
