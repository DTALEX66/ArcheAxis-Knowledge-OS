"""TaskPack adapters with explicit loss reporting."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from pydantic import BaseModel, Field

from app.contracts.v1 import CONTRACT_VERSION, TaskPackV1, TaskStepV1
from app.schemas import TaskPack as RuntimeTaskPack
from knowledge_base.taskpack import TaskPack as KnowledgeTaskPack


class ContractMappingError(ValueError):
    """Raised when an adapter would need to invent or downgrade data."""


class RuntimeTaskProjection(BaseModel):
    """Runtime-compatible view plus fields the runtime model cannot represent."""

    task: RuntimeTaskPack
    unmapped_fields: dict[str, Any] = Field(default_factory=dict)


def from_knowledge_taskpack(task: KnowledgeTaskPack) -> TaskPackV1:
    """Convert the KB dataclass into the canonical v1 contract losslessly."""

    requested_tools = _step_tools(task.steps)
    return TaskPackV1(
        schema_version=CONTRACT_VERSION,
        task_id=task.task_id,
        context_id=task.context_id,
        goal=task.goal,
        steps=deepcopy(task.steps),
        requested_tools=requested_tools,
        declared_allowed_tools=list(task.allowed_tools),
        explicitly_blocked_tools=list(task.blocked_tools),
        constraints=list(task.constraints),
        success_criteria=list(task.success_criteria),
        risk_level=task.risk_level,
        requires_review=task.requires_review,
    )


def to_knowledge_taskpack(contract: TaskPackV1) -> KnowledgeTaskPack:
    """Rebuild the legacy KB dataclass without dropping canonical fields."""

    if _step_tools(contract.steps) != contract.requested_tools:
        raise ContractMappingError("requested_tools do not match step tools")

    return KnowledgeTaskPack(
        task_id=contract.task_id,
        context_id=contract.context_id,
        goal=contract.goal,
        steps=[step.model_dump() for step in contract.steps],
        allowed_tools=list(contract.declared_allowed_tools),
        blocked_tools=list(contract.explicitly_blocked_tools),
        constraints=list(contract.constraints),
        success_criteria=list(contract.success_criteria),
        risk_level=contract.risk_level,
        requires_review=contract.requires_review,
    )


def _step_tools(steps: list[dict[str, Any]] | list[TaskStepV1]) -> list[str]:
    result: list[str] = []
    for step in steps:
        tool = step.tool if isinstance(step, TaskStepV1) else step.get("tool")
        if isinstance(tool, str) and tool and tool not in result:
            result.append(tool)
    return result


def project_to_runtime(contract: TaskPackV1) -> RuntimeTaskProjection:
    """Project v1 to the narrower runtime model and report every unmapped field."""

    if contract.requires_review:
        raise ContractMappingError("runtime projection cannot bypass requires_review")

    actual_step_tools = _step_tools(contract.steps)
    if actual_step_tools != contract.requested_tools:
        raise ContractMappingError("requested_tools do not match step tools")

    conflicting_tools = sorted(
        set(contract.declared_allowed_tools) & set(contract.explicitly_blocked_tools)
    )
    if conflicting_tools:
        raise ContractMappingError(
            f"tools cannot be both allowed and blocked: {', '.join(conflicting_tools)}"
        )

    blocked_requests = sorted(
        set(contract.requested_tools) & set(contract.explicitly_blocked_tools)
    )
    if blocked_requests:
        raise ContractMappingError(f"requested tools are blocked: {', '.join(blocked_requests)}")

    undeclared_requests = sorted(
        set(contract.requested_tools) - set(contract.declared_allowed_tools)
    )
    if undeclared_requests:
        raise ContractMappingError(
            f"requested tools are not declared allowed: {', '.join(undeclared_requests)}"
        )

    if contract.risk_level == "critical":
        raise ContractMappingError("runtime TaskPack cannot represent critical risk")

    unmapped: dict[str, Any] = {}
    if contract.declared_allowed_tools:
        unmapped["declared_allowed_tools"] = list(contract.declared_allowed_tools)
    if contract.explicitly_blocked_tools:
        unmapped["explicitly_blocked_tools"] = list(contract.explicitly_blocked_tools)
    if contract.context_id:
        unmapped["context_id"] = contract.context_id
    task = RuntimeTaskPack(
        id=contract.task_id,
        goal=contract.goal,
        steps=[step.model_dump() for step in contract.steps],
        constraints=contract.constraints,
        tools=contract.requested_tools,
        risk_level=contract.risk_level,
        success_criteria=contract.success_criteria,
    )
    return RuntimeTaskProjection(task=task, unmapped_fields=unmapped)
