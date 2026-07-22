"""Strict local consumer for completed Workspace research intake events."""
from __future__ import annotations

import json
import sqlite3
from collections.abc import Callable
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

from shared.research_store import load_research_package


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _canonical_json(value: dict[str, object]) -> str:
    return json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True)


def make_intake_research_handler(
    *, db_path: str | Path, consumer_name: str
) -> Callable[[dict[str, object]], dict[str, object]]:
    """Return a handler which verifies completed intake persistence and records its receipt."""

    if not consumer_name:
        raise ValueError("workspace research consumer requires a consumer name")
    database = Path(db_path)

    def consume(event: dict[str, object]) -> dict[str, object]:
        event_id = event.get("event_id")
        payload = event.get("payload")
        lease_token = event.get("lease_token")
        if (
            event.get("event_type") != "intake.research.succeeded"
            or not isinstance(event_id, str)
            or not isinstance(lease_token, str)
            or not lease_token
            or not isinstance(payload, dict)
            or set(payload) != {"package_id"}
            or not isinstance(payload.get("package_id"), str)
            or not payload["package_id"]
        ):
            raise RuntimeError("workspace research consumer received an invalid event")
        package_id = payload["package_id"]
        graph = load_research_package(package_id, db_path=database)
        if graph.package.package_id != package_id:
            raise RuntimeError("workspace research consumer graph binding is invalid")
        proof = {"package_id": package_id}
        proof_json = _canonical_json(proof)
        with closing(sqlite3.connect(database, timeout=30.0)) as connection:
            connection.execute("PRAGMA busy_timeout=30000")
            connection.execute("BEGIN IMMEDIATE")
            try:
                event_row = connection.execute(
                    "SELECT 1 FROM workspace_outbox_v1 WHERE event_id=? AND event_type=? "
                    "AND payload_json=? AND state='leased' AND lease_token=? "
                    "AND julianday(lease_expires_at)>julianday('now')",
                    (
                        event_id,
                        "intake.research.succeeded",
                        _canonical_json(payload),
                        lease_token,
                    ),
                ).fetchone()
                if event_row is None:
                    raise RuntimeError("workspace research consumer event binding is invalid")
                existing = connection.execute(
                    "SELECT consumer_name, proof_json FROM workspace_delivery_receipts_v1 WHERE event_id=?",
                    (event_id,),
                ).fetchone()
                if existing is None:
                    connection.execute(
                        "INSERT INTO workspace_delivery_receipts_v1"
                        "(event_id, consumer_name, proof_json, created_at) VALUES (?, ?, ?, ?)",
                        (event_id, consumer_name, proof_json, _timestamp()),
                    )
                elif existing != (consumer_name, proof_json):
                    raise RuntimeError("workspace research consumer receipt binding is invalid")
                connection.commit()
            except Exception:
                connection.rollback()
                raise
        return {"event_id": event_id, "lease_token": lease_token, "proof": proof}

    return consume
