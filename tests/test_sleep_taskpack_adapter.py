from __future__ import annotations

import pytest


def _ledger_task(**overrides):
    task = {
        "id": "slt_001",
        "run_id": "run_001",
        "title": "Read the design",
        "content": "Read the committed design file",
        "status": "pending",
        "executor": "file_read",
        "payload": {"path": "docs/design.md"},
        "dependencies": ["slt_parent_001", "slt_parent_002"],
        "risk_level": "low",
    }
    task.update(overrides)
    return task


def test_sleep_ledger_task_maps_execution_intent_and_dependencies_to_canonical_taskpack():
    from app.adapters.sleep_taskpack import from_sleep_ledger_task

    canonical = from_sleep_ledger_task(
        _ledger_task(), declared_allowed_tools=["file_read", "kb_search"]
    )

    assert canonical.schema_version == "1.0.0"
    assert canonical.task_id == "slt_001"
    assert canonical.context_id == "run_001"
    assert canonical.goal == "Read the committed design file"
    assert canonical.steps[0].step_id == "slt_001:execute"
    assert canonical.steps[0].tool == "file_read"
    assert canonical.steps[0].action == 'sleep_payload_json={"path":"docs/design.md"}'
    assert canonical.requested_tools == ["file_read"]
    assert canonical.declared_allowed_tools == ["file_read", "kb_search"]
    assert canonical.risk_level == "low"
    assert canonical.requires_review is False
    assert canonical.constraints == [
        "sleep_ledger_status=pending",
        'sleep_dependency_ids_json=["slt_parent_001","slt_parent_002"]',
    ]
    assert canonical.success_criteria == []


def test_sleep_execution_projection_accepts_declared_real_task():
    from app.adapters.sleep_taskpack import project_sleep_ledger_task_for_execution

    canonical = project_sleep_ledger_task_for_execution(
        _ledger_task(),
        declared_allowed_tools=["file_read"],
        satisfied_dependency_ids=["slt_parent_001", "slt_parent_002"],
    )

    assert canonical.requested_tools == ["file_read"]
    assert canonical.declared_allowed_tools == ["file_read"]


def test_sleep_execution_projection_builds_runtime_task_with_real_payload():
    from app.adapters.sleep_taskpack import project_sleep_ledger_task_to_runtime

    runtime = project_sleep_ledger_task_to_runtime(
        _ledger_task(),
        declared_allowed_tools=["file_read"],
        satisfied_dependency_ids=["slt_parent_001", "slt_parent_002"],
    )

    assert runtime.id == "slt_001"
    assert runtime.tools == ["file_read"]
    assert runtime.steps == [
        {
            "id": "slt_001:execute",
            "name": "sleep_runtime_execute",
            "type": "tool",
            "tool": "file_read",
            "path": "docs/design.md",
        }
    ]


@pytest.mark.parametrize(
    ("task", "allowed_tools", "message"),
    [
        (_ledger_task(status="blocked"), ["file_read"], "blocked"),
        (_ledger_task(payload={"path": "docs/design.md", "dry_run": True}), ["file_read"], "dry_run"),
        (_ledger_task(payload={"path": "docs/design.md", "preview": True}), ["file_read"], "preview"),
        (_ledger_task(payload={"path": "docs/design.md", "no_op": True}), ["file_read"], "no-op"),
        (_ledger_task(risk_level="critical"), ["file_read"], "critical"),
        (_ledger_task(), [], "not declared allowed"),
        (_ledger_task(requires_review=True), ["file_read"], "requires_review"),
        (_ledger_task(executor="echo", payload={}), ["echo"], "no-op"),
    ],
)
def test_sleep_execution_projection_fails_closed(
    task: dict, allowed_tools: list[str], message: str
):
    from app.adapters.sleep_taskpack import (
        ContractMappingError,
        project_sleep_ledger_task_for_execution,
    )

    with pytest.raises(ContractMappingError, match=message):
        project_sleep_ledger_task_for_execution(
            task,
            declared_allowed_tools=allowed_tools,
            satisfied_dependency_ids=task["dependencies"],
        )


def test_sleep_execution_projection_does_not_assume_ledger_dependencies_succeeded():
    from app.adapters.sleep_taskpack import (
        ContractMappingError,
        project_sleep_ledger_task_for_execution,
    )

    with pytest.raises(ContractMappingError, match="dependencies not proven complete"):
        project_sleep_ledger_task_for_execution(
            _ledger_task(), declared_allowed_tools=["file_read"]
        )
