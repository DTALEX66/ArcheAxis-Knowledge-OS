from __future__ import annotations

import app.schemas as runtime_schemas

_APPROVED = [
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

    assert contracts.__all__ == _APPROVED
    for name in _APPROVED:
        assert getattr(contracts, name) is getattr(runtime_schemas, name)


def test_contracts_facade_does_not_publish_phase_two_surface():
    from app.facades import contracts

    deferred = {
        "VERSION",
        "SCHEMA_VERSION",
        "CanonicalTaskPack",
        "TaskPackV1",
        "load_schema",
        "validate_contract",
        "to_canonical",
        "from_legacy",
    }
    assert deferred.isdisjoint(vars(contracts))
