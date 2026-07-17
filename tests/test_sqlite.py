"""Tests for SQLite database layer."""
from app.memory.database import (
    init_db,
    list_lessons_db,
    list_traces_db,
    save_core_object,
    save_lesson_db,
    save_trace,
    search_core_objects,
)


class TestSQLite:
    def test_save_and_search(self):
        init_db()
        obj = {
            "id": "test_obj_001", "object_type": "document",
            "content": "This is a B线 MVP development plan document",
            "source": "test", "metadata": {}, "created_at": "2026-01-01T00:00:00",
            "attention_score": 0.7, "route": "TASK",
        }
        save_core_object(obj)
        results = search_core_objects("MVP development", top_k=5)
        assert len(results) >= 1
        assert any(r["id"] == "test_obj_001" for r in results)

    def test_trace_roundtrip(self):
        trace = {
            "id": "trace_test_001", "task_id": "task_test_001",
            "events": [{"step": 1, "action": "test"}],
            "result": {"status": "done"}, "success": True,
            "created_at": "2026-01-01T00:00:00",
        }
        save_trace(trace)
        traces = list_traces_db(limit=500)
        assert any(t["id"] == "trace_test_001" for t in traces)

    def test_lesson_roundtrip(self):
        lesson = {
            "id": "lesson_test_001", "pattern": "test pattern",
            "lesson_type": "success",
            "future_constraint": "add more checks",
            "evidence_trace_id": "trace_test_001",
            "created_at": "2026-01-01T00:00:00",
        }
        save_lesson_db(lesson)
        lessons = list_lessons_db(limit=500)
        assert any(item["id"] == "lesson_test_001" for item in lessons)
