from __future__ import annotations

import sqlite3

from app.workspace import service


def test_workspace_lifecycle_projection_is_aggregate_and_fail_closed(tmp_path):
    database = tmp_path / "workspace.sqlite"
    with sqlite3.connect(database) as connection:
        connection.execute(
            "CREATE TABLE execution_traces (events_json TEXT NOT NULL)"
        )
        connection.execute(
            "INSERT INTO execution_traces(events_json) VALUES (?)",
            ('[{"result":{"tool":"permission","status":"blocked"}}]',),
        )
        connection.execute(
            "CREATE TABLE evaluation_candidates_v1 (status TEXT NOT NULL)"
        )
        connection.execute(
            "INSERT INTO evaluation_candidates_v1(status) VALUES ('approved')"
        )
        connection.execute("CREATE TABLE machine_lessons (id TEXT NOT NULL)")
        connection.execute("INSERT INTO machine_lessons(id) VALUES ('lesson-1')")

    payload = service.workspace_lifecycle(db_path=database)

    assert payload["privacy"] == "aggregate_only"
    assert payload["stages"] == {
        "permission": {"state": "blocked", "gates": 1, "blocked": 1},
        "execution": {"state": "recorded", "runs": 1},
        "trace": {"state": "recorded", "runs": 1},
        "evaluation": {"state": "approved", "candidates": 1, "approved": 1},
        "lesson": {"state": "recorded", "items": 1},
    }
    assert "lesson-1" not in str(payload)
