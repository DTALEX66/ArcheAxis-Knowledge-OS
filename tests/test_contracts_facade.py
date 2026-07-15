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


def test_contracts_facade_publishes_completed_phase_two_surfaces():
    from app.adapters.claim import bind_legacy_evidence, verify_with_legacy_evidence
    from app.adapters.evidence import from_match_result, to_legacy_verification_evidence
    from app.adapters.execution_trace import (
        from_runtime_trace,
        from_trace_row,
        to_runtime_trace,
        to_trace_row,
    )
    from app.adapters.source_record import from_kb_document_row, to_kb_document_row
    from app.adapters.taskpack import (
        RuntimeTaskProjection,
        from_knowledge_taskpack,
        project_to_runtime,
        to_knowledge_taskpack,
    )
    from app.contracts.v1 import (
        CONTRACT_VERSION,
        ClaimV1,
        EvidenceV1,
        ExecutionTraceV1,
        SourceRecordV1,
        TaskPackV1,
        TaskStepV1,
    )
    from app.facades import contracts

    assert contracts.CONTRACT_VERSION == CONTRACT_VERSION
    assert contracts.TaskPackV1 is TaskPackV1
    assert contracts.TaskStepV1 is TaskStepV1
    assert contracts.RuntimeTaskProjection is RuntimeTaskProjection
    assert contracts.from_knowledge_taskpack is from_knowledge_taskpack
    assert contracts.to_knowledge_taskpack is to_knowledge_taskpack
    assert contracts.project_to_runtime is project_to_runtime
    assert contracts.ExecutionTraceV1 is ExecutionTraceV1
    assert contracts.from_runtime_trace is from_runtime_trace
    assert contracts.to_runtime_trace is to_runtime_trace
    assert contracts.from_trace_row is from_trace_row
    assert contracts.to_trace_row is to_trace_row
    assert contracts.SourceRecordV1 is SourceRecordV1
    assert contracts.from_kb_document_row is from_kb_document_row
    assert contracts.to_kb_document_row is to_kb_document_row
    assert contracts.ClaimV1 is ClaimV1
    assert contracts.bind_legacy_evidence is bind_legacy_evidence
    assert contracts.verify_with_legacy_evidence is verify_with_legacy_evidence
    assert contracts.EvidenceV1 is EvidenceV1
    assert contracts.from_match_result is from_match_result
    assert contracts.to_legacy_verification_evidence is to_legacy_verification_evidence

    deferred = {
        "ContextPackV1",
        "validate_contract",
    }
    assert deferred.isdisjoint(vars(contracts))
