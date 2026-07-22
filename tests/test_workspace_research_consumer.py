from __future__ import annotations

import json
import sqlite3
from contextlib import closing


def test_research_intake_consumer_writes_event_bound_receipt_before_delivery(monkeypatch, tmp_path) -> None:
    from app.workspace import service
    from app.workspace.outbox_dispatcher import dispatch_once
    from app.workspace.research_consumer import make_intake_research_handler
    from shared.migration_runner import MigrationOperator
    from tests.test_phase5_mcs_closed_loop import _database

    database = _database(tmp_path)
    MigrationOperator(db_path=database, backup_dir=tmp_path / "workspace-backups").apply(
        "workspace.sqlite"
    )
    monkeypatch.setattr(service, "convert_url", lambda _: ("# Candidate\nEvidence body.", "test"))
    intake = service.intake_url(url="https://example.com/consumer", db_path=database)

    result = dispatch_once(
        db_path=database,
        worker_name="workspace-research-consumer-test",
        handler=make_intake_research_handler(db_path=database, consumer_name="local-research-readback"),
    )

    assert result == {"status": "delivered", "attempt": 1}
    with closing(sqlite3.connect(database)) as connection:
        receipt = connection.execute(
            "SELECT event_id, consumer_name, proof_json FROM workspace_delivery_receipts_v1"
        ).fetchone()
        outbox = connection.execute("SELECT state FROM workspace_outbox_v1").fetchone()
    assert receipt is not None
    assert receipt[1] == "local-research-readback"
    assert json.loads(receipt[2]) == {"package_id": intake["package_id"]}
    assert outbox == ("delivered",)


def test_research_consumer_rejects_a_superseded_lease_before_writing_receipt(monkeypatch, tmp_path) -> None:
    import pytest

    from app.workspace import service
    from app.workspace.research_consumer import make_intake_research_handler
    from shared.migration_runner import MigrationOperator
    from tests.test_phase5_mcs_closed_loop import _database

    database = _database(tmp_path)
    MigrationOperator(db_path=database, backup_dir=tmp_path / "workspace-backups").apply(
        "workspace.sqlite"
    )
    monkeypatch.setattr(service, "convert_url", lambda _: ("# Candidate\nEvidence body.", "test"))
    service.intake_url(url="https://example.com/superseded", db_path=database)
    with closing(sqlite3.connect(database)) as connection:
        event_id, payload_json = connection.execute(
            "SELECT event_id, payload_json FROM workspace_outbox_v1"
        ).fetchone()
        connection.execute(
            "UPDATE workspace_outbox_v1 SET state='leased', lease_token='new-token', "
            "lease_expires_at='2999-01-01T00:00:00Z' WHERE event_id=?",
            (event_id,),
        )
        connection.commit()

    handler = make_intake_research_handler(db_path=database, consumer_name="local-research-readback")
    with pytest.raises(RuntimeError, match="event binding is invalid"):
        handler(
            {
                "event_id": event_id,
                "event_type": "intake.research.succeeded",
                "payload": json.loads(payload_json),
                "lease_token": "old-token",
            }
        )
    with closing(sqlite3.connect(database)) as connection:
        assert connection.execute(
            "SELECT 1 FROM workspace_delivery_receipts_v1 WHERE event_id=?", (event_id,)
        ).fetchone() is None
