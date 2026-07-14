from __future__ import annotations

import app.schemas as runtime_schemas

_RUNTIME_EXPORTS = [
    "AttentionDecision",
    "ContextPack",
    "CoreObject",
    "EvalResult",
    "ExecutionTrace",
    "MachineLesson",
    "PermissionDecision",
    "TaskPack",
]


def test_contracts_facade_reexports_runtime_objects_by_identity():
    from app.facades import contracts

    assert set(_RUNTIME_EXPORTS).issubset(contracts.__all__)
    for name in _RUNTIME_EXPORTS:
        assert getattr(contracts, name) is getattr(runtime_schemas, name)


def test_contracts_facade_publishes_only_completed_phase_two_taskpack_surface():
    from app.adapters.taskpack import (
        RuntimeTaskProjection,
        from_knowledge_taskpack,
        project_to_runtime,
        to_knowledge_taskpack,
    )
    from app.contracts.v1 import CONTRACT_VERSION, TaskPackV1, TaskStepV1
    from app.facades import contracts

    assert contracts.CONTRACT_VERSION == CONTRACT_VERSION
    assert contracts.TaskPackV1 is TaskPackV1
    assert contracts.TaskStepV1 is TaskStepV1
    assert contracts.RuntimeTaskProjection is RuntimeTaskProjection
    assert contracts.from_knowledge_taskpack is from_knowledge_taskpack
    assert contracts.to_knowledge_taskpack is to_knowledge_taskpack
    assert contracts.project_to_runtime is project_to_runtime

    deferred = {
        "ContextPackV1",
        "ExecutionTraceV1",
        "EvaluationV1",
        "LessonV1",
        "SourceRecordV1",
        "validate_contract",
    }
    assert deferred.isdisjoint(vars(contracts))
