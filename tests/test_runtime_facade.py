from __future__ import annotations

from app.schemas import CoreObject, TaskPack


def _echo_task() -> TaskPack:
    return TaskPack(
        id="task_facade_contract",
        goal="Verify the runtime facade",
        steps=[{"id": 1, "name": "contract_probe", "tool": "echo"}],
        tools=["echo"],
    )


def test_runtime_facade_routes_permissions_executes_and_traces(monkeypatch):
    from app.facades import runtime as runtime_module

    persisted = []
    monkeypatch.setattr(runtime_module, "log_trace", persisted.append)

    result = runtime_module.execute_runtime(
        CoreObject(content="Please execute this task and produce a result."),
        _echo_task(),
    )

    assert result.route.route == "TASK"
    assert result.permission.task_id == "task_facade_contract"
    assert result.permission.requires_human_review is False
    assert result.permission.allowed_tools == ["echo"]
    assert result.trace.task_id == "task_facade_contract"
    assert result.trace.success is True
    assert result.trace.events[0]["result"]["tool"] == "echo"
    assert result.trace.events[0]["result"]["status"] == "ok"
    assert persisted == [result.trace]


def test_runtime_facade_stops_before_execution_when_review_is_required(monkeypatch):
    from app.facades import runtime as runtime_module

    def fail_if_called(trace):
        raise AssertionError("blocked execution must not persist a trace")

    monkeypatch.setattr(runtime_module, "log_trace", fail_if_called)
    task = TaskPack(
        id="task_facade_blocked",
        goal="Preview risky code",
        steps=[{"id": 1, "name": "risky_probe", "tool": "code_exec"}],
        tools=["code_exec"],
    )

    result = runtime_module.execute_runtime(
        CoreObject(content="Please execute this task and produce a result."),
        task,
    )

    assert result.route.route == "TASK"
    assert result.permission.requires_human_review is True
    assert result.permission.blocked_tools == ["code_exec"]
    assert result.trace is None


def test_legacy_run_reuses_comparable_runtime_contract(monkeypatch):
    import app.main as main_module
    from app.api.ingest import ingest
    from app.core.compiler import compile_task
    from app.facades import runtime as runtime_module
    from app.schemas import ContextPack

    payload = {"content": "Please execute this task and produce a result.", "source": "contract"}
    context = ContextPack(query=payload["content"], summary="isolated contract context")

    monkeypatch.setattr(main_module, "save_memory", lambda document: None)
    monkeypatch.setattr(main_module, "retrieve", lambda query: context)
    monkeypatch.setattr(main_module, "save_lesson", lambda lesson: None)
    monkeypatch.setattr(runtime_module, "log_trace", lambda trace: None)

    direct = runtime_module.execute_runtime(ingest(payload), compile_task(context))
    legacy = main_module.run(payload)

    assert legacy["route"].model_dump() == direct.route.model_dump()
    assert legacy["permission"]["risk_level"] == direct.permission.risk_level
    assert legacy["permission"]["allowed_tools"] == direct.permission.allowed_tools
    assert legacy["trace"].success == direct.trace.success
    assert [event["result"]["tool"] for event in legacy["trace"].events] == [
        event["result"]["tool"] for event in direct.trace.events
    ]
