from __future__ import annotations

import sqlite3
from contextlib import closing


def test_mastery_signal_projection_preserves_card_review_and_mistake_history(tmp_path):
    from app.knowledge.mastery import persist_mastery_signal
    from shared.migration_runner import MigrationOperator

    database = tmp_path / "mastery.sqlite"
    with closing(sqlite3.connect(database)):
        pass
    MigrationOperator(db_path=database, backup_dir=tmp_path / "backups").apply("core.sqlite")
    with closing(sqlite3.connect(database)) as connection:
        connection.execute(
            "INSERT INTO kb_cards(id, title, content, review_status) VALUES ('card-1', 'Claim', 'Evidence', 'reviewing')"
        )
        for index in range(3):
            connection.execute(
                "INSERT INTO kb_reviews(id, card_id, quality, interval_days, ease_factor, next_review_at, created_at) VALUES (?, 'card-1', 5, 1, 2.5, '2026-08-01T00:00:00Z', ?)",
                (f"review-{index}", f"2026-07-20T16:0{index}:00Z"),
            )
        connection.execute(
            "INSERT INTO kb_mistakes(id, card_id, resolved, created_at) VALUES ('mistake-1', 'card-1', 0, '2026-07-20T16:03:00Z')"
        )
        connection.commit()
        source_before = connection.execute(
            "SELECT review_status FROM kb_cards WHERE id='card-1'"
        ).fetchone(), connection.execute("SELECT COUNT(*) FROM kb_reviews").fetchone()

    blocked = persist_mastery_signal("card-1", db_path=database, calculated_at="2026-07-20T16:04:00Z")
    assert blocked.is_mastered is False
    assert blocked.unresolved_mistake_ids == ["mistake-1"]

    with closing(sqlite3.connect(database)) as connection:
        connection.execute("UPDATE kb_mistakes SET resolved=1 WHERE id='mistake-1'")
        connection.commit()
    mastered = persist_mastery_signal("card-1", db_path=database, calculated_at="2026-07-20T16:05:00Z")
    assert mastered.is_mastered is True

    with closing(sqlite3.connect(database)) as connection:
        source_after = connection.execute(
            "SELECT review_status FROM kb_cards WHERE id='card-1'"
        ).fetchone(), connection.execute("SELECT COUNT(*) FROM kb_reviews").fetchone()
        signal_rows = connection.execute("SELECT COUNT(*) FROM mastery_signals_v1").fetchone()[0]
    assert source_after == source_before
    assert signal_rows == 2
