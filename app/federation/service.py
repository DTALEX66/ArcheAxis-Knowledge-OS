"""Federation knowledge service — ArcheAxis-owned candidate/verified boundary.

Implements the stable knowledge API (AA-P0-002) and external asset registry
(AA-P1-001) with the TP-20260819 contract shape:

    submit_candidates (batch, idempotent) → receipt (hash readback)
    get_receipt / promote_to_verified (human-governed) / query_verified (paginated)
    register_external_asset / list_external_assets (records only, no file copies)

Governance: candidates NEVER auto-promote to verified; AI content defaults to
candidate until human review (AA-P0-003). All writes append-only with receipts.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any

from app.contracts.federation_v1 import (
    CandidateReceiptV1,
    CandidateSubmissionV1,
    EvidenceIntakeV1,
    ExternalAssetRecordV1,
    KnowledgeProjectionV1,
    KnowledgeQueryV1,
    LearningRecordV1,
    ProvenanceRecordV1,
    ReviewDecisionV1,
    RightsRecordV1,
)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS federation_candidates_v1 (
    id TEXT PRIMARY KEY,
    submission_id TEXT NOT NULL,
    idempotency_key TEXT NOT NULL,
    item_key TEXT NOT NULL,
    submitter TEXT NOT NULL,
    claim TEXT NOT NULL,
    source_ref TEXT NOT NULL,
    confidence REAL NOT NULL DEFAULT 0.5,
    kind TEXT NOT NULL DEFAULT 'fact',
    rights TEXT NOT NULL DEFAULT 'unspecified',
    status TEXT NOT NULL DEFAULT 'candidate',   -- candidate | verified | rejected
    verified_at TEXT,
    reviewer TEXT,
    revision INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    UNIQUE (idempotency_key, item_key)
);
CREATE INDEX IF NOT EXISTS idx_fc_status ON federation_candidates_v1(status);

CREATE TABLE IF NOT EXISTS federation_receipts_v1 (
    submission_id TEXT PRIMARY KEY,
    idempotency_key TEXT NOT NULL,
    status TEXT NOT NULL,
    accepted INTEGER NOT NULL,
    rejected INTEGER NOT NULL,
    items_hash TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS external_asset_records_v1 (
    asset_id TEXT PRIMARY KEY,
    uri TEXT NOT NULL,
    hash TEXT NOT NULL,
    media_type TEXT NOT NULL,
    source TEXT NOT NULL,
    rights TEXT NOT NULL,
    extraction_json TEXT NOT NULL,
    derived_ids_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS federation_candidate_events_v1 (
    event_id TEXT PRIMARY KEY,
    candidate_id TEXT NOT NULL,
    version INTEGER NOT NULL,
    decision TEXT NOT NULL,
    actor TEXT NOT NULL,
    rationale TEXT NOT NULL,
    idempotency_key TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(candidate_id, version),
    UNIQUE(candidate_id, idempotency_key)
);
CREATE INDEX IF NOT EXISTS idx_fce_candidate_version
    ON federation_candidate_events_v1(candidate_id, version DESC);
"""


class FederationError(ValueError):
    """Raised when a federation operation is invalid."""


@dataclass(frozen=True)
class SubmissionResult:
    receipt: CandidateReceiptV1
    duplicate: bool


def _connect(db: str | Path) -> sqlite3.Connection:
    path = Path(db)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(_SCHEMA)
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(federation_candidates_v1)")}
    if "revision" not in columns:
        conn.execute(
            "ALTER TABLE federation_candidates_v1 ADD COLUMN revision INTEGER NOT NULL DEFAULT 1"
        )
    return conn


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _stable_id(namespace: str, *parts: str) -> str:
    payload = "\0".join(parts).encode("utf-8")
    return f"{namespace}_{sha256(payload).hexdigest()[:24]}"


def _items_hash(submission: CandidateSubmissionV1) -> str:
    canonical = json.dumps(
        [item.model_dump() for item in submission.items],
        ensure_ascii=False, sort_keys=True,
    )
    return sha256(canonical.encode("utf-8")).hexdigest()


# ── candidate submission / receipt ───────────────────────────────────

def submit_candidates(db: str | Path, submission: CandidateSubmissionV1) -> SubmissionResult:
    """Batch candidate submission with idempotency (AA-P0-002)."""
    if not submission.items:
        raise FederationError("submission requires at least one item")
    items_hash = _items_hash(submission)
    now = _now()
    with _connect(db) as conn:
        existing = conn.execute(
            "SELECT submission_id FROM federation_receipts_v1 WHERE idempotency_key=?",
            (submission.idempotency_key,),
        ).fetchone()
        if existing is not None:
            row = conn.execute(
                "SELECT * FROM federation_receipts_v1 WHERE submission_id=?",
                (existing["submission_id"],),
            ).fetchone()
            return SubmissionResult(receipt=_row_to_receipt(row), duplicate=True)

        submission_id = _stable_id("fedsub", submission.idempotency_key, now)
        accepted = 0
        for item in submission.items:
            candidate_id = _stable_id("fedcand", submission.idempotency_key, item.item_key)
            inserted = conn.execute(
                "INSERT OR IGNORE INTO federation_candidates_v1 "
                "(id, submission_id, idempotency_key, item_key, submitter, claim, source_ref, "
                "confidence, kind, rights, status, verified_at, reviewer, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'candidate', NULL, NULL, ?)",
                (candidate_id, submission_id, submission.idempotency_key, item.item_key,
                 submission.submitter, item.claim, item.source_ref, item.confidence,
                 item.kind, item.rights, now),
            )
            if inserted.rowcount:
                conn.execute(
                    "INSERT INTO federation_candidate_events_v1 "
                    "(event_id, candidate_id, version, decision, actor, rationale, idempotency_key, created_at) "
                    "VALUES (?, ?, 1, 'candidate', ?, 'initial candidate submission', ?, ?)",
                    (
                        _stable_id("fedevent", candidate_id, "1"),
                        candidate_id,
                        submission.submitter,
                        submission.idempotency_key,
                        now,
                    ),
                )
                accepted += 1
        conn.execute(
            "INSERT INTO federation_receipts_v1 (submission_id, idempotency_key, status, "
            "accepted, rejected, items_hash, created_at) VALUES (?, ?, 'accepted', ?, 0, ?, ?)",
            (submission_id, submission.idempotency_key, accepted, items_hash, now),
        )
        row = conn.execute(
            "SELECT * FROM federation_receipts_v1 WHERE submission_id=?",
            (submission_id,),
        ).fetchone()
    return SubmissionResult(receipt=_row_to_receipt(row), duplicate=False)


def _row_to_receipt(row: sqlite3.Row) -> CandidateReceiptV1:
    return CandidateReceiptV1(
        submission_id=row["submission_id"], idempotency_key=row["idempotency_key"],
        status=row["status"], accepted=row["accepted"], rejected=row["rejected"],
        items_hash=row["items_hash"], created_at=row["created_at"],
    )


def get_receipt(db: str | Path, submission_id: str) -> CandidateReceiptV1:
    with _connect(db) as conn:
        row = conn.execute(
            "SELECT * FROM federation_receipts_v1 WHERE submission_id=?",
            (submission_id,),
        ).fetchone()
    if row is None:
        raise FederationError(f"receipt not found: {submission_id}")
    return _row_to_receipt(row)


# ── verified promotion (human-governed) / query ──────────────────────

_ALLOWED_REVIEW_TRANSITIONS = {
    "candidate": {"verified", "rejected", "disputed"},
    "verified": {"deprecated", "revoked", "disputed"},
    "rejected": {"disputed"},
    "disputed": {"verified", "rejected", "deprecated", "revoked"},
    "deprecated": {"revoked"},
    "revoked": set(),
}


def review_candidate(
    db: str | Path, candidate_id: str, decision: ReviewDecisionV1
) -> dict[str, object]:
    """Append and project one authenticated human review decision.

    The immutable event table is authoritative.  The candidate row is only a
    query projection kept in the same transaction for older consumers.
    """
    with _connect(db) as conn:
        row = conn.execute(
            "SELECT * FROM federation_candidates_v1 WHERE id=?", (candidate_id,)
        ).fetchone()
        if row is None:
            raise FederationError(f"candidate not found: {candidate_id}")
        current_status = str(row["status"])
        current_version = int(row["revision"])
        duplicate = conn.execute(
            "SELECT * FROM federation_candidate_events_v1 "
            "WHERE candidate_id=? AND idempotency_key=?",
            (candidate_id, decision.idempotency_key),
        ).fetchone()
        if duplicate is not None:
            if (
                duplicate["decision"] != decision.decision
                or duplicate["actor"] != decision.reviewer_id
                or duplicate["rationale"] != decision.rationale
            ):
                raise FederationError("idempotency key was already used for a different decision")
            return {
                "candidate_id": candidate_id,
                "status": duplicate["decision"],
                "version": int(duplicate["version"]),
                "duplicate": True,
            }
        if decision.expected_version != current_version:
            raise FederationError(
                f"review version conflict: expected {decision.expected_version}, current {current_version}"
            )
        if decision.decision not in _ALLOWED_REVIEW_TRANSITIONS.get(current_status, set()):
            raise FederationError(
                f"invalid review transition: {current_status} -> {decision.decision}"
            )
        next_version = current_version + 1
        now = _now()
        conn.execute(
            "INSERT INTO federation_candidate_events_v1 "
            "(event_id, candidate_id, version, decision, actor, rationale, idempotency_key, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                _stable_id("fedevent", candidate_id, str(next_version), decision.idempotency_key),
                candidate_id,
                next_version,
                decision.decision,
                decision.reviewer_id,
                decision.rationale,
                decision.idempotency_key,
                now,
            ),
        )
        conn.execute(
            "UPDATE federation_candidates_v1 SET status=?, verified_at=?, reviewer=?, revision=? WHERE id=?",
            (
                decision.decision,
                now if decision.decision == "verified" else None,
                decision.reviewer_id,
                next_version,
                candidate_id,
            ),
        )
    return {
        "candidate_id": candidate_id,
        "status": decision.decision,
        "version": next_version,
        "duplicate": False,
    }


def promote_to_verified(db: str | Path, candidate_id: str, *, reviewer: str) -> None:
    """Legacy service wrapper; API callers must use :func:`review_candidate`."""
    with _connect(db) as conn:
        row = conn.execute(
            "SELECT revision FROM federation_candidates_v1 WHERE id=?", (candidate_id,)
        ).fetchone()
    if row is None:
        raise FederationError(f"candidate not found: {candidate_id}")
    review_candidate(
        db,
        candidate_id,
        ReviewDecisionV1(
            decision="verified",
            reviewer_id=reviewer,
            rationale="legacy service promotion wrapper",
            expected_version=int(row["revision"]),
            idempotency_key=f"legacy-promote:{candidate_id}:{row['revision']}",
        ),
    )


def query_verified(db: str | Path, request: KnowledgeQueryV1) -> KnowledgeProjectionV1:
    """Paginated verified-knowledge readback with evidence anchors."""
    if request.kind == "candidate":
        status_filter = ("candidate",)
    elif request.kind == "verified":
        status_filter = ("verified",)
    else:
        status_filter = ("candidate", "verified")
    query = f"%{request.query}%"
    with _connect(db) as conn:
        rows = conn.execute(
            "SELECT * FROM federation_candidates_v1 WHERE status IN "
            f"({','.join('?' for _ in status_filter)}) AND claim LIKE ? "
            "ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (*status_filter, query, request.page_size, (request.page - 1) * request.page_size),
        ).fetchall()
        total_row = conn.execute(
            "SELECT COUNT(*) AS n FROM federation_candidates_v1 WHERE status IN "
            f"({','.join('?' for _ in status_filter)}) AND claim LIKE ?",
            (*status_filter, query),
        ).fetchone()
    items = [
        {
            "id": row["id"], "claim": row["claim"], "source_ref": row["source_ref"],
            "confidence": row["confidence"], "kind": row["kind"], "status": row["status"],
            "verified_at": row["verified_at"], "reviewer": row["reviewer"],
            "rights": row["rights"],
        }
        for row in rows
    ]
    return KnowledgeProjectionV1(query=request.query, page=request.page,
                                 page_size=request.page_size, total=int(total_row["n"]),
                                 items=items)


# ── external asset records (AA-P1-001) ───────────────────────────────

def register_external_asset(db: str | Path, record: ExternalAssetRecordV1) -> str:
    """Register an external asset RECORD without silently overwriting history."""
    with _connect(db) as conn:
        existing = conn.execute(
            "SELECT * FROM external_asset_records_v1 WHERE asset_id=?", (record.asset_id,)
        ).fetchone()
        extraction = json.dumps(record.extraction, ensure_ascii=False, sort_keys=True)
        derived_ids = json.dumps(record.derived_ids, ensure_ascii=False)
        if existing is not None:
            if (
                existing["uri"] != record.uri
                or existing["hash"] != record.hash
                or existing["media_type"] != record.media_type
                or existing["source"] != record.source
                or existing["rights"] != record.rights
                or existing["extraction_json"] != extraction
                or existing["derived_ids_json"] != derived_ids
            ):
                raise FederationError("external asset id already exists with different content")
            return record.asset_id
        conn.execute(
            "INSERT INTO external_asset_records_v1 "
            "(asset_id, uri, hash, media_type, source, rights, extraction_json, derived_ids_json, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (record.asset_id, record.uri, record.hash, record.media_type, record.source,
             record.rights, extraction, derived_ids,
             record.created_at or _now()),
        )
    return record.asset_id


def list_external_assets(db: str | Path, *, limit: int = 50) -> list[dict[str, Any]]:
    with _connect(db) as conn:
        rows = conn.execute(
            "SELECT * FROM external_asset_records_v1 ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [
        {"asset_id": row["asset_id"], "uri": row["uri"], "hash": row["hash"],
         "media_type": row["media_type"], "source": row["source"], "rights": row["rights"],
         "extraction": json.loads(row["extraction_json"]),
         "derived_ids": json.loads(row["derived_ids_json"]),
         "created_at": row["created_at"]}
        for row in rows
    ]


def hash_readback(db: str | Path, entity_id: str) -> dict[str, Any]:
    """Hash readback (AA-P0-002): stable content hash for a candidate record."""
    with _connect(db) as conn:
        row = conn.execute(
            "SELECT id, idempotency_key, claim, source_ref FROM federation_candidates_v1 WHERE id=?",
            (entity_id,),
        ).fetchone()
        if row is None:
            raise FederationError(f"entity not found: {entity_id}")
        content_hash = sha256(
            f"{row['id']}:{row['idempotency_key']}:{row['claim']}:{row['source_ref']}".encode()
        ).hexdigest()
        return {"entity_id": entity_id, "content_hash": content_hash,
                "claim": row["claim"], "source_ref": row["source_ref"]}


# ── record types (EvidenceIntake / LearningRecord / Provenance / Rights) ──
# Append-only record tables for the federation boundary (AA-P0-002 completion).

_RECORD_KIND_TABLES = {
    "evidence": "federation_evidence_records_v1",
    "learning": "federation_learning_records_v1",
    "provenance": "federation_provenance_records_v1",
    "rights": "federation_rights_records_v1",
}

_RECORD_CREATE_SQL_ALLOWLIST = {
    "federation_evidence_records_v1": """
        CREATE TABLE IF NOT EXISTS federation_evidence_records_v1 (
            record_id TEXT PRIMARY KEY, source_ref TEXT NOT NULL, anchor_json TEXT NOT NULL,
            content_hash TEXT NOT NULL, rights TEXT NOT NULL, verified INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        )
    """,
    "federation_learning_records_v1": """
        CREATE TABLE IF NOT EXISTS federation_learning_records_v1 (
            record_id TEXT PRIMARY KEY, concept TEXT NOT NULL, kind TEXT NOT NULL,
            outcome_json TEXT NOT NULL, source_ref TEXT NOT NULL, created_at TEXT NOT NULL
        )
    """,
    "federation_provenance_records_v1": """
        CREATE TABLE IF NOT EXISTS federation_provenance_records_v1 (
            record_id TEXT PRIMARY KEY, entity_id TEXT NOT NULL, event TEXT NOT NULL,
            actor TEXT NOT NULL, at TEXT NOT NULL, parent_id TEXT, reason TEXT, created_at TEXT NOT NULL
        )
    """,
    "federation_rights_records_v1": """
        CREATE TABLE IF NOT EXISTS federation_rights_records_v1 (
            record_id TEXT PRIMARY KEY, entity_id TEXT NOT NULL, rights TEXT NOT NULL,
            scope TEXT NOT NULL DEFAULT 'internal', source_ref TEXT, created_at TEXT NOT NULL
        )
    """,
}

_RECORD_COLUMNS = {
    "federation_evidence_records_v1": (
        "record_id", "source_ref", "anchor_json", "content_hash", "rights", "verified", "created_at",
    ),
    "federation_learning_records_v1": (
        "record_id", "concept", "kind", "outcome_json", "source_ref", "created_at",
    ),
    "federation_provenance_records_v1": (
        "record_id", "entity_id", "event", "actor", "at", "parent_id", "reason", "created_at",
    ),
    "federation_rights_records_v1": (
        "record_id", "entity_id", "rights", "scope", "source_ref", "created_at",
    ),
}

_RECORD_INSERT_SQL_ALLOWLIST = {
    table: f"INSERT INTO {table} ({','.join(columns)}) VALUES ({','.join('?' for _ in columns)})"
    for table, columns in _RECORD_COLUMNS.items()
}
_RECORD_SELECT_SQL_ALLOWLIST = {
    table: f"SELECT * FROM {table} ORDER BY created_at DESC LIMIT ?"
    for table in _RECORD_COLUMNS
}


def _create_append_only_triggers(conn: sqlite3.Connection) -> None:
    """Install mutation guards only for tables in the static record allowlist."""
    for table in _RECORD_COLUMNS:
        for operation, verb in (("UPDATE", "updated"), ("DELETE", "deleted")):
            conn.execute(
                f"CREATE TRIGGER IF NOT EXISTS {table}_append_only_no_{operation.lower()} "
                f"BEFORE {operation} ON {table} "
                "BEGIN "
                f"SELECT RAISE(ABORT, 'append-only record cannot be {verb}'); "
                "END"
            )


def _ensure_record_tables(conn: sqlite3.Connection) -> None:
    """Atomically apply the allowlisted record schema and its forward migration.

    Version one provenance tables lack ``reason``.  The only supported data
    migration is additive; a failed installation rolls the entire transaction
    back, while a successful record write is never schema-downgraded because
    that could discard evidence history.
    """
    conn.execute("BEGIN IMMEDIATE")
    try:
        for statement in _RECORD_CREATE_SQL_ALLOWLIST.values():
            conn.execute(statement)
        columns = {
            str(row[1])
            for row in conn.execute("PRAGMA table_info(federation_provenance_records_v1)")
        }
        if "reason" not in columns:
            conn.execute("ALTER TABLE federation_provenance_records_v1 ADD COLUMN reason TEXT")
        _create_append_only_triggers(conn)
    except Exception:
        conn.rollback()
        raise
    else:
        conn.commit()


def _append_record(conn: sqlite3.Connection, table: str, record_id: str, values: tuple[Any, ...]) -> None:
    columns = _RECORD_COLUMNS.get(table)
    statement = _RECORD_INSERT_SQL_ALLOWLIST.get(table)
    if columns is None or statement is None:
        raise FederationError(f"append-only table is not allowlisted: {table}")
    if len(columns) != len(values):
        raise ValueError(f"append-only record shape mismatch: {table}")
    try:
        conn.execute(statement, values)
    except sqlite3.IntegrityError as exc:
        raise FederationError(f"append-only record already exists: {record_id}") from exc


def record_evidence(db: str | Path, record: EvidenceIntakeV1) -> str:
    """Evidence intake (append-only) — evidence object with anchor + hash."""
    with _connect(db) as conn:
        _ensure_record_tables(conn)
        _append_record(
            conn,
            "federation_evidence_records_v1",
            record.evidence_id,
            (record.evidence_id, record.source_ref, json.dumps(record.anchor, ensure_ascii=False),
             record.content_hash, record.rights, int(record.verified), _now()),
        )
    return record.evidence_id


def record_learning(db: str | Path, record: LearningRecordV1) -> str:
    """Human learning record (append-only) — review/quiz/teach_back/mastery."""
    with _connect(db) as conn:
        _ensure_record_tables(conn)
        _append_record(
            conn,
            "federation_learning_records_v1",
            record.record_id,
            (record.record_id, record.concept, record.kind,
             json.dumps(record.outcome, ensure_ascii=False), record.source_ref, _now()),
        )
    return record.record_id


def record_provenance(db: str | Path, record: ProvenanceRecordV1) -> str:
    """Provenance event (append-only) — created/promoted/revoked/superseded."""
    with _connect(db) as conn:
        _ensure_record_tables(conn)
        _append_record(
            conn,
            "federation_provenance_records_v1",
            record.record_id,
            (record.record_id, record.entity_id, record.event, record.actor, record.at,
             record.parent_id, record.reason, _now()),
        )
    return record.record_id


def record_rights(db: str | Path, record: RightsRecordV1) -> str:
    """Rights/permission record (append-only)."""
    with _connect(db) as conn:
        _ensure_record_tables(conn)
        _append_record(
            conn,
            "federation_rights_records_v1",
            record.record_id,
            (record.record_id, record.entity_id, record.rights, record.scope,
             record.source_ref, _now()),
        )
    return record.record_id


def list_records(db: str | Path, kind: str, *, limit: int = 50) -> list[dict[str, Any]]:
    """List latest records of a kind (evidence|learning|provenance|rights)."""
    table = _RECORD_KIND_TABLES[kind]
    with _connect(db) as conn:
        _ensure_record_tables(conn)
        rows = conn.execute(_RECORD_SELECT_SQL_ALLOWLIST[table], (limit,)).fetchall()
    return [dict(r) for r in rows]
