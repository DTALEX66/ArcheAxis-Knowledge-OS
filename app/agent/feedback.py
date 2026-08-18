"""Execution feedback — closes the machine-learning feedback arc (gap D).

After the agent executor runs a TaskPack, its trace becomes experience:
    ExecutionTrace → lifecycle events → experience_harvest.capture (principle)
    → skill_evolution.record_usage (when a skill was exercised)

This is a consumer of the executor's output — the executor itself stays
unchanged (controlled boundary). Fail-closed: a malformed trace never raises
through the executor.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.agent.experience_harvest import LifecycleEvent, capture
from app.knowledge.skill_evolution import record_usage


class FeedbackError(ValueError):
    """Raised when execution feedback cannot be recorded."""


def record_execution_feedback(
    db: str | Path,
    trace: dict[str, Any],
    *,
    skill_id: str | None = None,
) -> dict[str, Any]:
    """Consume one ExecutionTrace and return the harvested principle + skill usage.

    Args:
        db: reasoning/skill sqlite path.
        trace: ExecutionTrace-shaped dict (task_id, events, success).
        skill_id: optional skill exercised by the task.

    Returns:
        {principle_id, principle, usage_id} — principle may be absent if the
        trace cannot be converted.
    """
    task_id = str(trace.get("task_id") or trace.get("id") or "task")
    success = bool(trace.get("success", True))
    events: list[LifecycleEvent] = []
    steps = trace.get("events", [])
    if not steps:
        raise FeedbackError("trace requires events")

    events.append(LifecycleEvent.started(f"task {task_id}", "now"))
    for event in steps:
        step = event.get("step", {}) if isinstance(event, dict) else {}
        tool = step.get("tool") or step.get("name")
        if tool:
            events.append(LifecycleEvent.tool_called(str(tool), "now"))
    error = None
    if not success:
        result = trace.get("result") or {}
        error = result.get("reason") or result.get("message") or "execution failed"
    events.append(LifecycleEvent.ended(
        "failure" if not success else "success", "now", error=error,
    ))

    try:
        principles = capture(db, events, llm_reflection=None)
    except Exception as exc:  # noqa: BLE001 — fail closed, never break the caller
        raise FeedbackError(f"harvest failed: {exc}") from exc

    usage_id: str | None = None
    if skill_id and success:
        usage_id = record_usage(db, skill_id=skill_id, task=f"task {task_id}",
                                outcome="success")
    elif skill_id:
        usage_id = record_usage(db, skill_id=skill_id, task=f"task {task_id}",
                                outcome="failure",
                                failure_analysis=error or "execution failed")
    return {"principle_id": principles[0].principle_id,
            "principle": principles[0].statement,
            "usage_id": usage_id}
