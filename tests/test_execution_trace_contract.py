from __future__ import annotations

import pytest

from app.schemas import ExecutionTrace


def test_runtime_execution_trace_roundtrips_losslessly_through_v1():
    from app.adapters.execution_trace import from_runtime_trace, to_runtime_trace
    from app.contracts.v1 import CONTRACT_VERSION, ExecutionTraceV1

    legacy = ExecutionTrace(
        id="trace_runtime_001",
        task_id="task_runtime_001",
        events=[
            {
                "step": {"step_id": "collect", "tool": "http", "action": "collect"},
                "result": {
                    "status": "blocked",
                    "risk_level": "high",
                    "evidence_id": "evidence_001",
                },
            }
        ],
        result={"status": "completed_with_errors", "outputs": [{"status": "blocked"}]},
        success=False,
        created_at="2026-07-15T00:00:00+00:00",
    )

    canonical = from_runtime_trace(legacy)

    assert isinstance(canonical, ExecutionTraceV1)
    assert canonical.schema_version == CONTRACT_VERSION
    assert canonical.trace_id == legacy.id
    assert to_runtime_trace(canonical).model_dump() == legacy.model_dump()


def test_runtime_to_canonical_trace_does_not_share_nested_mutable_state():
    from app.adapters.execution_trace import from_runtime_trace

    runtime = ExecutionTrace(
        id="trace_isolation_runtime",
        events=[{"result": {"evidence": ["original"]}}],
        result={"outputs": [{"status": "original"}]},
    )

    canonical = from_runtime_trace(runtime)
    canonical.events[0]["result"]["evidence"].append("canonical-only")
    canonical.result["outputs"][0]["status"] = "canonical-only"

    assert runtime.events == [{"result": {"evidence": ["original"]}}]
    assert runtime.result == {"outputs": [{"status": "original"}]}


def test_canonical_to_runtime_trace_does_not_share_nested_mutable_state():
    from app.adapters.execution_trace import to_runtime_trace
    from app.contracts.v1 import CONTRACT_VERSION, ExecutionTraceV1

    canonical = ExecutionTraceV1(
        schema_version=CONTRACT_VERSION,
        trace_id="trace_isolation_canonical",
        events=[{"result": {"evidence": ["original"]}}],
        result={"outputs": [{"status": "original"}]},
        created_at="2026-07-15T00:00:00+00:00",
    )

    runtime = to_runtime_trace(canonical)
    runtime.events[0]["result"]["evidence"].append("runtime-only")
    runtime.result["outputs"][0]["status"] = "runtime-only"

    assert canonical.events == [{"result": {"evidence": ["original"]}}]
    assert canonical.result == {"outputs": [{"status": "original"}]}


def test_sqlite_trace_row_roundtrips_losslessly_through_v1():
    from app.adapters.execution_trace import from_trace_row, to_trace_row

    row = {
        "id": "trace_row_001",
        "task_id": "task_row_001",
        "events": [{"step": {"tool": "search"}, "result": {"status": "ok"}}],
        "result": {"status": "done", "outputs": [{"status": "ok"}]},
        "success": True,
        "created_at": "2026-07-15T00:01:00+00:00",
    }

    assert to_trace_row(from_trace_row(row)) == row


def test_sqlite_row_to_canonical_trace_does_not_share_nested_mutable_state():
    from app.adapters.execution_trace import from_trace_row

    row = {
        "id": "trace_row_isolation",
        "task_id": None,
        "events": [{"result": {"evidence": ["original"]}}],
        "result": {"outputs": [{"status": "original"}]},
        "success": None,
        "created_at": "2026-07-15T00:01:00+00:00",
    }

    canonical = from_trace_row(row)
    canonical.events[0]["result"]["evidence"].append("canonical-only")
    canonical.result["outputs"][0]["status"] = "canonical-only"

    assert row["events"] == [{"result": {"evidence": ["original"]}}]
    assert row["result"] == {"outputs": [{"status": "original"}]}


def test_canonical_to_sqlite_row_does_not_share_nested_mutable_state():
    from app.adapters.execution_trace import to_trace_row
    from app.contracts.v1 import CONTRACT_VERSION, ExecutionTraceV1

    canonical = ExecutionTraceV1(
        schema_version=CONTRACT_VERSION,
        trace_id="trace_row_isolation_canonical",
        events=[{"result": {"evidence": ["original"]}}],
        result={"outputs": [{"status": "original"}]},
        created_at="2026-07-15T00:01:00+00:00",
    )

    row = to_trace_row(canonical)
    row["events"][0]["result"]["evidence"].append("row-only")
    row["result"]["outputs"][0]["status"] = "row-only"

    assert canonical.events == [{"result": {"evidence": ["original"]}}]
    assert canonical.result == {"outputs": [{"status": "original"}]}


def test_sqlite_trace_row_rejects_unmapped_columns():
    from app.adapters.execution_trace import from_trace_row
    from app.adapters.taskpack import ContractMappingError

    row = {
        "id": "trace_row_002",
        "task_id": "task_row_002",
        "events": [],
        "result": {},
        "success": None,
        "created_at": "2026-07-15T00:02:00+00:00",
        "risk_events": [{"kind": "policy"}],
    }

    with pytest.raises(ContractMappingError, match="unmapped fields: risk_events"):
        from_trace_row(row)


def test_execution_trace_v1_crosses_the_real_sqlite_row_boundary(tmp_path, monkeypatch):
    from app.adapters.execution_trace import from_trace_row, to_trace_row
    from app.contracts.v1 import CONTRACT_VERSION, ExecutionTraceV1
    from app.memory import database

    monkeypatch.setattr(database, "DB_PATH", tmp_path / "trace-contract.sqlite")
    database.init_db()
    canonical = ExecutionTraceV1(
        schema_version=CONTRACT_VERSION,
        trace_id="trace_sqlite_001",
        task_id="task_sqlite_001",
        events=[{"step": {"tool": "search"}, "result": {"status": "ok"}}],
        result={"status": "done"},
        success=True,
        created_at="2026-07-15T00:03:00+00:00",
    )

    database.save_trace(to_trace_row(canonical))
    persisted = next(
        row for row in database.list_traces_db() if row["id"] == canonical.trace_id
    )

    assert from_trace_row(persisted) == canonical


def test_execution_trace_v1_rejects_corrupt_success_from_real_sqlite(tmp_path, monkeypatch):
    from app.adapters.execution_trace import from_trace_row
    from app.adapters.taskpack import ContractMappingError
    from app.memory import database

    monkeypatch.setattr(database, "DB_PATH", tmp_path / "trace-contract-corrupt.sqlite")
    database.init_db()
    connection = database._get_conn()
    try:
        connection.execute(
            "INSERT INTO execution_traces VALUES (?,?,?,?,?,?)",
            ("trace_corrupt", None, "[]", "{}", 2, "2026-07-15T00:04:00+00:00"),
        )
        connection.commit()
    finally:
        connection.close()

    persisted = next(
        row for row in database.list_traces_db() if row["id"] == "trace_corrupt"
    )

    with pytest.raises(ContractMappingError, match="success must be 0, 1, or null"):
        from_trace_row(persisted)
