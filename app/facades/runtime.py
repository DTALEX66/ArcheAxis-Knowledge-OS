"""Public runtime facade over the existing route/permission/execute/trace pipeline."""

from __future__ import annotations

from pydantic import BaseModel

from app.agent.executor import execute
from app.core.permissions import check_permission
from app.core.router import route
from app.core.trace import log_trace
from app.schemas import AttentionDecision, CoreObject, ExecutionTrace, PermissionDecision, TaskPack


class RuntimeExecution(BaseModel):
    """Stable result contract for one permission-gated runtime execution."""

    route: AttentionDecision
    permission: PermissionDecision
    trace: ExecutionTrace | None = None


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
