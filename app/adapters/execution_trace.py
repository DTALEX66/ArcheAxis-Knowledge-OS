"""ExecutionTrace adapters with fail-closed legacy boundary validation."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from app.adapters.taskpack import ContractMappingError
from app.contracts.v1 import CONTRACT_VERSION, ExecutionTraceV1
from app.schemas import ExecutionTrace as RuntimeExecutionTrace


def from_runtime_trace(trace: RuntimeExecutionTrace) -> ExecutionTraceV1:
    """Convert the runtime model to the canonical v1 contract losslessly."""

    return ExecutionTraceV1(
        schema_version=CONTRACT_VERSION,
        trace_id=trace.id,
        task_id=trace.task_id,
        events=deepcopy(trace.events),
        result=deepcopy(trace.result),
        success=trace.success,
        created_at=trace.created_at,
    )


def to_runtime_trace(contract: ExecutionTraceV1) -> RuntimeExecutionTrace:
    """Rebuild the current runtime trace without dropping canonical fields."""

    return RuntimeExecutionTrace(
        id=contract.trace_id,
        task_id=contract.task_id,
        events=deepcopy(contract.events),
        result=deepcopy(contract.result),
        success=contract.success,
        created_at=contract.created_at,
    )


def from_trace_row(row: dict[str, Any]) -> ExecutionTraceV1:
    """Map the decoded SQLite/KB trace row to v1 without coercing corrupt fields."""

    required = {"id", "task_id", "events", "result", "success", "created_at"}
    missing = sorted(required - row.keys())
    if missing:
        raise ContractMappingError(f"execution trace row missing fields: {', '.join(missing)}")
    unmapped = sorted(row.keys() - required)
    if unmapped:
        raise ContractMappingError(f"execution trace row unmapped fields: {', '.join(unmapped)}")
    if not isinstance(row["events"], list):
        raise ContractMappingError("execution trace row events must be a list")
    if not isinstance(row["result"], dict):
        raise ContractMappingError("execution trace row result must be an object")
    success = row["success"]
    if success is not None and type(success) not in (bool, int):
        raise ContractMappingError("execution trace row success must be 0, 1, or null")
    if type(success) is int and success not in (0, 1):
        raise ContractMappingError("execution trace row success must be 0, 1, or null")

    return ExecutionTraceV1(
        schema_version=CONTRACT_VERSION,
        trace_id=row["id"],
        task_id=row["task_id"],
        events=deepcopy(row["events"]),
        result=deepcopy(row["result"]),
        success=None if success is None else bool(success),
        created_at=row["created_at"],
    )


def to_trace_row(contract: ExecutionTraceV1) -> dict[str, Any]:
    """Map v1 to the decoded row shape accepted by the runtime SQLite writer."""

    return {
        "id": contract.trace_id,
        "task_id": contract.task_id,
        "events": deepcopy(contract.events),
        "result": deepcopy(contract.result),
        "success": contract.success,
        "created_at": contract.created_at,
    }
