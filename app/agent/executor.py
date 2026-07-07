"""Task executor — permission-gated step execution."""

from app.schemas import ExecutionTrace, PermissionDecision, TaskPack
from app.tools.registry import run_tool


def execute(task: TaskPack, permission: PermissionDecision | None = None) -> ExecutionTrace:
    """Execute a TaskPack with optional permission gating.

    If permission is provided, blocked tools are skipped and marked as blocked.
    If permission.requires_human_review, execution is skipped entirely.
    """
    trace = ExecutionTrace(task_id=task.id)

    # ── Human review gate ──
    if permission and permission.requires_human_review:
        trace.events.append(
            {
                "step": {"name": "permission_check", "type": "gate"},
                "result": {
                    "tool": "permission",
                    "risk_level": permission.risk_level,
                    "status": "blocked",
                    "message": "requires human review",
                    "reason": permission.reason,
                },
            }
        )
        trace.result = {"status": "blocked", "reason": permission.reason}
        trace.success = False
        return trace

    blocked_set = set(permission.blocked_tools) if permission else set()
    results: list[dict] = []
    success = True

    for step in task.steps:
        tool_name = step.get("tool", "echo")

        # ── Block gated tools ──
        if tool_name in blocked_set:
            event = {
                "step": step,
                "result": {
                    "tool": tool_name,
                    "risk_level": "blocked",
                    "dry_run": True,
                    "status": "blocked",
                    "message": f"tool '{tool_name}' blocked by permission policy",
                },
            }
            trace.events.append(event)
            results.append(event["result"])
            success = False
            continue

        # ── Determine dry_run from permission policy ──
        dry_run = step.get("dry_run")
        if dry_run is None and permission and permission.risk_level in ("medium", "high"):
            dry_run = True

        result = run_tool(tool_name, step, dry_run=dry_run)
        event = {"step": step, "result": result}
        trace.events.append(event)
        results.append(result)

        if result.get("status") in {"error", "blocked"}:
            success = False

    trace.result = {"status": "done" if success else "completed_with_errors", "outputs": results}
    trace.success = success
    return trace
