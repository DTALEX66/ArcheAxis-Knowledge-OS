"""Tests for learning-outcome persistence (loop gap A)."""
from __future__ import annotations

import os
import sqlite3
import textwrap
from pathlib import Path

import pytest


def _migrated_db(tmp_path: Path) -> str:
    """Create a migrated runtime DB in tmp (governance tables present)."""
    runtime = tmp_path / "runtime"
    env = os.environ.copy()
    env["COGNITIVE_DATA_DIR"] = str(runtime)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    code = textwrap.dedent(
        r"""
        import os, sqlite3, sys
        from pathlib import Path
        runtime = Path(os.environ["COGNITIVE_DATA_DIR"]).resolve()
        from shared import storage
        from app.runtime_entrypoint import run_migration
        from argparse import Namespace
        assert storage.DB_PATH.is_relative_to(runtime)
        assert run_migration(Namespace()) == 0
        conn = sqlite3.connect(storage.DB_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute(
            "INSERT INTO kb_cards (id, title, content, source_ids_json, tags_json, review_status) "
            "VALUES ('card-a', 'BKT', 'BKT 是隐马尔可夫模型', '[]', '[]', 'reviewing')"
        )
        conn.commit()
        conn.close()
        print("DBPATH:" + str(storage.DB_PATH))
        """
    )
    result = _run_py(env, code)
    path = result.strip().splitlines()[-1].split("DBPATH:", 1)[1].strip()
    assert Path(path).exists()
    return path


def _run_py(env: dict, code: str) -> str:
    import subprocess, sys
    proc = subprocess.run(
        [sys.executable, "-c", code], env=env, capture_output=True, text=True, cwd=str(Path(__file__).resolve().parents[1])
    )
    if proc.returncode != 0:
        raise AssertionError(f"setup failed: {proc.stderr}")
    return proc.stdout.strip()


def _signal_count(db: str) -> int:
    with sqlite3.connect(db) as conn:
        return conn.execute("SELECT COUNT(*) FROM mastery_signals_v1").fetchone()[0]


def _candidate_count(db: str) -> int:
    with sqlite3.connect(db) as conn:
        return conn.execute("SELECT COUNT(*) FROM machine_knowledge_candidates_v1").fetchone()[0]


def test_review_and_mistake_persisted(tmp_path):
    db = _migrated_db(tmp_path)
    from app.knowledge.learning_outcome import record_learning_outcome
    result = record_learning_outcome(
        card_id="card-a", command_id="cmd-1", quality=1, recorded_at="2026-08-18T00:00:00+00:00",
        db_path=db, mistake_detail="答错了：混淆了先验与后验",
    )
    assert result["review_id"]
    assert result["mistake_id"]
    assert result["mastery_signal"].review_count == 1
    assert result["mastery_signal"].is_mastered is False
    assert _candidate_count(db) == 0
    with sqlite3.connect(db) as conn:
        conn.row_factory = sqlite3.Row
        mistakes = conn.execute("SELECT * FROM kb_mistakes WHERE card_id='card-a'").fetchall()
        assert len(mistakes) == 1
        assert mistakes[0]["resolved"] == 0


def test_mastery_cascade_to_machine_candidate(tmp_path):
    db = _migrated_db(tmp_path)
    from app.knowledge.learning_outcome import record_learning_outcome
    for i in range(3):
        record_learning_outcome(
            card_id="card-a", command_id=f"cmd-{i}", quality=5,
            recorded_at=f"2026-08-18T00:0{i}:00+00:00", db_path=db,
        )
    assert _signal_count(db) == 3
    assert _candidate_count(db) == 1  # mastered → machine knowledge candidate


def test_validation(tmp_path):
    db = _migrated_db(tmp_path)
    from app.knowledge.learning_outcome import LearningOutcomeError, record_learning_outcome
    with pytest.raises(LearningOutcomeError, match="quality"):
        record_learning_outcome(card_id="card-a", command_id="x", quality=9,
                                recorded_at="t", db_path=db)
    with pytest.raises(LearningOutcomeError, match="card not found"):
        record_learning_outcome(card_id="missing", command_id="x", quality=3,
                                recorded_at="t", db_path=db)
