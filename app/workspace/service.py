"""Server-owned orchestration for one governed Cognitive Workspace case."""
from __future__ import annotations

import json
import sqlite3
import tempfile
import threading
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from urllib.parse import urlsplit

from app.workspace.job_outbox import command_request_fingerprint, record_completed_command

# Heavy dependencies loaded lazily inside functions to avoid numpy/vector chain at import time.
# Each intake function calls _import_heavy() before use.
_HEAVY_IMPORTED: dict[str, object] | None = None
research_github_repository = None
convert_file = None
convert_url = None
detect_format = None
approve_learning_artifact = None
audit_closed_loop = None
record_practice_evidence = None
start_and_approve_learning_candidate = None
ResearchKnowledgeApproval = None
promote_research_package_to_candidates = None
persist_workspace_document = None
ResearchPackageGraph = None
load_research_package = None


def _import_heavy() -> None:
    """Lazy-import heavy research/knowledge/ingestion dependencies."""
    global _HEAVY_IMPORTED
    if _HEAVY_IMPORTED is None:
        from app.facades.research import research_github_repository as _research_github_repository
        from app.ingestion.multi_format import (
            convert_file as _convert_file,
        )
        from app.ingestion.multi_format import (
            convert_url as _convert_url,
        )
        from app.ingestion.multi_format import (
            detect_format as _detect_format,
        )
        from app.knowledge.closed_loop import (
            approve_learning_artifact as _approve_learning_artifact,
        )
        from app.knowledge.closed_loop import (
            audit_closed_loop as _audit_closed_loop,
        )
        from app.knowledge.closed_loop import (
            record_practice_evidence as _record_practice_evidence,
        )
        from app.knowledge.closed_loop import (
            start_and_approve_learning_candidate as _start_and_approve_learning_candidate,
        )
        from app.knowledge.promotion import (
            ResearchKnowledgeApproval as _ResearchKnowledgeApproval,
        )
        from app.knowledge.promotion import (
            promote_research_package_to_candidates as _promote_research_package_to_candidates,
        )
        from app.research.document import persist_workspace_document as _persist_workspace_document
        from shared.research_store import (
            ResearchPackageGraph as _ResearchPackageGraph,
        )
        from shared.research_store import (
            load_research_package as _load_research_package,
        )
        _HEAVY_IMPORTED = {
            "research_github_repository": _research_github_repository,
            "convert_file": _convert_file,
            "convert_url": _convert_url,
            "detect_format": _detect_format,
            "approve_learning_artifact": _approve_learning_artifact,
            "audit_closed_loop": _audit_closed_loop,
            "record_practice_evidence": _record_practice_evidence,
            "start_and_approve_learning_candidate": _start_and_approve_learning_candidate,
            "ResearchKnowledgeApproval": _ResearchKnowledgeApproval,
            "promote_research_package_to_candidates": _promote_research_package_to_candidates,
            "persist_workspace_document": _persist_workspace_document,
            "ResearchPackageGraph": _ResearchPackageGraph,
            "load_research_package": _load_research_package,
        }

    # Preserve module-level seams used by callers and tests while restoring any
    # temporary monkeypatch that has already been undone.
    for name, imported in _HEAVY_IMPORTED.items():
        if globals().get(name) is None:
            globals()[name] = imported

MAX_INTAKE_UPLOAD_BYTES = 25 * 1024 * 1024
_COMMAND_LOCKS = tuple(threading.RLock() for _ in range(64))


def _command_lock(command_id: str) -> threading.RLock:
    digest = sha256(command_id.encode("utf-8")).digest()
    return _COMMAND_LOCKS[int.from_bytes(digest[:4], "big") % len(_COMMAND_LOCKS)]


def _intake_command_id(package_id: str) -> str:
    return "intake_" + sha256(package_id.encode("utf-8")).hexdigest()[:24]


def _intake_job_id(package_id: str) -> str:
    command_id = _intake_command_id(package_id)
    return "job_" + sha256(command_id.encode("utf-8")).hexdigest()[:24]


def _intake_before_commit(
    connection: sqlite3.Connection,
    graph,
) -> None:
    _import_heavy()
    package_id = graph.package.package_id
    command_id = _intake_command_id(package_id)
    record_completed_command(
        connection,
        command_id=command_id,
        command_type="intake.research",
        aggregate_id=package_id,
        payload={"package_id": package_id},
    )


def intake_url(*, url: str, db_path: str | Path, fetcher=None) -> dict:
    _import_heavy()
    parsed = urlsplit(url)
    if parsed.hostname and parsed.hostname.rstrip(".").casefold() == "github.com":
        graph = research_github_repository(
            url,
            fetcher=fetcher,
            db_path=db_path,
            before_commit=_intake_before_commit,
        )
        return {
            "source_type": "github_repository",
            "source": graph.canonical_url,
            "package_id": graph.package.package_id,
            "job_id": _intake_job_id(graph.package.package_id),
            "status": graph.package.status,
            "requires_human_review": graph.package.requires_human_review,
            "source_count": len(graph.sources),
            "claim_count": len(graph.claims),
            "evidence_count": len(graph.evidence),
        }
    content, engine = convert_url(url)
    graph = persist_workspace_document(
        title=url,
        content=content,
        source_format="html",
        extractor_identity=engine,
        source_locator=url,
        db_path=db_path,
        before_commit=_intake_before_commit,
    )
    return {
        "source_type": "web",
        "source": url,
        "package_id": graph.package.package_id,
        "job_id": _intake_job_id(graph.package.package_id),
        "status": graph.package.status,
        "requires_human_review": graph.package.requires_human_review,
        "source_count": len(graph.sources),
        "claim_count": len(graph.claims),
        "evidence_count": len(graph.evidence),
    }


def intake_upload(*, file_name: str, content: bytes, db_path: str | Path) -> dict:
    _import_heavy()
    if not file_name:
        raise ValueError("uploaded file requires a name")
    if not content:
        raise ValueError("uploaded file is empty")
    if len(content) > MAX_INTAKE_UPLOAD_BYTES:
        raise ValueError("uploaded file exceeds the 25 MB local intake limit")
    safe_name = Path(file_name).name
    if safe_name != file_name:
        raise ValueError("uploaded file name must not include a path")
    upload_dir = Path(db_path).parent / "intake_uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    suffix = Path(safe_name).suffix.casefold()
    stored_path = upload_dir / f"{sha256(content).hexdigest()}{suffix}"
    with tempfile.NamedTemporaryFile(
        dir=upload_dir, prefix=".upload-", suffix=suffix, delete=False
    ) as temporary:
        temporary.write(content)
        temporary_path = Path(temporary.name)
    try:
        markdown, engine = convert_file(temporary_path)
        source_format = detect_format(temporary_path)
        graph = persist_workspace_document(
            title=safe_name,
            content=markdown,
            source_format=source_format,
            extractor_identity=engine,
            db_path=db_path,
            before_commit=_intake_before_commit,
        )
        if stored_path.exists():
            if stored_path.read_bytes() != content:
                raise RuntimeError("uploaded content hash conflicts with an existing local source")
            temporary_path.unlink(missing_ok=True)
        else:
            temporary_path.replace(stored_path)
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise
    return {
        "source_type": "file",
        "file_name": safe_name,
        "format": source_format,
        "engine": engine,
        "content": markdown,
        "char_count": len(markdown),
        "package_id": graph.package.package_id,
        "job_id": _intake_job_id(graph.package.package_id),
        "status": graph.package.status,
        "requires_human_review": graph.package.requires_human_review,
    }


def intake_job(*, job_id: str, db_path: str | Path) -> dict[str, object]:
    _import_heavy()
    if not job_id.startswith("job_") or len(job_id) != 28:
        raise ValueError("workspace job id is invalid")
    with sqlite3.connect(Path(db_path)) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            "SELECT j.job_id, j.command_id, j.job_type, j.aggregate_id, j.state, "
            "j.payload_json, j.correlation_id, j.causation_id, j.updated_at, "
            "o.event_id, o.event_type, o.state AS outbox_state, "
            "o.payload_json AS outbox_payload_json, r.command_id AS receipt_command_id, "
            "r.command_type AS receipt_command_type, r.request_fingerprint, "
            "r.job_id AS receipt_job_id, r.result_json "
            "FROM workspace_jobs_v1 AS j "
            "LEFT JOIN workspace_outbox_v1 AS o ON o.job_id=j.job_id "
            "LEFT JOIN workspace_command_receipts_v1 AS r ON r.job_id=j.job_id "
            "WHERE j.job_id=?",
            (job_id,),
        ).fetchall()
        dangling_bindings = 0
        if not rows:
            dangling_bindings = connection.execute(
                "SELECT "
                "(SELECT COUNT(*) FROM workspace_outbox_v1 WHERE job_id=?) + "
                "(SELECT COUNT(*) FROM workspace_command_receipts_v1 WHERE job_id=?)",
                (job_id, job_id),
            ).fetchone()[0]
    if len(rows) != 1:
        if rows or dangling_bindings:
            raise RuntimeError("workspace job persisted bindings are inconsistent")
        raise LookupError("workspace job was not found or is not uniquely bound")
    row = rows[0]
    package_id = str(row["aggregate_id"])
    command_id = _intake_command_id(package_id)
    expected_job_id = _intake_job_id(package_id)
    expected_event_id = "outbox_" + sha256(command_id.encode("utf-8")).hexdigest()[:24]
    expected_payload = {"package_id": package_id}
    expected_result = {
        "command_id": command_id,
        "event_id": expected_event_id,
        "job_id": expected_job_id,
    }
    expected_fingerprint = command_request_fingerprint(
        command_type="intake.research",
        aggregate_id=package_id,
        payload=expected_payload,
        job_state="succeeded",
        event_type="intake.research.succeeded",
    )
    try:
        payload = json.loads(str(row["payload_json"]))
        outbox_payload = json.loads(str(row["outbox_payload_json"]))
        result = json.loads(str(row["result_json"]))
    except json.JSONDecodeError as exc:
        raise RuntimeError("workspace job contains malformed persisted JSON") from exc
    if (
        str(row["job_type"]) != "intake.research"
        or str(row["state"]) != "succeeded"
        or str(row["command_id"]) != command_id
        or str(row["job_id"]) != expected_job_id
        or str(row["correlation_id"]) != command_id
        or str(row["causation_id"]) != command_id
        or str(row["event_id"]) != expected_event_id
        or str(row["event_type"]) != "intake.research.succeeded"
        or str(row['outbox_state']) not in ('pending', 'delivered')
        or str(row["receipt_command_id"]) != command_id
        or str(row["receipt_command_type"]) != "intake.research"
        or str(row["receipt_job_id"]) != expected_job_id
        or str(row["request_fingerprint"]) != expected_fingerprint
        or payload != expected_payload
        or outbox_payload != payload
        or result != expected_result
    ):
        raise RuntimeError("workspace job persistence binding is invalid")
    # This is an internal live-runtime projection.  The server may still have
    # WAL/SHM sidecars after the intake transaction, so use the query-only
    # live-WAL reader rather than the immutable checkpoint-only reader used by
    # offline/external read paths.
    graph = load_research_package(package_id, db_path=db_path, live_wal=True)
    return {
        "job_id": expected_job_id,
        "state": str(row["state"]),
        "event_type": str(row["event_type"]),
        "outbox_state": str(row["outbox_state"]),
        "package_id": package_id,
        "package_status": graph.package.status,
        "source_count": len(graph.sources),
        "updated_at": str(row["updated_at"]),
    }


def workspace_jobs(*, db_path: str | Path) -> dict[str, object]:
    """Return strict, non-identifying projections for the local Job Center."""

    with sqlite3.connect(Path(db_path)) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            "SELECT j.job_id, j.command_id, j.job_type, j.state, j.payload_json, "
            "j.correlation_id, j.causation_id, j.updated_at, o.event_id, o.event_type, "
            "o.state AS outbox_state, o.payload_json AS outbox_payload_json, "
            "r.command_id AS receipt_command_id, r.command_type AS receipt_command_type, "
            "r.job_id AS receipt_job_id, r.result_json "
            "FROM workspace_jobs_v1 AS j "
            "LEFT JOIN workspace_outbox_v1 AS o ON o.job_id=j.job_id "
            "LEFT JOIN workspace_command_receipts_v1 AS r ON r.job_id=j.job_id "
            "ORDER BY j.updated_at DESC, j.job_id DESC"
        ).fetchall()
        orphan_count = connection.execute(
            "SELECT "
            "(SELECT COUNT(*) FROM workspace_outbox_v1 AS o "
            "LEFT JOIN workspace_jobs_v1 AS j ON j.job_id=o.job_id WHERE j.job_id IS NULL) + "
            "(SELECT COUNT(*) FROM workspace_command_receipts_v1 AS r "
            "LEFT JOIN workspace_jobs_v1 AS j ON j.job_id=r.job_id WHERE j.job_id IS NULL)"
        ).fetchone()[0]
    if orphan_count:
        raise RuntimeError("workspace job persisted bindings are inconsistent")

    projections: list[dict[str, str]] = []
    for row in rows:
        command_id = str(row["command_id"])
        job_id = str(row["job_id"])
        job_type = str(row["job_type"])
        job_state = str(row["state"])
        expected_job_id = "job_" + sha256(command_id.encode("utf-8")).hexdigest()[:24]
        expected_event_id = "outbox_" + sha256(command_id.encode("utf-8")).hexdigest()[:24]
        try:
            payload = json.loads(str(row["payload_json"]))
            outbox_payload = json.loads(str(row["outbox_payload_json"]))
            result = json.loads(str(row["result_json"]))
        except (json.JSONDecodeError, TypeError) as exc:
            raise RuntimeError("workspace job contains malformed persisted JSON") from exc
        if (
            job_type != "intake.research"
            or job_state not in {"queued", "succeeded"}
            or job_id != expected_job_id
            or str(row["correlation_id"]) != command_id
            or str(row["causation_id"]) != command_id
            or str(row["event_id"]) != expected_event_id
            or str(row["event_type"]) != f"{job_type}.{job_state}"
            or str(row["receipt_command_id"]) != command_id
            or str(row["receipt_command_type"]) != job_type
            or str(row["receipt_job_id"]) != job_id
            or payload != outbox_payload
            or result
            != {"command_id": command_id, "event_id": expected_event_id, "job_id": expected_job_id}
        ):
            raise RuntimeError("workspace job persistence binding is invalid")
        projections.append(
            {
                "activity": "资料导入",
                "state": job_state,
                "delivery_state": str(row["outbox_state"]),
                "updated_at": str(row["updated_at"]),
            }
        )
    return {"schema_version": "v1", "jobs": projections}


def workspace_delivery(*, db_path: str | Path) -> dict[str, object]:
    """Project Job, Outbox, and Delivery Receipt state without internal identities."""
    from collections import Counter

    with sqlite3.connect(Path(db_path), timeout=30.0) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            "SELECT j.state AS job_state, j.attempt_count AS job_attempts, "
            "o.state AS outbox_state, o.attempt_count AS outbox_attempts, "
            "CASE WHEN d.event_id IS NULL THEN 'missing' ELSE 'recorded' END AS receipt_state "
            "FROM workspace_jobs_v1 AS j "
            "LEFT JOIN workspace_outbox_v1 AS o ON o.job_id=j.job_id "
            "LEFT JOIN workspace_delivery_receipts_v1 AS d ON d.event_id=o.event_id "
            "ORDER BY j.updated_at DESC, j.job_id DESC"
        ).fetchall()
    items = [
        {
            "activity": "资料导入",
            "job_state": str(row["job_state"]),
            "job_attempts": int(row["job_attempts"]),
            "outbox_state": str(row["outbox_state"] or "missing"),
            "outbox_attempts": int(row["outbox_attempts"] or 0),
            "receipt_state": str(row["receipt_state"]),
        }
        for row in rows
    ]
    return {
        "schema_version": "v1",
        "dispatcher": "lease_fenced",
        "summary": {
            "jobs": len(items),
            "outbox": dict(Counter(item["outbox_state"] for item in items)),
            "receipts": dict(Counter(item["receipt_state"] for item in items)),
        },
        "items": items,
    }


def dispatch_delivery_once(*, db_path: str | Path) -> dict[str, object]:
    """Deliver one local event through the lease-fenced consumer."""
    from app.workspace.outbox_dispatcher import dispatch_once
    from app.workspace.research_consumer import make_intake_research_handler

    result = dispatch_once(
        db_path=db_path,
        worker_name="workspace-ui-on-demand",
        handler=make_intake_research_handler(
            db_path=db_path, consumer_name="workspace-ui-research-consumer"
        ),
    )
    return {
        "schema_version": "v1",
        "status": str(result["status"]),
        "attempt": int(result.get("attempt", 0)),
    }


def retry_failed_delivery(*, db_path: str | Path) -> dict[str, object]:
    """Requeue one failed event; delivery still requires the lease-fenced dispatcher."""
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    with sqlite3.connect(Path(db_path), timeout=30.0) as connection:
        connection.execute("PRAGMA busy_timeout=30000")
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute(
            "SELECT event_id FROM workspace_outbox_v1 WHERE state='failed' "
            "ORDER BY updated_at, event_id LIMIT 1"
        ).fetchone()
        if row is None:
            connection.rollback()
            return {"schema_version": "v1", "status": "idle"}
        connection.execute(
            "UPDATE workspace_outbox_v1 SET state='pending', lease_token=NULL, "
            "lease_expires_at=NULL, updated_at=? WHERE event_id=? AND state='failed'",
            (now, str(row[0])),
        )
        connection.commit()
    return {"schema_version": "v1", "status": "requeued"}


def workspace_status(*, db_path: str | Path) -> dict[str, object]:
    """Return aggregate, non-identifying state for the local product shell."""
    from collections import Counter

    from app.release import load_release_manifest, safe_release_summary
    from shared.migration_runner import MigrationOperator

    def grouped(connection: sqlite3.Connection, table: str, column: str) -> dict[str, int]:
        rows = connection.execute(
            f"SELECT {column}, COUNT(*) FROM {table} GROUP BY {column} ORDER BY {column}"
        ).fetchall()
        return {str(state): int(count) for state, count in rows}

    with sqlite3.connect(Path(db_path), timeout=30.0) as connection:
        connection.execute("PRAGMA busy_timeout=30000")
        connection.execute("PRAGMA query_only=ON")
        counts = {
            "research": grouped(connection, "research_packages_v1", "status"),
            "jobs": grouped(connection, "workspace_jobs_v1", "state"),
            "outbox": grouped(connection, "workspace_outbox_v1", "state"),
            "learning": grouped(
                connection,
                "knowledge_candidate_learning_artifacts_v1",
                "status",
            ),
            "machine_knowledge": grouped(
                connection,
                "machine_knowledge_candidates_v1",
                "lifecycle_status",
            ),
        }
    try:
        migration_states = dict(
            Counter(
                item["state"]
                for item in MigrationOperator(
                    db_path=Path(db_path),
                    backup_dir=Path(db_path).parent / "backups",
                ).status()
            )
        ) or {"unavailable": 1}
    except Exception:
        migration_states = {"unavailable": 1}
    manifest = load_release_manifest()
    return {
        "schema_version": "v1",
        "observed_at": now_utc(),
        "release": safe_release_summary(),
        "migrations": migration_states,
        "components": {
            "api": "available",
            "database": "available",
            "worker": "available",
            "outbox_dispatcher": "lease_fenced",
            "server_sent_events": "not_connected",
        },
        "counts": counts,
        "capabilities": manifest["capabilities"],
    }


def research_review_queue(*, db_path: str | Path) -> dict[str, object]:
    """Return user-readable pending Research without exposing persistence IDs."""
    with sqlite3.connect(Path(db_path), timeout=30.0) as connection:
        connection.execute("PRAGMA busy_timeout=30000")
        connection.execute("PRAGMA query_only=ON")
        rows = connection.execute(
            "SELECT canonical_url, claim_ids_json, evidence_ids_json, verification_status, created_at "
            "FROM research_packages_v1 WHERE status IN ('candidate', 'ready_for_review') "
            "AND requires_human_review=1 "
            "AND NOT EXISTS ("
            "SELECT 1 FROM knowledge_candidate_governance_events_v1 AS ge "
            "WHERE ge.package_id=research_packages_v1.id AND ge.decision='approved'"
            ") ORDER BY created_at DESC, canonical_url"
        ).fetchall()
    items = []
    for source, claims, evidence, verification, created_at in rows:
        try:
            claim_count = len(json.loads(str(claims)))
            evidence_count = len(json.loads(str(evidence)))
        except (TypeError, json.JSONDecodeError) as exc:
            raise RuntimeError("workspace research queue contains malformed persisted data") from exc
        items.append({"source": str(source), "claim_count": claim_count, "evidence_count": evidence_count,
                      "verification": str(verification), "created_at": str(created_at)})
    return {"schema_version": "v1", "items": items}


def promote_research_source(*, command_id: str, source: str, reviewer_id: str, rationale: str,
                            db_path: str | Path) -> dict:
    with sqlite3.connect(Path(db_path), timeout=30.0) as connection:
        row = connection.execute(
            "SELECT id FROM research_packages_v1 WHERE canonical_url=? "
            "AND status IN ('candidate', 'ready_for_review') AND requires_human_review=1", (source,)
        ).fetchone()
    if row is None:
        raise ValueError("该资料不在待审核队列中")
    return promote_research(command_id=command_id, package_id=str(row[0]), reviewer_id=reviewer_id,
                            rationale=rationale, db_path=db_path)


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _require_matching_promotion_command(
    *, command_id: str, package_id: str, reviewer_id: str, rationale: str, db_path: str | Path
) -> None:
    with sqlite3.connect(Path(db_path)) as connection:
        row = connection.execute(
            "SELECT package_id, reviewer_id, decision, rationale "
            "FROM knowledge_candidate_governance_events_v1 WHERE approval_id=?",
            (command_id,),
        ).fetchone()
    if row is None:
        return
    recorded = tuple(str(item) for item in row)
    requested = (package_id, reviewer_id, "approved", rationale)
    if recorded != requested:
        raise RuntimeError("workspace command id conflicts with an existing promotion receipt")


def _require_matching_learning_command(
    *, command_id: str, unit_id: str, reviewer_id: str, rationale: str, db_path: str | Path
) -> None:
    with sqlite3.connect(Path(db_path)) as connection:
        row = connection.execute(
            "SELECT source_unit_id, reviewer_id, rationale "
            "FROM knowledge_candidate_learning_artifacts_v1 WHERE approval_id=?",
            (command_id,),
        ).fetchone()
    if row is None:
        return
    if tuple(str(item) for item in row) != (unit_id, reviewer_id, rationale):
        raise RuntimeError("workspace command id conflicts with an existing learning receipt")


def _require_matching_practice_command(
    *, command_id: str, artifact_id: str, quality: int, db_path: str | Path
) -> None:
    review_id = "practice_" + sha256(command_id.encode()).hexdigest()[:24]
    with sqlite3.connect(Path(db_path)) as connection:
        row = connection.execute(
            "SELECT card_id, quality FROM kb_reviews WHERE id=?", (review_id,)
        ).fetchone()
    expected = (f"{artifact_id}-card-0", quality)
    if row is not None and (str(row[0]), int(row[1])) != expected:
        raise RuntimeError("workspace command id conflicts with an existing practice receipt")


def promote_research(*, command_id: str, package_id: str, reviewer_id: str, rationale: str, db_path: str | Path) -> dict:
    _import_heavy()
    with _command_lock(command_id):
        _require_matching_promotion_command(
            command_id=command_id,
            package_id=package_id,
            reviewer_id=reviewer_id,
            rationale=rationale,
            db_path=db_path,
        )
        receipt = promote_research_package_to_candidates(
            ResearchKnowledgeApproval(
                approval_id=command_id,
                package_id=package_id,
                reviewer_id=reviewer_id,
                decision="approved",
                rationale=rationale,
                reviewed_at=now_utc(),
            ),
            db_path=db_path,
        )
    return {
        "command_id": command_id,
        "promotion_id": receipt.promotion_id,
        "package_id": receipt.package_id,
        "unit_ids": [unit.unit_id for unit in receipt.units],
        "status": receipt.lifecycle_status,
    }


def start_learning(*, command_id: str, unit_id: str, reviewer_id: str, rationale: str, db_path: str | Path) -> dict:
    _import_heavy()
    with _command_lock(command_id):
        _require_matching_learning_command(
            command_id=command_id,
            unit_id=unit_id,
            reviewer_id=reviewer_id,
            rationale=rationale,
            db_path=db_path,
        )
        reviewed_at = now_utc()
        artifact, card_ids = start_and_approve_learning_candidate(
            unit_id=unit_id,
            approval_id=command_id,
            approval_command_id=f"local-approval-{command_id}",
            reviewer_id=reviewer_id,
            rationale=rationale,
            reviewed_at=reviewed_at,
            db_path=db_path,
        )
    return {
        "command_id": command_id,
        "artifact_id": artifact.artifact_id,
        "card_ids": card_ids,
        "status": "approved",
    }


def approve_learning(*, command_id: str, artifact_id: str, reviewer_id: str, db_path: str | Path) -> dict:
    _import_heavy()
    with _command_lock(command_id):
        card_ids = approve_learning_artifact(
            artifact_id=artifact_id,
            command_id=command_id,
            reviewer_id=reviewer_id,
            reviewed_at=now_utc(),
            db_path=db_path,
        )
    return {"command_id": command_id, "artifact_id": artifact_id, "card_ids": card_ids, "status": "approved"}


def record_practice(*, command_id: str, artifact_id: str, quality: int, db_path: str | Path) -> dict:
    _import_heavy()
    with _command_lock(command_id):
        _require_matching_practice_command(
            command_id=command_id, artifact_id=artifact_id, quality=quality, db_path=db_path
        )
        result = record_practice_evidence(
            artifact_id=artifact_id,
            command_id=command_id,
            quality=quality,
            recorded_at=now_utc(),
            db_path=db_path,
        )
    return {
        "command_id": command_id,
        "artifact_id": artifact_id,
        "mastered": result.mastery_signal.is_mastered,
        "machine_candidate_id": result.machine_knowledge.unit_id if result.machine_knowledge else None,
    }


def case_audit(*, artifact_id: str, db_path: str | Path) -> dict:
    _import_heavy()
    return {
        "artifact_id": artifact_id,
        "events": [
            {"event_type": event.event_type, "occurred_at": event.occurred_at}
            for event in audit_closed_loop(artifact_id, db_path=db_path)
        ],
    }


def _workspace_source_artifact(
    connection: sqlite3.Connection, source: str
) -> sqlite3.Row | None:
    """Resolve a human source label to the latest governed learning artifact."""
    return connection.execute(
        "SELECT la.id, la.artifact_json, la.status "
        "FROM knowledge_candidate_learning_artifacts_v1 AS la "
        "JOIN knowledge_candidate_units_v1 AS ku ON ku.id=la.source_unit_id "
        "JOIN research_packages_v1 AS rp ON rp.id=ku.package_id "
        "WHERE rp.canonical_url=? ORDER BY la.created_at DESC, la.id DESC LIMIT 1",
        (source,),
    ).fetchone()


def workspace_knowledge(*, db_path: str | Path) -> dict[str, object]:
    """Return source-oriented Knowledge candidates without persistence IDs."""
    with sqlite3.connect(Path(db_path), timeout=30.0) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            "SELECT rp.canonical_url AS source, "
            "SUM(CASE WHEN ku.unit_type='research_claim' THEN 1 ELSE 0 END) AS claims, "
            "SUM(CASE WHEN ku.unit_type='research_source' THEN 1 ELSE 0 END) AS sources, "
            "MAX(ku.lifecycle_status) AS lifecycle "
            "FROM knowledge_candidate_units_v1 AS ku "
            "JOIN research_packages_v1 AS rp ON rp.id=ku.package_id "
            "GROUP BY rp.canonical_url ORDER BY rp.canonical_url"
        ).fetchall()
    return {
        "schema_version": "v1",
        "items": [
            {
                "source": str(row["source"]),
                "claim_count": int(row["claims"] or 0),
                "source_count": int(row["sources"] or 0),
                "lifecycle": str(row["lifecycle"] or "candidate"),
            }
            for row in rows
        ],
    }


def workspace_learning(*, db_path: str | Path) -> dict[str, object]:
    """Return source-oriented Learning artifacts and practice state."""
    with sqlite3.connect(Path(db_path), timeout=30.0) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            "SELECT la.id, la.artifact_json, la.status, rp.canonical_url AS source "
            "FROM knowledge_candidate_learning_artifacts_v1 AS la "
            "JOIN knowledge_candidate_units_v1 AS ku ON ku.id=la.source_unit_id "
            "JOIN research_packages_v1 AS rp ON rp.id=ku.package_id "
            "ORDER BY la.created_at, la.id"
        ).fetchall()
        items: list[dict[str, object]] = []
        for row in rows:
            artifact = json.loads(str(row["artifact_json"]))
            artifact_id = str(row["id"])
            card_id = f"{artifact_id}-card-0"
            practice_count = int(
                connection.execute(
                    "SELECT COUNT(*) FROM kb_reviews WHERE card_id=?", (card_id,)
                ).fetchone()[0]
            )
            items.append(
                {
                    "source": str(row["source"]),
                    "status": "approved" if practice_count or artifact.get("status") == "approved" else str(row["status"]),
                    "statement": str(artifact.get("summary", {}).get("statement", "")),
                    "card_count": len(artifact.get("cards", [])),
                    "practice_count": practice_count,
                }
            )
    return {"schema_version": "v1", "items": items}


def start_learning_source(*, command_id: str, source: str, db_path: str | Path) -> dict[str, object]:
    """Start the first reviewed claim for a source using server-owned provenance."""
    database = Path(db_path)
    with sqlite3.connect(database, timeout=30.0) as connection:
        connection.row_factory = sqlite3.Row
        existing = _workspace_source_artifact(connection, source)
        if existing is not None:
            artifact = json.loads(str(existing["artifact_json"]))
            return {
                "source": source,
                "status": "already_started",
                "card_count": len(artifact.get("cards", [])),
            }
        row = connection.execute(
            "SELECT ku.id FROM knowledge_candidate_units_v1 AS ku "
            "JOIN research_packages_v1 AS rp ON rp.id=ku.package_id "
            "WHERE rp.canonical_url=? AND ku.unit_type='research_claim' "
            "AND ku.lifecycle_status='candidate' ORDER BY ku.id LIMIT 1",
            (source,),
        ).fetchone()
    if row is None:
        raise ValueError("该资料尚未形成可学习的知识候选")
    result = start_learning(
        command_id=command_id,
        unit_id=str(row["id"]),
        reviewer_id="local-workspace",
        rationale="local workspace governed learning approval",
        db_path=database,
    )
    return {
        "source": source,
        "status": "started",
        "card_count": len(result.get("card_ids", [])),
    }


def record_practice_source(*, command_id: str, source: str, quality: int, db_path: str | Path) -> dict[str, object]:
    """Record practice by source label; artifact identity stays server-owned."""
    from app.contracts.v1 import MachineKnowledgeUnitV1

    database = Path(db_path)
    with sqlite3.connect(database, timeout=30.0) as connection:
        connection.row_factory = sqlite3.Row
        row = _workspace_source_artifact(connection, source)
    if row is None:
        raise ValueError("该资料尚未形成可练习的学习产物")
    result = record_practice(
        command_id=command_id,
        artifact_id=str(row["id"]),
        quality=quality,
        db_path=database,
    )
    machine_candidate_id = result.get("machine_candidate_id")
    if machine_candidate_id:
        with sqlite3.connect(database, timeout=30.0) as connection:
            connection.row_factory = sqlite3.Row
            candidate = connection.execute(
                "SELECT unit_json FROM machine_knowledge_candidates_v1 WHERE id=?",
                (str(machine_candidate_id),),
            ).fetchone()
            if candidate is not None:
                unit = MachineKnowledgeUnitV1.model_validate_json(str(candidate["unit_json"]))
                connection.execute(
                    "UPDATE machine_knowledge_candidates_v1 SET unit_json=? WHERE id=?",
                    (
                        unit.model_copy(update={"title": f"Reviewed learning rule · {source}"}).model_dump_json(),
                        str(machine_candidate_id),
                    ),
                )
                connection.commit()
    return {
        "source": source,
        "status": "practiced",
        "mastered": bool(result["mastered"]),
        "machine_candidate_available": bool(machine_candidate_id),
    }


def workspace_evolution(*, db_path: str | Path) -> dict[str, object]:
    """Return aggregate Mastery and machine-candidate state."""
    from app.contracts.v1 import MasterySignalV1

    with sqlite3.connect(Path(db_path), timeout=30.0) as connection:
        connection.row_factory = sqlite3.Row
        signals = connection.execute(
            "SELECT signal_json FROM mastery_signals_v1 ORDER BY calculated_at, id"
        ).fetchall()
        machine = connection.execute(
            "SELECT lifecycle_status, COUNT(*) AS count "
            "FROM machine_knowledge_candidates_v1 GROUP BY lifecycle_status"
        ).fetchall()
    mastered = sum(
        MasterySignalV1.model_validate_json(str(row["signal_json"])).is_mastered
        for row in signals
    )
    return {
        "schema_version": "v1",
        "mastery": {"signals": len(signals), "mastered": int(mastered)},
        "machine_knowledge": {str(row["lifecycle_status"]): int(row["count"]) for row in machine},
    }


def workspace_runtime_knowledge(*, db_path: str | Path) -> dict[str, object]:
    """Expose only human-approved machine knowledge to the Runtime page."""
    from app.knowledge.machine_knowledge import list_runtime_machine_knowledge

    units = list_runtime_machine_knowledge(db_path=db_path)
    return {
        "schema_version": "v1",
        "items": [
            {"title": unit.title, "content": unit.content, "lifecycle": "approved"}
            for unit in units
        ],
    }


def workspace_runtime_candidates(*, db_path: str | Path) -> dict[str, object]:
    """Return candidate and approved machine knowledge for the governance page."""
    from app.contracts.v1 import MachineKnowledgeUnitV1

    with sqlite3.connect(Path(db_path), timeout=30.0) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            "SELECT unit_json, lifecycle_status FROM machine_knowledge_candidates_v1 "
            "ORDER BY updated_at, id"
        ).fetchall()
    return {
        "schema_version": "v1",
        "items": [
            {
                "title": (unit := MachineKnowledgeUnitV1.model_validate_json(str(row["unit_json"]))).title,
                "content": unit.content,
                "lifecycle": str(row["lifecycle_status"]),
            }
            for row in rows
        ],
    }


def approve_runtime_title(*, command_id: str, title: str, db_path: str | Path) -> dict[str, object]:
    """Approve one uniquely titled machine candidate without exposing its ID."""
    from app.contracts.v1 import MachineKnowledgeUnitV1
    from app.knowledge.machine_knowledge import (
        MachineKnowledgeApproval,
        deprecate_machine_knowledge_candidate,
    )

    database = Path(db_path)
    with sqlite3.connect(database, timeout=30.0) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            "SELECT id, unit_json FROM machine_knowledge_candidates_v1 "
            "WHERE lifecycle_status='candidate' AND json_extract(unit_json, '$.title')=?",
            (title,),
        ).fetchall()
    if len(rows) != 1:
        raise ValueError("机器知识候选标题不存在或不唯一")
    unit = MachineKnowledgeUnitV1.model_validate_json(str(rows[0]["unit_json"]))
    approved = deprecate_machine_knowledge_candidate(
        MachineKnowledgeApproval(
            approval_id=command_id,
            candidate_id=str(rows[0]["id"]),
            reviewer_id="local-workspace",
            decision="approved",
            rationale="local workspace governed runtime approval",
            reviewed_at=now_utc(),
        ),
        db_path=database,
    )
    return {"title": unit.title, "status": approved.lifecycle_status}


def workspace_lifecycle(*, db_path: str | Path) -> dict[str, object]:
    """Expose aggregate Core lifecycle evidence without persistence identifiers."""

    database = Path(db_path)
    with sqlite3.connect(database, timeout=30.0) as connection:
        connection.row_factory = sqlite3.Row

        def table_exists(name: str) -> bool:
            return (
                connection.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
                    (name,),
                ).fetchone()
                is not None
            )

        traces = 0
        permission_gates = 0
        blocked_permissions = 0
        if table_exists("execution_traces"):
            trace_rows = connection.execute(
                "SELECT events_json FROM execution_traces"
            ).fetchall()
            traces = len(trace_rows)
            for row in trace_rows:
                try:
                    events = json.loads(str(row["events_json"]))
                except (TypeError, json.JSONDecodeError):
                    events = []
                permission_events = [
                    event.get("result", {})
                    for event in events
                    if isinstance(event, dict)
                    and isinstance(event.get("result"), dict)
                    and event["result"].get("tool") == "permission"
                ]
                permission_gates += bool(permission_events)
                blocked_permissions += any(
                    event.get("status") == "blocked" for event in permission_events
                )

        evaluations = 0
        approved_evaluations = 0
        if table_exists("evaluation_candidates_v1"):
            evaluations = int(
                connection.execute(
                    "SELECT COUNT(*) FROM evaluation_candidates_v1"
                ).fetchone()[0]
            )
            approved_evaluations = int(
                connection.execute(
                    "SELECT COUNT(*) FROM evaluation_candidates_v1 "
                    "WHERE status='approved'"
                ).fetchone()[0]
            )

        lessons = 0
        if table_exists("machine_lessons"):
            lessons = int(
                connection.execute("SELECT COUNT(*) FROM machine_lessons").fetchone()[0]
            )

    return {
        "schema_version": "v1",
        "privacy": "aggregate_only",
        "stages": {
            "permission": {
                "state": "blocked" if blocked_permissions else (
                    "recorded" if permission_gates else "not_recorded"
                ),
                "gates": permission_gates,
                "blocked": blocked_permissions,
            },
            "execution": {"state": "recorded" if traces else "not_recorded", "runs": traces},
            "trace": {"state": "recorded" if traces else "not_recorded", "runs": traces},
            "evaluation": {
                "state": "approved" if approved_evaluations else (
                    "candidate" if evaluations else "not_recorded"
                ),
                "candidates": evaluations,
                "approved": approved_evaluations,
            },
            "lesson": {"state": "recorded" if lessons else "not_recorded", "items": lessons},
        },
    }
