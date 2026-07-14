from __future__ import annotations

import pytest

from knowledge_base.taskpack import TaskPack as KnowledgeTaskPack


def _legacy_taskpack() -> KnowledgeTaskPack:
    return KnowledgeTaskPack(
        task_id="task_contract_001",
        context_id="ctx_contract_001",
        goal="Preserve every legacy task field",
        steps=[{"step_id": "s1", "action": "inspect", "tool": "file_read"}],
        allowed_tools=["file_read", "echo"],
        blocked_tools=["shell_exec", "delete_file"],
        constraints=["read only"],
        success_criteria=["all fields round-trip"],
        risk_level="high",
        requires_review=True,
    )


def test_knowledge_taskpack_round_trips_through_v1_without_field_loss():
    from app.adapters.taskpack import from_knowledge_taskpack, to_knowledge_taskpack

    legacy = _legacy_taskpack()

    canonical = from_knowledge_taskpack(legacy)
    restored = to_knowledge_taskpack(canonical)

    assert canonical.schema_version == "1.0.0"
    assert canonical.requested_tools == ["file_read"]
    assert canonical.declared_allowed_tools == legacy.allowed_tools
    assert canonical.explicitly_blocked_tools == legacy.blocked_tools
    assert restored.to_dict() == legacy.to_dict()


def test_knowledge_adapter_does_not_alias_mutable_legacy_or_canonical_fields():
    from app.adapters.taskpack import from_knowledge_taskpack, to_knowledge_taskpack

    legacy = _legacy_taskpack()
    legacy_snapshot = legacy.to_dict()
    canonical = from_knowledge_taskpack(legacy)

    canonical.steps[0].action = "mutated canonical"
    canonical.constraints.append("canonical only")
    assert legacy.to_dict() == legacy_snapshot

    restored = to_knowledge_taskpack(canonical)
    restored.steps[0]["action"] = "mutated restored"
    restored.constraints.append("restored only")
    assert canonical.steps[0].action == "mutated canonical"
    assert canonical.constraints == ["read only", "canonical only"]


def test_knowledge_adapter_rejects_requested_tools_not_representable_by_steps():
    from app.adapters.taskpack import (
        ContractMappingError,
        from_knowledge_taskpack,
        to_knowledge_taskpack,
    )

    canonical = from_knowledge_taskpack(_legacy_taskpack()).model_copy(
        update={"requested_tools": ["echo"]}
    )

    with pytest.raises(ContractMappingError, match="requested_tools"):
        to_knowledge_taskpack(canonical)


def test_runtime_projection_reports_fields_runtime_cannot_represent():
    from app.adapters.taskpack import from_knowledge_taskpack, project_to_runtime

    canonical = from_knowledge_taskpack(_legacy_taskpack()).model_copy(
        update={"requires_review": False}
    )

    projection = project_to_runtime(canonical)

    assert projection.task.id == canonical.task_id
    assert projection.task.tools == ["file_read"]
    assert projection.task.risk_level == canonical.risk_level
    assert projection.unmapped_fields == {
        "declared_allowed_tools": ["file_read", "echo"],
        "explicitly_blocked_tools": ["shell_exec", "delete_file"],
        "context_id": "ctx_contract_001",
    }


def test_runtime_projection_rejects_review_required_task():
    from app.adapters.taskpack import (
        ContractMappingError,
        from_knowledge_taskpack,
        project_to_runtime,
    )

    canonical = from_knowledge_taskpack(_legacy_taskpack())

    with pytest.raises(ContractMappingError, match="requires_review"):
        project_to_runtime(canonical)


def test_runtime_projection_rejects_tool_that_is_both_allowed_and_blocked():
    from app.adapters.taskpack import ContractMappingError, project_to_runtime
    from app.contracts.v1 import TaskPackV1

    contract = TaskPackV1(
        schema_version="1.0.0",
        task_id="task_conflict",
        goal="Do not execute blocked tools",
        steps=[{"step_id": "s1", "action": "run", "tool": "shell_exec"}],
        requested_tools=["shell_exec"],
        declared_allowed_tools=["shell_exec"],
        explicitly_blocked_tools=["shell_exec"],
    )

    with pytest.raises(ContractMappingError, match="allowed and blocked"):
        project_to_runtime(contract)


def test_runtime_projection_rejects_step_tool_not_declared_allowed():
    from app.adapters.taskpack import ContractMappingError, project_to_runtime
    from app.contracts.v1 import TaskPackV1

    contract = TaskPackV1(
        schema_version="1.0.0",
        task_id="task_undeclared",
        goal="Do not invent permission",
        steps=[{"step_id": "s1", "action": "run", "tool": "code_exec"}],
        requested_tools=["code_exec"],
        declared_allowed_tools=["file_read"],
    )

    with pytest.raises(ContractMappingError, match="not declared allowed"):
        project_to_runtime(contract)


def test_runtime_projection_rejects_requested_tool_not_used_by_steps():
    from app.adapters.taskpack import ContractMappingError, project_to_runtime
    from app.contracts.v1 import TaskPackV1

    contract = TaskPackV1(
        schema_version="1.0.0",
        task_id="task_mismatch",
        goal="Keep requested tools bound to steps",
        steps=[{"step_id": "s1", "action": "read", "tool": "file_read"}],
        requested_tools=["echo"],
        declared_allowed_tools=["file_read", "echo"],
    )

    with pytest.raises(ContractMappingError, match="do not match step tools"):
        project_to_runtime(contract)


def test_runtime_projection_rejects_requested_blocked_tool():
    from app.adapters.taskpack import ContractMappingError, project_to_runtime
    from app.contracts.v1 import TaskPackV1

    contract = TaskPackV1(
        schema_version="1.0.0",
        task_id="task_blocked",
        goal="Never request a blocked tool",
        steps=[{"step_id": "s1", "action": "run", "tool": "code_exec"}],
        requested_tools=["code_exec"],
        explicitly_blocked_tools=["code_exec"],
    )

    with pytest.raises(ContractMappingError, match="requested tools are blocked"):
        project_to_runtime(contract)


def test_runtime_projection_rejects_critical_risk_instead_of_downgrading():
    from app.adapters.taskpack import ContractMappingError, project_to_runtime
    from app.contracts.v1 import TaskPackV1

    contract = TaskPackV1(
        schema_version="1.0.0",
        task_id="task_critical",
        goal="Do not downgrade risk",
        risk_level="critical",
    )

    with pytest.raises(ContractMappingError, match="critical"):
        project_to_runtime(contract)


def test_taskpack_v1_schema_is_versioned_and_rejects_unknown_fields():
    from pydantic import ValidationError

    from app.contracts.v1 import TaskPackV1

    schema = TaskPackV1.model_json_schema()

    assert schema["$id"].endswith("/contracts/v1/taskpack.schema.json")
    assert schema["properties"]["schema_version"]["const"] == "1.0.0"
    assert schema["additionalProperties"] is False
    assert {"schema_version", "task_id", "goal"} <= set(schema["required"])
    with pytest.raises(ValidationError, match="schema_version"):
        TaskPackV1(task_id="task_unversioned", goal="reject missing version")
    with pytest.raises(ValidationError, match="unknown"):
        TaskPackV1(
            schema_version="1.0.0",
            task_id="task_extra",
            goal="reject extras",
            unknown=True,
        )


def test_ci_escapes_json_schema_id_from_shell_expansion():
    from pathlib import Path

    workflow = (
        Path(__file__).resolve().parents[1] / ".github/workflows/ci.yml"
    ).read_text(encoding="utf-8")
    assert "['\\$id']" in workflow
    assert "['$id']" not in workflow


def test_task_step_v1_rejects_unknown_nested_fields():
    from pydantic import ValidationError

    from app.contracts.v1 import TaskPackV1

    with pytest.raises(ValidationError, match="typo"):
        TaskPackV1(
            schema_version="1.0.0",
            task_id="task_step_extra",
            goal="reject weak step objects",
            steps=[{"step_id": "s1", "action": "read", "tool": "file_read", "typo": True}],
            requested_tools=["file_read"],
            declared_allowed_tools=["file_read"],
        )

    schema = TaskPackV1.model_json_schema()
    assert schema["$defs"]["TaskStepV1"]["additionalProperties"] is False
