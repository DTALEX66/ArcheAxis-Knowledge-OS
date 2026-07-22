"""Public runtime facade over the existing route/permission/execute/trace pipeline."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel

from app.agent.executor import execute
from app.core.permissions import check_permission
from app.core.router import route
from app.core.trace import log_trace
from app.evaluation.evaluator import evaluate
from app.evaluation.feedback import compile_lesson
from app.schemas import (
    AttentionDecision,
    CoreObject,
    EvalResult,
    ExecutionTrace,
    MachineLesson,
    PermissionDecision,
    TaskPack,
)


class RuntimeExecution(BaseModel):
    """Stable result contract for one permission-gated runtime execution."""

    route: AttentionDecision
    permission: PermissionDecision
    trace: ExecutionTrace | None = None


class RuntimeTaskResult(BaseModel):
    """One authoritative Runtime terminal decision for an executable TaskPack."""

    status: Literal["blocked", "done", "failed"]
    route: AttentionDecision
    permission: PermissionDecision
    trace: ExecutionTrace | None = None
    evaluation: EvalResult | None = None
    lesson: MachineLesson | None = None


def execute_runtime(
    document: CoreObject,
    task: TaskPack,
    *,
    decision: AttentionDecision | None = None,
) -> RuntimeExecution:
    """Route a document, authorize its task, execute it, and persist the trace."""
    route_decision = decision or route(document)
    permission = check_permission(task, document.content)
    if permission.requires_human_review:
        return RuntimeExecution(route=route_decision, permission=permission)
    trace = execute(task, permission)
    log_trace(trace)
    return RuntimeExecution(route=route_decision, permission=permission, trace=trace)


def run_runtime_task(
    document: CoreObject,
    task: TaskPack,
    *,
    decision: AttentionDecision | None = None,
    sleep_ledger_task: dict[str, Any] | None = None,
    dependency_proof: object | None = None,
) -> RuntimeTaskResult:
    """Authorize, execute, evaluate, and derive one trace-bound terminal result."""

    if any(item.startswith("sleep_ledger_status=") for item in task.constraints):
        if sleep_ledger_task is None:
            raise ValueError("sleep runtime task requires scheduler dependency proof")
        from app.adapters.sleep_taskpack import project_sleep_ledger_task_to_runtime
        from shared import sleep_loop_engine

        verified_dependencies = sleep_loop_engine.require_scheduler_dependency_proof(
            sleep_ledger_task, dependency_proof
        )
        expected = project_sleep_ledger_task_to_runtime(
            sleep_ledger_task,
            declared_allowed_tools=sleep_loop_engine.REAL_EXECUTORS,
            satisfied_dependency_ids=verified_dependencies,
        )
        if task.model_dump(mode="json") != expected.model_dump(mode="json"):
            raise ValueError("sleep runtime task does not match durable scheduler projection")

    execution = execute_runtime(document, task, decision=decision)
    if execution.permission.requires_human_review:
        return RuntimeTaskResult(
            status="blocked",
            route=execution.route,
            permission=execution.permission,
        )
    if execution.trace is None:
        raise RuntimeError("runtime facade returned no trace for an allowed task")
    evaluation = evaluate(execution.trace)
    lesson = compile_lesson(evaluation, execution.trace)
    return RuntimeTaskResult(
        status="done" if evaluation.success else "failed",
        route=execution.route,
        permission=execution.permission,
        trace=execution.trace,
        evaluation=evaluation,
        lesson=lesson,
    )
