"""Gap coverage tests — fills holes in the test coverage heatmap.

Covers 10 previously untested or under-tested modules:
  shared/storage, shared/bridge, shared/logging,
  app/core/scheduler, app/core/compiler, app/agent/planner,
  app/evaluation/evaluator, app/ingestion/multi_format,
  Knowledge-Base/api, Inspiration-Research/api
"""

from __future__ import annotations

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_PROJECT_ROOT))
sys.path.insert(0, str(_PROJECT_ROOT / "Knowledge-Base"))

import pytest

# ── shared/storage ──────────────────────────────────────


class TestStorage:
    """shared/storage.py — CRUD + FTS5."""

    def test_insert_and_select(self):
        from shared.storage import insert, select_one, select_all, count

        insert("kb_documents", {
            "id": "gap_test_s1", "title": "Storage Test",
            "content": "testing insert and select",
        })
        row = select_one("kb_documents", "gap_test_s1")
        assert row is not None
        assert row["title"] == "Storage Test"

        rows = select_all("kb_documents", limit=500)
        assert any(r["id"] == "gap_test_s1" for r in rows)

        n = count("kb_documents")
        assert n >= 1

        # cleanup
        import sqlite3
        db = sqlite3.connect(str(Path(_PROJECT_ROOT) / "data" / "cognitive_os.sqlite"))
        db.execute("DELETE FROM kb_documents WHERE id=?", ("gap_test_s1",))
        db.execute("DELETE FROM kb_documents_fts WHERE id=?", ("gap_test_s1",))
        db.commit()
        db.close()

    def test_fts5_search_and_sync(self):
        from shared.storage import insert, fts5_sync, fts5_search

        insert("kb_documents", {
            "id": "gap_fts5", "title": "FTS5 Test",
            "content": "full text search with porter stemming",
        })
        fts5_sync("kb_documents", {
            "id": "gap_fts5", "title": "FTS5 Test",
            "content": "full text search with porter stemming",
        })
        results = fts5_search("kb_documents", "search stemming", top_k=5)
        assert len(results) >= 1
        assert any(r["id"] == "gap_fts5" for r in results)

        # LIKE fallback when no match
        empty = fts5_search("kb_documents", "xyznonexistent", top_k=3)
        assert isinstance(empty, list)

        # cleanup
        import sqlite3
        db = sqlite3.connect(str(Path(_PROJECT_ROOT) / "data" / "cognitive_os.sqlite"))
        db.execute("DELETE FROM kb_documents WHERE id=?", ("gap_fts5",))
        db.execute("DELETE FROM kb_documents_fts WHERE id=?", ("gap_fts5",))
        db.commit()
        db.close()

    def test_insert_json_fields(self):
        from shared.storage import insert, select_one

        insert("kb_documents", {
            "id": "gap_json", "title": "JSON Test",
            "content": "test", "tags": ["tag1", "tag2"],
        })
        row = select_one("kb_documents", "gap_json")
        assert row is not None
        assert isinstance(row.get("tags"), list)
        assert "tag1" in row.get("tags", [])

        # cleanup
        import sqlite3
        db = sqlite3.connect(str(Path(_PROJECT_ROOT) / "data" / "cognitive_os.sqlite"))
        db.execute("DELETE FROM kb_documents WHERE id=?", ("gap_json",))
        db.execute("DELETE FROM kb_documents_fts WHERE id=?", ("gap_json",))
        db.commit()
        db.close()


# ── shared/bridge ───────────────────────────────────────


class TestBridge:
    """shared/bridge.py — IR→KB bridge functions."""

    def test_bridge_intake_to_kb(self):
        from shared.bridge import bridge_intake_to_kb
        from shared.storage import select_one

        intake = {
            "id": "intake_test_1",
            "why": "Evaluate sqlite-vec for vector search",
            "risk_level": "low",
        }
        result = bridge_intake_to_kb(intake)
        assert "context_pack_id" in result
        assert "taskpack_id" in result

        # Verify both created in DB
        ctx = select_one("kb_context_packs", result["context_pack_id"])
        assert ctx is not None
        assert "vector search" in ctx.get("goal", "")

        task = select_one("kb_taskpacks", result["taskpack_id"])
        assert task is not None

        # cleanup
        import sqlite3
        db = sqlite3.connect(str(Path(_PROJECT_ROOT) / "data" / "cognitive_os.sqlite"))
        for tid in [result["context_pack_id"], result["taskpack_id"]]:
            db.execute("DELETE FROM kb_context_packs WHERE id=?", (tid,))
            db.execute("DELETE FROM kb_taskpacks WHERE id=?", (tid,))
        db.commit()
        db.close()

    def test_bridge_contract_to_kb(self):
        from shared.bridge import bridge_contract_to_kb
        from shared.storage import select_one

        contract = {"goal": "Absorb firecrawl adapter", "risk_level": "medium"}
        result = bridge_contract_to_kb(contract)
        assert "taskpack_id" in result

        task = select_one("kb_taskpacks", result["taskpack_id"])
        assert task is not None
        assert "firecrawl" in task.get("goal", "")

        # cleanup
        import sqlite3
        db = sqlite3.connect(str(Path(_PROJECT_ROOT) / "data" / "cognitive_os.sqlite"))
        db.execute("DELETE FROM kb_taskpacks WHERE id=?", (result["taskpack_id"],))
        db.commit()
        db.close()

    def test_bridge_trending_to_kb(self):
        from shared.bridge import bridge_trending_to_kb

        repos = [
            {"repo": "test/repo1", "qualifies": True, "stars": 100},
            {"repo": "test/repo2", "qualifies": False, "stars": 0},
        ]
        result = bridge_trending_to_kb(repos)
        assert result["bridged"] == 1
        assert result["items"][0]["repo"] == "test/repo1"

        # cleanup
        import sqlite3
        db = sqlite3.connect(str(Path(_PROJECT_ROOT) / "data" / "cognitive_os.sqlite"))
        for item in result["items"]:
            db.execute("DELETE FROM kb_context_packs WHERE id=?", (item["context_pack_id"],))
        db.commit()
        db.close()


# ── shared/logging ──────────────────────────────────────


class TestLogging:
    """shared/logging.py — loguru setup."""

    def test_logger_imports(self):
        from shared.logging import logger
        assert logger is not None

    def test_logger_levels(self):
        from shared.logging import logger
        # All levels should work without error
        logger.debug("gap test debug")
        logger.info("gap test info")
        logger.warning("gap test warning")
        # error would print to stderr - skip in test


# ── app/core/scheduler ──────────────────────────────────


class TestScheduler:
    """app/core/scheduler.py — APScheduler wrapper."""

    def test_list_jobs_empty(self):
        from app.core.scheduler import list_jobs
        jobs = list_jobs()
        assert isinstance(jobs, list)

    def test_is_running(self):
        from app.core.scheduler import is_running
        # Scheduler not started in test, but should not crash
        assert isinstance(is_running(), bool)


# ── app/core/compiler ───────────────────────────────────


class TestCompiler:
    """app/core/compiler.py — context→task compilation."""

    def test_compile_task(self):
        from app.core.compiler import compile_task
        from app.schemas import ContextPack

        ctx = ContextPack(
            query="Build a vector search module",
            sources=["doc_001"],
            evidence=[],
            constraints=[],
            token_budget=4000,
        )
        task = compile_task(ctx)
        assert task.goal == "Build a vector search module"
        assert len(task.steps) == 3
        assert task.risk_level == "low"


# ── app/agent/planner ───────────────────────────────────


class TestPlanner:
    """app/agent/planner.py — task step planning."""

    def test_plan_returns_steps(self):
        from app.agent.planner import plan
        from app.schemas import TaskPack

        task = TaskPack(
            goal="test",
            steps=[{"id": 1, "name": "step1"}, {"id": 2, "name": "step2"}],
            constraints=[], tools=[], risk_level="low", success_criteria=[],
        )
        steps = plan(task)
        assert len(steps) == 2
        assert steps[0]["name"] == "step1"


# ── app/evaluation ──────────────────────────────────────


class TestEvaluator:
    """app/evaluation/evaluator.py — trace evaluation."""

    def test_evaluate_success(self):
        from app.evaluation.evaluator import evaluate
        from app.schemas import ExecutionTrace

        trace = ExecutionTrace(
            task_id="t1",
            events=[{"step": 1, "result": "ok"}],
            result={"output": "done"},
            success=True,
        )
        result = evaluate(trace)
        assert result.success is True
        assert result.score == 1.0
        assert result.failure_reason == ""

    def test_evaluate_failure(self):
        from app.evaluation.evaluator import evaluate
        from app.schemas import ExecutionTrace

        trace = ExecutionTrace(
            task_id="t2",
            events=[{"step": 1, "error": "fail"}],
            result={},
            success=False,
        )
        result = evaluate(trace)
        assert result.success is False
        assert result.score == 0.0
        assert "failed" in result.failure_reason


# ── app/ingestion/multi_format ──────────────────────────


class TestMultiFormat:
    """app/ingestion/multi_format.py — file/URL conversion."""

    def test_convert_markdown_file(self):
        import tempfile, os
        from app.ingestion.multi_format import convert_file

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False, encoding="utf-8"
        ) as f:
            f.write("# Test Heading\n\nThis is a test markdown file.")
            tmp_path = f.name

        try:
            content, engine = convert_file(tmp_path, "md")
            assert "Test Heading" in content
            assert "test markdown" in content
            assert engine in ("markitdown", "passthrough")
        finally:
            os.unlink(tmp_path)

    def test_convert_txt_passthrough(self):
        import tempfile, os
        from app.ingestion.multi_format import convert_file

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as f:
            f.write("plain text content")
            tmp_path = f.name

        try:
            content, engine = convert_file(tmp_path, "txt")
            assert "plain text" in content
            assert engine == "passthrough"
        finally:
            os.unlink(tmp_path)

    def test_convert_nonexistent_file(self):
        import pytest
        from app.ingestion.multi_format import convert_file

        with pytest.raises(RuntimeError):
            convert_file("/nonexistent/path/file.pdf", "pdf")


# ── Knowledge-Base/api ──────────────────────────────────


def _get_kb_app():
    """Load Knowledge-Base FastAPI app (directory name has a hyphen)."""
    import importlib.util

    kb_api_path = Path(_PROJECT_ROOT) / "Knowledge-Base" / "api.py"
    spec = importlib.util.spec_from_file_location("kb_api", kb_api_path)
    mod = importlib.util.module_from_spec(spec)
    # Ensure the module can find its own imports
    kb_dir = str(Path(_PROJECT_ROOT) / "Knowledge-Base")
    if kb_dir not in sys.path:
        sys.path.insert(0, kb_dir)
    if str(_PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(_PROJECT_ROOT))
    spec.loader.exec_module(mod)
    return mod.app


class TestKBApi:
    """Knowledge-Base/api.py — endpoint integration tests."""

    def test_health_endpoint(self):
        from fastapi.testclient import TestClient

        app = _get_kb_app()
        client = TestClient(app)
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_create_and_search_document(self):
        from fastapi.testclient import TestClient

        app = _get_kb_app()
        client = TestClient(app)
        # Create
        resp = client.post("/documents", json={
            "title": "Gap Test Doc", "content": "test content for coverage gap",
            "source": "test",
        })
        assert resp.status_code == 200
        doc_id = resp.json()["id"]

        # Search (hybrid)
        resp2 = client.post("/search", json={
            "query": "coverage gap", "top_k": 5, "mode": "hybrid",
        })
        assert resp2.status_code == 200
        assert resp2.json()["count"] >= 0

        # Vector search
        resp3 = client.post("/search", json={
            "query": "test content", "mode": "vector",
        })
        assert resp3.status_code == 200

        # Keyword search
        resp4 = client.post("/search", json={
            "query": "test", "mode": "keyword",
        })
        assert resp4.status_code == 200

        # Search stats
        resp5 = client.get("/search/stats")
        assert resp5.status_code == 200
        assert "documents_indexed" in resp5.json()

        # Cleanup
        import sqlite3
        db = sqlite3.connect(str(Path(_PROJECT_ROOT) / "data" / "cognitive_os.sqlite"))
        db.execute("DELETE FROM kb_documents WHERE id=?", (doc_id,))
        db.execute("DELETE FROM kb_documents_fts WHERE id=?", (doc_id,))
        db.commit()
        db.close()

    def test_review_and_mistake_flow(self):
        from fastapi.testclient import TestClient

        app = _get_kb_app()
        client = TestClient(app)

        # Create card
        resp = client.post("/cards", json={
            "title": "Review Test Card", "content": "test review flow",
        })
        assert resp.status_code == 200
        card = resp.json()
        card_id = card.get("card_id") or card.get("id")

        # Record review
        resp2 = client.post("/reviews", json={
            "card_id": card_id, "quality": 4,
        })
        assert resp2.status_code == 200
        assert "next_review_at" in resp2.json()

        # Due reviews
        resp3 = client.get("/reviews/due?limit=5")
        assert resp3.status_code == 200

        # Review history
        resp4 = client.get(f"/reviews/history/{card_id}")
        assert resp4.status_code == 200

        # Mistakes
        resp5 = client.get("/mistakes?limit=5")
        assert resp5.status_code == 200

        resp6 = client.get("/mistakes/patterns")
        assert resp6.status_code == 200
        assert "total_mistakes" in resp6.json()

        # Cleanup
        import sqlite3
        db = sqlite3.connect(str(Path(_PROJECT_ROOT) / "data" / "cognitive_os.sqlite"))
        db.execute("DELETE FROM kb_cards WHERE id=?", (card_id,))
        db.execute("DELETE FROM kb_cards_fts WHERE id=?", (card_id,))
        db.execute("DELETE FROM kb_reviews WHERE card_id=?", (card_id,))
        db.commit()
        db.close()

    def test_a_to_b_flow(self):
        from fastapi.testclient import TestClient

        app = _get_kb_app()
        client = TestClient(app)
        resp = client.get("/a-to-b/candidates?limit=5")
        assert resp.status_code == 200

        resp2 = client.get("/a-to-b/pending")
        assert resp2.status_code == 200

    def test_machine_knowledge_flow(self):
        from fastapi.testclient import TestClient

        app = _get_kb_app()
        client = TestClient(app)
        # Create
        resp = client.post("/machine-knowledge", json={
            "title": "Gap Test MKU", "content": "test machine knowledge",
            "unit_type": "rule",
        })
        assert resp.status_code == 200
        unit_id = resp.json()["id"]

        # Get
        resp2 = client.get(f"/machine-knowledge/{unit_id}")
        assert resp2.status_code == 200
        assert resp2.json()["title"] == "Gap Test MKU"

        # List
        resp3 = client.get("/machine-knowledge")
        assert resp3.status_code == 200
        assert "stats" in resp3.json()

        # Search
        resp4 = client.get("/machine-knowledge/search?q=test")
        assert resp4.status_code == 200

        # Deactivate
        resp5 = client.post(f"/machine-knowledge/{unit_id}/deactivate")
        assert resp5.status_code == 200

        # Cleanup
        import sqlite3
        db = sqlite3.connect(str(Path(_PROJECT_ROOT) / "data" / "cognitive_os.sqlite"))
        db.execute("DELETE FROM machine_knowledge_units WHERE id=?", (unit_id,))
        db.commit()
        db.close()


# ── Inspiration-Research/api ────────────────────────────


def _get_ir_app():
    """Load Inspiration-Research FastAPI app (directory name has a hyphen)."""
    import importlib.util

    ir_api_path = Path(_PROJECT_ROOT) / "Inspiration-Research" / "api.py"
    spec = importlib.util.spec_from_file_location("ir_api", ir_api_path)
    mod = importlib.util.module_from_spec(spec)
    ir_dir = str(Path(_PROJECT_ROOT) / "Inspiration-Research")
    if ir_dir not in sys.path:
        sys.path.insert(0, ir_dir)
    if str(_PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(_PROJECT_ROOT))
    spec.loader.exec_module(mod)
    return mod.app


class TestIRApi:
    """Inspiration-Research/api.py — health check."""

    def test_ir_health(self):
        from fastapi.testclient import TestClient

        app = _get_ir_app()
        client = TestClient(app)
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
