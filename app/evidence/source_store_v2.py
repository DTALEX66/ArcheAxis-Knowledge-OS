"""Durable append-only storage for Source/Anchor/PROV V2 contracts."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from app.contracts.source_anchor_v2 import AnchorV2, ProvenanceActivityV2, SourceObjectV2


class SourceConflictError(ValueError):
    """Raised when an immutable source or anchor identity is reused."""


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


class SourceStoreV2:
    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(str(self.db_path), timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        names = {
            str(row[0])
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        required = {"source_objects_v2", "anchors_v2", "provenance_activities_v2"}
        if not required <= names:
            connection.close()
            raise RuntimeError("AXR source truth migration is pending")
        return connection

    @staticmethod
    def _source_from_row(row: sqlite3.Row) -> SourceObjectV2:
        return SourceObjectV2(
            source_id=str(row["source_id"]),
            version=int(row["version"]),
            sha256=str(row["raw_sha256"]),
            byte_size=int(row["byte_size"]),
            media_type=str(row["media_type"]),
            rights_status=str(row["rights_status"]),  # type: ignore[arg-type]
            original_retained=bool(row["original_retained"]),
            created_at=str(row["created_at"]),
        )

    def put_source(self, source: SourceObjectV2) -> SourceObjectV2:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                "SELECT * FROM source_objects_v2 WHERE source_id=? AND version=?",
                (source.source_id, source.version),
            ).fetchone()
            if existing is not None:
                current = self._source_from_row(existing)
                if current != source:
                    raise SourceConflictError("source version is immutable")
                return current
            latest = connection.execute(
                "SELECT MAX(version) FROM source_objects_v2 WHERE source_id=?",
                (source.source_id,),
            ).fetchone()[0]
            expected = 1 if latest is None else int(latest) + 1
            if source.version != expected:
                raise SourceConflictError(f"source version must be the next append-only value: {expected}")
            connection.execute(
                "INSERT INTO source_objects_v2 "
                "(source_id,version,raw_sha256,byte_size,media_type,rights_status,rights_json,"
                "provenance_json,original_retained,created_at) VALUES (?,?,?,?,?,?,?,?,1,?)",
                (
                    source.source_id,
                    source.version,
                    source.sha256,
                    source.byte_size,
                    source.media_type,
                    source.rights_status,
                    _json({"status": source.rights_status}),
                    _json({"source_id": source.source_id, "version": source.version}),
                    source.created_at,
                ),
            )
            connection.execute(
                "UPDATE anchors_v2 SET state='STALE', updated_at=? "
                "WHERE source_id=? AND source_version<? AND state='CURRENT'",
                (source.created_at, source.source_id, source.version),
            )
            row = connection.execute(
                "SELECT * FROM source_objects_v2 WHERE source_id=? AND version=?",
                (source.source_id, source.version),
            ).fetchone()
            if row is None:
                raise RuntimeError("source readback failed")
            connection.commit()
            return self._source_from_row(row)

    def put_anchor(self, anchor: AnchorV2) -> dict[str, Any]:
        selector_json = _json(anchor.selector.model_dump(mode="json"))
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            source = connection.execute(
                "SELECT 1 FROM source_objects_v2 WHERE source_id=? AND version=?",
                (anchor.source_id, anchor.source_version),
            ).fetchone()
            if source is None:
                raise ValueError("anchor source version does not exist")
            latest = int(
                connection.execute(
                    "SELECT MAX(version) FROM source_objects_v2 WHERE source_id=?",
                    (anchor.source_id,),
                ).fetchone()[0]
            )
            state = "CURRENT" if anchor.source_version == latest else "STALE"
            existing = connection.execute(
                "SELECT * FROM anchors_v2 WHERE anchor_id=?", (anchor.anchor_id,)
            ).fetchone()
            if existing is not None:
                expected = (anchor.source_id, anchor.source_version, selector_json)
                actual = (
                    str(existing["source_id"]),
                    int(existing["source_version"]),
                    str(existing["selector_json"]),
                )
                if actual != expected:
                    raise SourceConflictError("anchor identity is immutable")
                return self.resolve_anchor(anchor.anchor_id, connection=connection)
            connection.execute(
                "INSERT INTO anchors_v2 "
                "(anchor_id,source_id,source_version,selector_json,state,created_at,updated_at) "
                "VALUES (?,?,?,?,?,?,?)",
                (
                    anchor.anchor_id,
                    anchor.source_id,
                    anchor.source_version,
                    selector_json,
                    state,
                    anchor.created_at,
                    anchor.created_at,
                ),
            )
            result = self.resolve_anchor(anchor.anchor_id, connection=connection)
            connection.commit()
            return result

    def resolve_anchor(
        self, anchor_id: str, *, connection: sqlite3.Connection | None = None
    ) -> dict[str, Any]:
        owns_connection = connection is None
        conn = connection or self._connect()
        try:
            row = conn.execute("SELECT * FROM anchors_v2 WHERE anchor_id=?", (anchor_id,)).fetchone()
            if row is None:
                raise KeyError(anchor_id)
            latest = conn.execute(
                "SELECT MAX(version) FROM source_objects_v2 WHERE source_id=?",
                (row["source_id"],),
            ).fetchone()[0]
            state = "ORPHANED" if latest is None else (
                "CURRENT" if int(row["source_version"]) == int(latest) else "STALE"
            )
            if state != row["state"]:
                conn.execute("UPDATE anchors_v2 SET state=? WHERE anchor_id=?", (state, anchor_id))
            return {
                "anchor_id": str(row["anchor_id"]),
                "source_id": str(row["source_id"]),
                "source_version": int(row["source_version"]),
                "latest_source_version": int(latest) if latest is not None else None,
                "selector": json.loads(str(row["selector_json"])),
                "state": state,
            }
        finally:
            if owns_connection:
                conn.close()

    def record_provenance(
        self,
        activity: ProvenanceActivityV2,
        *,
        source_id: str,
        source_version: int,
    ) -> dict[str, Any]:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                "INSERT INTO provenance_activities_v2 "
                "(activity_id,source_id,source_version,activity_type,agent,used_json,"
                "generated_json,started_at,ended_at) VALUES (?,?,?,?,?,?,?,?,?)",
                (
                    activity.activity_id,
                    source_id,
                    source_version,
                    activity.activity_type,
                    activity.agent,
                    _json(activity.used),
                    _json(activity.generated),
                    activity.started_at,
                    activity.ended_at,
                ),
            )
            row = connection.execute(
                "SELECT * FROM provenance_activities_v2 WHERE activity_id=?",
                (activity.activity_id,),
            ).fetchone()
            if row is None:
                raise RuntimeError("provenance readback failed")
            connection.commit()
        result = dict(row)
        result["used"] = json.loads(result.pop("used_json"))
        result["generated"] = json.loads(result.pop("generated_json"))
        return result
