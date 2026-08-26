"""Project-owned bridge from ArcheAxis truth to the DeepTutor shell."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from app.adapters.deeptutor.authority import (
    AuthorityBoundaryError,
    DeepTutorAuthorityAdapter,
)
from app.learning.event_store import LearningEvent, append_event


class DeepTutorBridge:
    """Read canonical truth, build a replaceable projection, accept candidates."""

    def __init__(
        self,
        *,
        project_root: str | Path,
        db_path: str | Path,
        projection_root: str | Path | None = None,
    ) -> None:
        self.project_root = Path(project_root).resolve()
        self.runtime_root = (self.project_root / ".hermes/task-runtime").resolve()
        self.db_path = Path(db_path).resolve()
        requested = Path(projection_root) if projection_root is not None else (
            self.runtime_root / "deeptutor-home/projections/current"
        )
        self.projection_root = requested.resolve()
        if not self.projection_root.is_relative_to(self.runtime_root):
            raise ValueError("DeepTutor projection must stay inside the project runtime")
        self.adapter = DeepTutorAuthorityAdapter(self.projection_root)

    def _connect_readonly(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            f"file:{self.db_path.as_posix()}?mode=ro", uri=True, timeout=30
        )
        connection.row_factory = sqlite3.Row
        return connection

    def _canonical_records(self) -> tuple[list[dict[str, object]], dict[str, int]]:
        with self._connect_readonly() as connection:
            sources = [
                dict(row)
                for row in connection.execute(
                    "SELECT source_id,version,raw_sha256 AS sha256,byte_size,media_type,"
                    "rights_status,created_at FROM source_objects_v2 "
                    "ORDER BY source_id,version"
                )
            ]
            anchors = [
                {
                    **dict(row),
                    "selector": json.loads(str(row["selector_json"])),
                }
                for row in connection.execute(
                    "SELECT anchor_id,source_id,source_version,selector_json,state "
                    "FROM anchors_v2 ORDER BY anchor_id"
                )
            ]
            events = [
                {
                    **dict(row),
                    "payload": json.loads(str(row["payload_json"])),
                    "status": "candidate",
                }
                for row in connection.execute(
                    "SELECT event_id,learner_id,node_id,event_type,payload_json,occurred_at "
                    "FROM learning_events_v2 ORDER BY occurred_at,event_id"
                )
            ]
        anchors_by_source: dict[tuple[str, int], list[dict[str, object]]] = {}
        for anchor in anchors:
            anchor.pop("selector_json", None)
            key = (str(anchor["source_id"]), int(anchor["source_version"]))
            anchors_by_source.setdefault(key, []).append(anchor)
        records = [
            {
                **source,
                "record_type": "source_projection",
                "anchors": anchors_by_source.get(
                    (str(source["source_id"]), int(source["version"])), []
                ),
            }
            for source in sources
        ]
        records.extend(
            {
                "source_id": f"learning:{event['event_id']}",
                "record_type": "learning_event_candidate",
                **event,
            }
            for event in events
        )
        return records, {
            "anchors": len(anchors),
            "learning_events": len(events),
            "sources": len(sources),
        }

    def rebuild_projection(self) -> dict[str, object]:
        records, counts = self._canonical_records()
        manifest = self.adapter.rebuild_projection(records)
        result = {
            "schema_version": "archeaxis/deeptutor-bridge/v1",
            "projection_root": str(self.projection_root),
            "digest": str(manifest["projection_sha256"]),
            "counts": counts,
            "authority": "ArcheAxis",
            "data_scope": "derived-rebuildable",
        }
        self.projection_root.mkdir(parents=True, exist_ok=True)
        (self.projection_root / "manifest.json").write_text(
            json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )
        return result

    def accept_event(self, payload: dict[str, Any]) -> dict[str, Any]:
        forbidden = {
            "verified",
            "verification_status",
            "knowledge_status",
            "machine_level",
            "machine_competence",
            "human_mastery",
            "human_learning_state",
            "claim_status",
            "source",
            "anchor",
            "provenance",
        }.intersection(payload)
        if forbidden:
            raise ValueError(
                "forbidden authority fields: " + ", ".join(sorted(forbidden))
            )
        required = {
            "event_id",
            "learner_id",
            "node_id",
            "event_type",
            "idempotency_key",
            "outcome",
        }
        missing = sorted(required - set(payload))
        if missing:
            raise ValueError("missing event fields: " + ", ".join(missing))
        try:
            candidate = self.adapter.accept_learning_result(
                {
                    "event_id": payload["event_id"],
                    "learner_id": payload["learner_id"],
                    "source_ref": payload["node_id"],
                    "kind": payload["event_type"],
                    "outcome": payload["outcome"],
                    "recorded_at": payload.get("recorded_at"),
                }
            )
        except AuthorityBoundaryError as exc:
            raise ValueError(str(exc)) from exc
        event_type = {
            "quiz_answer": "quiz",
            "quiz_attempt": "quiz",
            "review_result": "review",
            "review": "review",
            "teach_back": "teach_back",
            "hint": "hint",
            "mistake": "mistake",
            "session_started": "session_started",
            "session_completed": "session_completed",
        }.get(str(candidate["kind"]))
        if event_type is None:
            raise ValueError("unsupported DeepTutor learning event type")
        event = append_event(
            self.db_path,
            LearningEvent(
                event_id=str(candidate["event_id"]),
                learner_id=str(candidate["learner_id"]),
                node_id=str(candidate["source_ref"]),
                event_type=event_type,
                payload=dict(candidate["outcome"]),
                occurred_at=str(candidate.get("recorded_at") or "1970-01-01T00:00:00+00:00"),
                idempotency_key=str(payload["idempotency_key"]),
                source_system="deeptutor",
            ),
        )
        return {
            "event_id": event.event_id,
            "status": "candidate",
            "verified": False,
        }
