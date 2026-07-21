"""Application composition adapter for Sleep Loop Runtime execution."""

from __future__ import annotations

from typing import Any

from app.adapters.sleep_taskpack import project_sleep_ledger_task_to_runtime
from app.facades.runtime import run_runtime_task
from app.schemas import CoreObject
from shared import sleep_loop_engine


def execute_sleep_runtime_task(task: dict[str, Any]) -> dict[str, Any]:
    """Project one leased ledger task through the canonical Runtime facade."""

    runtime_task = project_sleep_ledger_task_to_runtime(
        task,
        declared_allowed_tools=sleep_loop_engine.REAL_EXECUTORS,
        satisfied_dependency_ids=task.get("dependencies", []),
    )
    outcome = run_runtime_task(
        CoreObject(content=str(task.get("content") or task.get("title") or "")),
        runtime_task,
    )
    result: dict[str, Any] = {}
    if outcome.trace and outcome.trace.events:
        tool_result = outcome.trace.events[-1].get("result", {})
        if isinstance(tool_result, dict):
            result.update(tool_result)
    result["runtime_status"] = outcome.status
    result["permission"] = outcome.permission.model_dump(mode="json")
    if outcome.trace:
        result["trace_id"] = outcome.trace.id
    if outcome.evaluation:
        result["evaluation"] = outcome.evaluation.model_dump(mode="json")
    if outcome.lesson:
        result["lesson"] = outcome.lesson.model_dump(mode="json")
    if outcome.status == "blocked":
        result["status"] = "blocked"
        result.setdefault("error", outcome.permission.reason)
    elif outcome.status == "failed":
        result["status"] = "error"
        result.setdefault("error", "runtime_evaluation_failed")
    return result


def configure_sleep_runtime() -> None:
    """Bind the application Runtime adapter to the lower Sleep scheduler port."""

    sleep_loop_engine.configure_runtime_task_executor(execute_sleep_runtime_task)


def tick_once(*, worker_id: str | None = None) -> dict[str, Any]:
    """Run one configured Sleep tick from an application composition root."""

    configure_sleep_runtime()
    return sleep_loop_engine.tick_once(worker_id=worker_id)
