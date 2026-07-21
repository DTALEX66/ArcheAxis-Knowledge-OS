"""Public runtime facade over the existing route/permission/execute/trace pipeline."""

from __future__ import annotations

from typing import Literal

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
) -> RuntimeTaskResult:
    """Authorize, execute, evaluate, and derive one trace-bound terminal result."""

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
