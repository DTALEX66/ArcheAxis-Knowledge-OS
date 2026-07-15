from __future__ import annotations

from app.schemas import ContextPack, ExecutionTrace


def test_read_file_goal_produces_real_evidence_and_trace_bound_success_lesson(monkeypatch):
    import app.main as main_module
    from app.evaluation.evaluator import evaluate
    from app.facades import runtime as runtime_module

    persisted_traces = []
    persisted_lessons = []
    monkeypatch.setattr(main_module, "save_memory", lambda document: None)
    monkeypatch.setattr(
        main_module,
        "retrieve",
        lambda query: ContextPack(query=query, summary="phase 7 tracer context"),
    )
    monkeypatch.setattr(main_module, "save_lesson", persisted_lessons.append)
    monkeypatch.setattr(runtime_module, "log_trace", persisted_traces.append)

    response = main_module.run({"content": "read file: AGENTS.md", "source": "phase7-test"})

    assert response["status"] == "done"
    assert response["task"].goal == "read file: AGENTS.md"
    assert response["task"].tools == ["file_read"]
    assert response["task"].steps == [
        {
            "id": 1,
            "name": "read_file",
            "type": "tool",
            "tool": "file_read",
            "path": "AGENTS.md",
            "dry_run": False,
        }
    ]
    assert response["permission"]["allowed_tools"] == ["file_read"]
    assert response["permission"]["requires_human_review"] is False

    trace = response["trace"]
    evidence = trace.events[0]["result"]
    assert trace.success is True
    assert evidence["tool"] == "file_read"
    assert evidence["status"] == "ok"
    assert evidence["dry_run"] is False
    assert evidence["path"].endswith("AGENTS.md")
    assert "Cognitive-OS Agent Operating Guide" in evidence["content"]
    assert response["eval"].success is True
    assert response["eval"].score == 1.0
    assert response["lesson"].lesson_type == "success"
    assert response["lesson"].evidence_trace_id == trace.id
    assert persisted_traces == [trace]
    assert persisted_lessons == [response["lesson"]]

    for tool, result in [
        ("echo", {"tool": "echo", "status": "ok", "dry_run": False, "message": "executed"}),
        ("noop", {"tool": "noop", "status": "ok", "dry_run": False}),
        (
            "file_read",
            {
                "tool": "file_read",
                "status": "ok",
                "dry_run": True,
                "path": "AGENTS.md",
                "preview": "dry-run read only",
            },
        ),
    ]:
        fake_trace = ExecutionTrace(
            task_id=f"fake-{tool}",
            events=[{"step": {"tool": tool}, "result": result}],
            result={"status": "done", "outputs": [result]},
            success=True,
        )
        fake_eval = evaluate(fake_trace)
        assert fake_eval.success is False
        assert fake_eval.score < 1.0
        assert "evidence" in fake_eval.failure_reason
