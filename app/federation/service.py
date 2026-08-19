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
    ExternalAssetRecordV1,
    KnowledgeProjectionV1,
    KnowledgeQueryV1,
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
"""


class FederationError(ValueError):
    """Raised when a federation operation is invalid."""


@dataclass(frozen=True)
class SubmissionResult:
    receipt: CandidateReceiptV1
    duplicate: bool


def _connect(db: str | Path) -> sqlite3.Connection:
    conn = sqlite3.connect(Path(db))
    conn.row_factory = sqlite3.Row
    conn.executescript(_SCHEMA)
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
            conn.execute(
                "INSERT OR IGNORE INTO federation_candidates_v1 "
                "(id, submission_id, idempotency_key, item_key, submitter, claim, source_ref, "
                "confidence, kind, rights, status, verified_at, reviewer, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'candidate', NULL, NULL, ?)",
                (candidate_id, submission_id, submission.idempotency_key, item.item_key,
                 submission.submitter, item.claim, item.source_ref, item.confidence,
                 item.kind, item.rights, now),
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

def promote_to_verified(db: str | Path, candidate_id: str, *, reviewer: str) -> None:
    """Human-governed promotion: candidate -> verified (AA-P0-003: never auto)."""
    with _connect(db) as conn:
        row = conn.execute(
            "SELECT * FROM federation_candidates_v1 WHERE id=?", (candidate_id,)
        ).fetchone()
        if row is None:
            raise FederationError(f"candidate not found: {candidate_id}")
        if row["status"] != "candidate":
            raise FederationError("only candidates can be promoted")
        conn.execute(
            "UPDATE federation_candidates_v1 SET status='verified', verified_at=?, reviewer=? "
            "WHERE id=?",
            (_now(), reviewer, candidate_id),
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
    """Register an external asset RECORD (URI/hash only; never copies the file)."""
    with _connect(db) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO external_asset_records_v1 "
            "(asset_id, uri, hash, media_type, source, rights, extraction_json, derived_ids_json, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (record.asset_id, record.uri, record.hash, record.media_type, record.source,
             record.rights, json.dumps(record.extraction, ensure_ascii=False),
             json.dumps(record.derived_ids, ensure_ascii=False),
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
