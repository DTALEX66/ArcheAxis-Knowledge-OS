"""Append-only mastery signal projection from immutable learning snapshots."""
from __future__ import annotations

import sqlite3
from hashlib import sha256
from pathlib import Path

from app.adapters.mastery_signal import from_learning_snapshots
from app.contracts.v1 import MasterySignalV1
from shared import core_schema


def persist_mastery_signal_on_connection(
    connection: sqlite3.Connection, card_id: str, *, calculated_at: str
) -> tuple[MasterySignalV1, str]:
    """Write one signal without committing the caller-owned transaction."""
    core_schema.validate(connection)
    card = connection.execute("SELECT * FROM kb_cards WHERE id=?", (card_id,)).fetchone()
    if card is None:
        raise ValueError("mastery signal requires an existing card")
    reviews = connection.execute(
        "SELECT * FROM kb_reviews WHERE card_id=? ORDER BY created_at, id", (card_id,)
    ).fetchall()
    mistakes = connection.execute(
        "SELECT * FROM kb_mistakes WHERE card_id=? ORDER BY created_at, id", (card_id,)
    ).fetchall()
    signal = from_learning_snapshots(
        dict(card), [dict(item) for item in reviews], [dict(item) for item in mistakes]
    )
    snapshot_id = "mastery_" + sha256(
        f"{card_id}:{calculated_at}:{signal.model_dump_json()}".encode()
    ).hexdigest()[:24]
    connection.execute(
        "INSERT INTO mastery_signals_v1(id, card_id, signal_json, calculated_at) VALUES (?, ?, ?, ?)",
        (snapshot_id, card_id, signal.model_dump_json(), calculated_at),
    )
    return signal, snapshot_id


def persist_mastery_signal(
    card_id: str, *, db_path: str | Path, calculated_at: str
) -> MasterySignalV1:
    database = Path(db_path)
    with sqlite3.connect(database) as connection:
        connection.row_factory = sqlite3.Row
        connection.execute("BEGIN IMMEDIATE")
        try:
            signal, _ = persist_mastery_signal_on_connection(
                connection, card_id, calculated_at=calculated_at
            )
            connection.commit()
            return signal
        except Exception:
            connection.rollback()
            raise
