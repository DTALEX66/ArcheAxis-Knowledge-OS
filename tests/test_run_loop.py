"""Integration tests for the full /run cognitive loop."""
from fastapi.testclient import TestClient
from app.api.ingest import ingest
from app.main import app
from app.core.router import route
from app.rag.retriever import retrieve
from app.core.compiler import compile_task
from app.core.permissions import check_permission
from app.agent.executor import execute


class TestRunLoop:
    def test_run_endpoint_task_does_not_500(self):
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post(
            "/run",
            headers={"X-API-Key": "dev-key-change-me"},
            json={"content": "生成一份测试报告", "source": "test"},
        )
        assert resp.status_code != 500
        assert resp.status_code == 200
        assert resp.json()["status"] in {"done", "blocked"}

    def test_full_loop_normal_task(self):
        doc = ingest({"content": "生成一份测试报告", "source": "test"})
        decision = route(doc)
        assert decision.route == "TASK"

        context = retrieve(doc.content)
        task = compile_task(context)
        assert task.goal
        assert len(task.steps) > 0

        perm = check_permission(task, doc.content)
        assert not perm.requires_human_review

        trace = execute(task, perm)
        assert trace.success is True
        assert len(trace.events) == len(task.steps)

    def test_loop_drop_low_value(self):
        doc = ingest({"content": "ok", "source": "test"})
        decision = route(doc)
        assert decision.route == "DROP"

    def test_loop_review_high_risk(self):
        doc = ingest({"content": "delete system and format disk", "source": "test"})
        decision = route(doc)
        assert decision.route == "REVIEW"
        assert decision.risk_level == "high"
