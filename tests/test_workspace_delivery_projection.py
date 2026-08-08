from __future__ import annotations

import sqlite3

from app.workspace.service import workspace_delivery
from shared.workspace_migration import (
    WORKSPACE_DELIVERY_RECEIPT_SCHEMA_SQL,
    WORKSPACE_SCHEMA_SQL,
)


def test_workspace_delivery_projects_job_outbox_and_receipt_without_ids(tmp_path) -> None:
    db_path = tmp_path / "workspace.sqlite"
    with sqlite3.connect(db_path) as connection:
        connection.executescript(WORKSPACE_SCHEMA_SQL)
        connection.executescript(WORKSPACE_DELIVERY_RECEIPT_SCHEMA_SQL)
        connection.execute(
            "INSERT INTO workspace_jobs_v1 "
            "(job_id, command_id, job_type, aggregate_id, state, attempt_count, payload_json, "
            "correlation_id, causation_id, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "job_internal",
                "command_internal",
                "intake.research",
                "package_internal",
                "succeeded",
                1,
                '{"package_id":"package_internal"}',
                "command_internal",
                "command_internal",
                "2026-07-26T00:00:00Z",
                "2026-07-26T00:00:01Z",
            ),
        )
        connection.execute(
            "INSERT INTO workspace_outbox_v1 "
            "(event_id, job_id, event_type, payload_json, state, attempt_count, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "event_internal",
                "job_internal",
                "intake.research.succeeded",
                '{"package_id":"package_internal"}',
                "delivered",
                1,
                "2026-07-26T00:00:00Z",
                "2026-07-26T00:00:01Z",
            ),
        )
        connection.execute(
            "INSERT INTO workspace_delivery_receipts_v1 "
            "(event_id, consumer_name, proof_json, created_at) VALUES (?, ?, ?, ?)",
            (
                "event_internal",
                "research-consumer",
                '{"verified":true}',
                "2026-07-26T00:00:01Z",
            ),
        )
        connection.commit()

    payload = workspace_delivery(db_path=db_path)

    assert payload == {
        "schema_version": "v1",
        "dispatcher": "lease_fenced",
        "summary": {
            "jobs": 1,
            "outbox": {"delivered": 1},
            "receipts": {"recorded": 1},
        },
        "items": [
            {
                "activity": "资料导入",
                "job_state": "succeeded",
                "job_attempts": 1,
                "outbox_state": "delivered",
                "outbox_attempts": 1,
                "receipt_state": "recorded",
            }
        ],
    }
    serialized = repr(payload)
    for internal_value in ("job_internal", "command_internal", "package_internal", "event_internal"):
        assert internal_value not in serialized
