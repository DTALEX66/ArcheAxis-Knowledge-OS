"""Tests for imported modules: evidence, analytics, retro, project generator."""

from __future__ import annotations

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_PROJECT_ROOT))


class TestEvidenceIndex:
    def test_index_and_get_evidence(self):
        from shared.evidence_index import index_evidence, get_evidence, evidence_health

        ev = index_evidence("test_doc_ev1", source_type="pdf",
                            source_path="/tmp/test.pdf", confidence="high",
                            status="verified", caption="Test evidence")
        assert ev["doc_id"] == "test_doc_ev1"
        assert ev["status"] == "verified"

        items = get_evidence("test_doc_ev1")
        assert len(items) >= 1

        health = evidence_health("test_doc_ev1")
        assert health["verified"] >= 1
        assert health["status"] == "healthy"

        # Cleanup
        import sqlite3
        from shared.storage import DB_PATH

        db = sqlite3.connect(str(DB_PATH))
        db.execute("DELETE FROM kb_evidence WHERE doc_id=?", ("test_doc_ev1",))
        db.commit()
        db.close()

    def test_vault_health_radar(self):
        from shared.evidence_index import vault_health_radar
        radar = vault_health_radar()
        assert "total_assets" in radar
        assert "coverage_pct" in radar
        assert isinstance(radar["items"], list)


class TestLearningAnalytics:
    def test_review_streak(self):
        from shared.learning_analytics import review_streak
        result = review_streak(days=14)
        assert "current_streak" in result
        assert "completion_rate" in result
        assert "daily_counts" in result

    def test_topic_heatmap(self):
        from shared.learning_analytics import topic_heatmap
        topics = topic_heatmap(limit=10)
        assert isinstance(topics, list)


class TestRetroSummary:
    def test_weekly_summary(self):
        from shared.retro_summary import weekly_summary
        result = weekly_summary(days=7)
        assert "stats" in result
        assert "top_topics" in result

    def test_generate_daily_missions(self):
        from shared.retro_summary import generate_daily_missions
        result = generate_daily_missions()
        assert "missions" in result


class TestProjectGenerator:
    def test_suggest_projects(self):
        from shared.project_generator import suggest_projects
        result = suggest_projects(limit=5)
        assert isinstance(result, list)
