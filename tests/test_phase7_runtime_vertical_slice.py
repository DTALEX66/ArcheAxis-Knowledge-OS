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
    assert "ArcheAxis Workspace (Human–AI Learning Workspace)" in evidence["content"]
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


def test_search_knowledge_goal_returns_real_kb_evidence_and_trace_bound_lesson(
    monkeypatch, tmp_path
):
    import sqlite3
    from contextlib import closing

    import app.main as main_module
    from app.agent.planner import plan_goal
    from app.evaluation.evaluator import evaluate
    from app.facades import runtime as runtime_module
    from knowledge_base.search import vector_search
    from shared import storage
    from shared.migration_runner import MigrationOperator

    database = tmp_path / "runtime-kb-search.sqlite"
    monkeypatch.setattr(storage, "DB_PATH", database)
    with closing(sqlite3.connect(database)):
        pass
    MigrationOperator(db_path=database, backup_dir=tmp_path / "backups").apply(
        "core.sqlite"
    )
    storage.insert(
        "kb_documents",
        {
            "id": "doc-runtime-evidence",
            "title": "Governed runtime evidence",
            "content": "Attributable evidence keeps runtime completion truthful.",
            "source": "phase7-test",
            "tags": ["runtime", "evidence"],
        },
    )
    monkeypatch.setattr(vector_search, "search_all", lambda query, top_k=5: [])

    persisted_traces = []
    persisted_lessons = []
    monkeypatch.setattr(main_module, "save_memory", lambda document: None)
    monkeypatch.setattr(
        main_module,
        "retrieve",
        lambda query: ContextPack(query=query, summary="phase 7 KB search context"),
    )
    monkeypatch.setattr(main_module, "save_lesson", persisted_lessons.append)
    monkeypatch.setattr(runtime_module, "log_trace", persisted_traces.append)

    response = main_module.run(
        {"content": "search knowledge: attributable evidence", "source": "phase7-test"}
    )

    assert response["status"] == "done"
    assert response["task"].tools == ["kb_search"]
    assert response["permission"]["allowed_tools"] == ["kb_search"]
    trace = response["trace"]
    evidence = trace.events[0]["result"]
    assert evidence["tool"] == "kb_search"
    assert evidence["status"] == "ok"
    assert evidence["dry_run"] is False
    assert evidence["count"] == 1
    assert evidence["items"][0]["id"] == "doc-runtime-evidence"
    assert response["eval"].success is True
    assert response["lesson"].lesson_type == "success"
    assert response["lesson"].evidence_trace_id == trace.id
    assert persisted_traces == [trace]
    assert persisted_lessons == [response["lesson"]]

    assert plan_goal("search knowledge:") == []
    fabricated_trace = ExecutionTrace(
        task_id="fake-kb-search",
        events=[
            {
                "step": {"tool": "kb_search"},
                "result": {"tool": "kb_search", "status": "ok", "dry_run": False},
            }
        ],
        result={"status": "done"},
        success=True,
    )
    fabricated_evaluation = evaluate(fabricated_trace)
    assert fabricated_evaluation.success is False
    assert "missing_kb_search_evidence" in fabricated_evaluation.failure_reason
