"""P0 security regressions for the learner-state API."""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from fastapi import HTTPException

from app.api import learning


@pytest.mark.parametrize(
    "forbidden",
    [
        {"human": {"teaching_evidence": True}},
        {"machine": {"verified": True, "transferable": True}},
        {"evidence_verified": True},
        {"has_superseding": True},
        {"has_contradiction": True},
    ],
)
def test_tick_rejects_client_asserted_truth_fields(forbidden: dict[str, object]):
    payload: dict[str, object] = {
        "node_id": "card-a",
        "learner_id": "learner-a",
        "action_intent": "evaluate",
        "idempotency_key": "intent-1",
    }
    payload.update(forbidden)
    with pytest.raises(HTTPException) as exc:
        learning.learning_tick(payload)
    assert exc.value.status_code == 400
    assert "server-derived" in str(exc.value.detail)


def test_tick_accepts_only_intent_and_fails_closed_without_receipts():
    result = learning.learning_tick(
        {
            "node_id": "card-a",
            "learner_id": "learner-a",
            "action_intent": "evaluate",
            "idempotency_key": "intent-1",
        }
    )
    assert result["action"] == "review_evidence"


def test_get_mastery_reads_sqlite_row_without_mapping_get(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    db = tmp_path / "mastery.sqlite"
    with sqlite3.connect(db) as conn:
        conn.executescript(
            """
            CREATE TABLE kb_cards (
                id TEXT PRIMARY KEY,
                review_status TEXT,
                stability_days REAL,
                bkt_mastery REAL
            );
            CREATE TABLE kb_reviews (
                id TEXT PRIMARY KEY,
                card_id TEXT,
                quality INTEGER,
                ease_factor REAL,
                created_at TEXT
            );
            CREATE TABLE kb_mistakes (
                id TEXT PRIMARY KEY,
                card_id TEXT,
                resolved INTEGER,
                created_at TEXT
            );
            INSERT INTO kb_cards VALUES ('card-a', 'reviewing', 3.0, 0.4);
            """
        )
    monkeypatch.setattr(learning, "_db_path", lambda: db)

    result = learning.get_mastery("card-a")

    assert result["card_id"] == "card-a"
    assert result["state"]["evidence"] == "unverified"
    assert result["state"]["machine"]["level"] == "K2"
