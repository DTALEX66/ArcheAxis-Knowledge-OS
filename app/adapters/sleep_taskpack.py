"""Fail-closed adapter from Sleep Loop ledger tasks to ``TaskPackV1``."""

from __future__ import annotations

import json
from collections.abc import Iterable
from typing import Any

from app.adapters.taskpack import ContractMappingError
from app.contracts.v1 import CONTRACT_VERSION, TaskPackV1

_NON_EXECUTING_EXECUTORS = {
    "context_pack_build",
    "echo",
    "no-op",
    "no_op",
    "noop",
    "preview",
    "taskpack_generate",
}


def _json(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    except (TypeError, ValueError) as exc:
        raise ContractMappingError("sleep ledger task contains non-JSON data") from exc


def from_sleep_ledger_task(
    task: dict[str, Any],
    *,
    declared_allowed_tools: Iterable[str] | None = None,
) -> TaskPackV1:
    """Represent one decoded Sleep Loop ledger row as canonical execution intent.

    Dependency IDs remain explicit constraints. They are deliberately not turned
    into success criteria or evidence: this adapter cannot prove dependencies ran.
    """

    task_id = str(task.get("id", "")).strip()
    executor = str(task.get("executor", "")).strip()
    payload = task.get("payload", {})
    dependencies = task.get("dependencies", [])
    if not task_id:
        raise ContractMappingError("sleep ledger task requires id")
    if not executor:
        raise ContractMappingError("sleep ledger task requires executor")
    if not isinstance(payload, dict):
        raise ContractMappingError("sleep ledger task payload must be an object")
    if not isinstance(dependencies, list) or not all(
        isinstance(dependency, str) and dependency for dependency in dependencies
    ):
        raise ContractMappingError("sleep ledger task dependencies must be non-empty string IDs")

    allowed_tools = list(declared_allowed_tools or [])
    status = str(task.get("status", "")).strip() or "unknown"
    goal = str(task.get("content") or task.get("title") or "").strip()
    if not goal:
        raise ContractMappingError("sleep ledger task requires content or title")

    constraints = [f"sleep_ledger_status={status}"]
    if dependencies:
        constraints.append(f"sleep_dependency_ids_json={_json(dependencies)}")

    return TaskPackV1(
        schema_version=CONTRACT_VERSION,
        task_id=task_id,
        context_id=str(task.get("run_id", "")),
        goal=goal,
        steps=[
            {
                "step_id": f"{task_id}:execute",
                "action": f"sleep_payload_json={_json(payload)}",
                "tool": executor,
            }
        ],
        requested_tools=[executor],
        declared_allowed_tools=allowed_tools,
        constraints=constraints,
        success_criteria=[],
        risk_level=task.get("risk_level", "low"),
        requires_review=bool(task.get("requires_review", False)),
    )


def project_sleep_ledger_task_for_execution(
    task: dict[str, Any],
    *,
    declared_allowed_tools: Iterable[str] | None = None,
    satisfied_dependency_ids: Iterable[str] | None = None,
) -> TaskPackV1:
    """Project a ledger row only when its execution safety can be represented.

    Dependency completion is caller evidence, not something this DTO adapter
    infers from dependency IDs or the task's own ledger status.
    """

    status = str(task.get("status", "")).strip().lower()
    executor = str(task.get("executor", "")).strip()
    executor_key = executor.lower()
    payload = task.get("payload", {})
    dependencies = task.get("dependencies", [])
    allowed_tools = list(declared_allowed_tools or [])

    if status == "blocked":
        raise ContractMappingError("blocked sleep ledger task cannot be projected for execution")
    if not isinstance(payload, dict):
        raise ContractMappingError("sleep ledger task payload must be an object")
    if executor_key in _NON_EXECUTING_EXECUTORS:
        raise ContractMappingError(f"no-op executor cannot be projected: {executor or '<missing>'}")
    if payload.get("dry_run") is True:
        raise ContractMappingError("dry_run sleep task cannot be projected for execution")
    if payload.get("preview") is True or payload.get("preview_only") is True:
        raise ContractMappingError("preview sleep task cannot be projected for execution")
    if payload.get("no_op") is True or payload.get("noop") is True:
        raise ContractMappingError("no-op sleep task cannot be projected for execution")
    mode = str(payload.get("mode", "")).strip().lower()
    if mode in {"dry-run", "dry_run"}:
        raise ContractMappingError("dry_run sleep task cannot be projected for execution")
    if mode == "preview":
        raise ContractMappingError("preview sleep task cannot be projected for execution")
    if mode in {"no-op", "no_op", "noop"}:
        raise ContractMappingError("no-op sleep task cannot be projected for execution")
    if executor_key == "safe_write" and payload.get("dry_run") is not False:
        raise ContractMappingError("safe_write requires explicit dry_run false")
    if str(task.get("risk_level", "low")).strip().lower() == "critical":
        raise ContractMappingError("critical sleep task cannot be projected for execution")
    if executor not in allowed_tools:
        raise ContractMappingError(f"executor is not declared allowed: {executor or '<missing>'}")
    if task.get("requires_review", False) not in (False, 0):
        raise ContractMappingError("runtime execution cannot bypass requires_review")
    if not isinstance(dependencies, list):
        raise ContractMappingError("sleep ledger task dependencies must be a list")
    satisfied = set(satisfied_dependency_ids or [])
    missing_dependencies = [dependency for dependency in dependencies if dependency not in satisfied]
    if missing_dependencies:
        raise ContractMappingError(
            "sleep ledger dependencies not proven complete: " + ", ".join(missing_dependencies)
        )

    return from_sleep_ledger_task(task, declared_allowed_tools=allowed_tools)
