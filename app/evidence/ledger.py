"""Persisted, human-governed EvidenceBundle ledger for AXR-060-303."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from shared import knowledge_governance_migration


class EvidenceBundleError(ValueError):
    """Raised when a bundle cannot be stored or promoted under its evidence rules."""


class EvidenceBundleEntry(BaseModel):
    """One source-bound support, refutation, or unknown item in a bundle."""

    model_config = ConfigDict(extra="forbid")

    entry_id: str = Field(min_length=1)
    relation_kind: Literal["supports", "refutes", "unknown"]
    raw_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_revision: str = Field(min_length=1)
    anchor: dict[str, Any] = Field(min_length=1)
    source_lineage: str = Field(min_length=1)
    source_kind: Literal["document", "web", "model_output", "ocr"]
    valid_from: str | None = None
    valid_to: str | None = None
    scope: str = Field(min_length=1)
    rights: str = Field(min_length=1)

    @model_validator(mode="after")
    def validity_window_is_ordered(self) -> EvidenceBundleEntry:
        if self.valid_from and self.valid_to:
            try:
                valid_from = datetime.fromisoformat(self.valid_from.replace("Z", "+00:00"))
                valid_to = datetime.fromisoformat(self.valid_to.replace("Z", "+00:00"))
            except ValueError as exc:
                raise ValueError("valid_from and valid_to must be ISO-8601 timestamps") from exc
            if valid_to < valid_from:
                raise ValueError("valid_to must not be before valid_from")
        return self


class EvidenceBundleDraft(BaseModel):
    """Immutable input bundle, before an independent human review receipt exists."""

    model_config = ConfigDict(extra="forbid")

    bundle_id: str = Field(min_length=1)
    claim_id: str = Field(min_length=1)
    entries: list[EvidenceBundleEntry] = Field(min_length=1)

    @model_validator(mode="after")
    def entry_ids_are_unique(self) -> EvidenceBundleDraft:
        if len({entry.entry_id for entry in self.entries}) != len(self.entries):
            raise ValueError("bundle entry ids must be unique")
        return self


class BundleReview(BaseModel):
    """A separately persisted human decision about one immutable bundle."""

    model_config = ConfigDict(extra="forbid")

    review_id: str = Field(min_length=1)
    bundle_id: str = Field(min_length=1)
    decision: Literal["verified", "not_verifiable", "rejected"]
    reviewer_id: str = Field(min_length=1)
    rationale: str = Field(min_length=1)
    reviewed_at: str = Field(min_length=1)


class StoredEvidenceBundle(EvidenceBundleDraft):
    fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")


class StoredBundleReview(BundleReview):
    pass


def _dump(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _fingerprint(draft: EvidenceBundleDraft) -> str:
    payload = {
        "claim_id": draft.claim_id,
        "entries": [
            entry.model_dump(mode="json")
            for entry in sorted(draft.entries, key=lambda item: item.entry_id)
        ],
    }
    return sha256(_dump(payload).encode("utf-8")).hexdigest()


def _connect(database: Path) -> sqlite3.Connection:
    knowledge_governance_migration.require_applied(db_path=database, live_wal=True)
    connection = sqlite3.connect(database)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys=ON")
    return connection


def _get_bundle(connection: sqlite3.Connection, bundle_id: str) -> StoredEvidenceBundle:
    header = connection.execute(
        "SELECT id, claim_id, bundle_fingerprint FROM evidence_bundles_v1 WHERE id=?",
        (bundle_id,),
    ).fetchone()
    if header is None:
        raise EvidenceBundleError(f"unknown evidence bundle: {bundle_id}")
    rows = connection.execute(
        "SELECT id, relation_kind, raw_sha256, source_revision, anchor_json, source_lineage, "
        "source_kind, valid_from, valid_to, scope, rights "
        "FROM evidence_bundle_entries_v1 WHERE bundle_id=? ORDER BY created_at, id",
        (bundle_id,),
    ).fetchall()
    return StoredEvidenceBundle(
        bundle_id=str(header["id"]),
        claim_id=str(header["claim_id"]),
        fingerprint=str(header["bundle_fingerprint"]),
        entries=[
            EvidenceBundleEntry(
                entry_id=str(row["id"]),
                relation_kind=str(row["relation_kind"]),
                raw_sha256=str(row["raw_sha256"]),
                source_revision=str(row["source_revision"]),
                anchor=json.loads(str(row["anchor_json"])),
                source_lineage=str(row["source_lineage"]),
                source_kind=str(row["source_kind"]),
                valid_from=row["valid_from"],
                valid_to=row["valid_to"],
                scope=str(row["scope"]),
                rights=str(row["rights"]),
            )
            for row in rows
        ],
    )


def store_bundle(draft: EvidenceBundleDraft, *, db_path: str | Path) -> StoredEvidenceBundle:
    """Store one immutable bundle and its source entries, or reject identity reuse."""

    database = Path(db_path)
    fingerprint = _fingerprint(draft)
    with _connect(database) as connection:
        connection.execute("BEGIN IMMEDIATE")
        try:
            existing = connection.execute(
                "SELECT id, bundle_fingerprint FROM evidence_bundles_v1 "
                "WHERE id=? OR bundle_fingerprint=?",
                (draft.bundle_id, fingerprint),
            ).fetchone()
            if existing is not None:
                if (
                    str(existing["id"]) == draft.bundle_id
                    and str(existing["bundle_fingerprint"]) == fingerprint
                ):
                    connection.rollback()
                    return _get_bundle(connection, draft.bundle_id)
                raise EvidenceBundleError("evidence bundle identity already exists with different content")
            connection.execute(
                "INSERT INTO evidence_bundles_v1 (id, claim_id, bundle_fingerprint, created_at) "
                "VALUES (?, ?, ?, datetime('now'))",
                (draft.bundle_id, draft.claim_id, fingerprint),
            )
            for entry in draft.entries:
                connection.execute(
                    "INSERT INTO evidence_bundle_entries_v1 "
                    "(id, bundle_id, relation_kind, raw_sha256, source_revision, anchor_json, "
                    "source_lineage, source_kind, valid_from, valid_to, scope, rights, created_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))",
                    (
                        entry.entry_id,
                        draft.bundle_id,
                        entry.relation_kind,
                        entry.raw_sha256,
                        entry.source_revision,
                        _dump(entry.anchor),
                        entry.source_lineage,
                        entry.source_kind,
                        entry.valid_from,
                        entry.valid_to,
                        entry.scope,
                        entry.rights,
                    ),
                )
            connection.commit()
        except Exception:
            connection.rollback()
            raise
    return get_bundle(draft.bundle_id, db_path=database)


def get_bundle(bundle_id: str, *, db_path: str | Path) -> StoredEvidenceBundle:
    """Read an immutable bundle through a new database connection."""

    with _connect(Path(db_path)) as connection:
        return _get_bundle(connection, bundle_id)


def _require_verifiable(entries: list[EvidenceBundleEntry]) -> None:
    if len({entry.source_lineage for entry in entries}) < 2:
        raise EvidenceBundleError("verified bundle requires at least two independent source lineages")


def review_bundle(review: BundleReview, *, db_path: str | Path) -> StoredBundleReview:
    """Append one human review receipt; only reviewed independent bundles can verify."""

    database = Path(db_path)
    with _connect(database) as connection:
        connection.execute("BEGIN IMMEDIATE")
        try:
            bundle = _get_bundle(connection, review.bundle_id)
            if review.decision == "verified":
                _require_verifiable(bundle.entries)
            duplicate = connection.execute(
                "SELECT id FROM evidence_bundle_reviews_v1 WHERE id=?", (review.review_id,)
            ).fetchone()
            if duplicate is not None:
                raise EvidenceBundleError(f"evidence bundle review already exists: {review.review_id}")
            connection.execute(
                "INSERT INTO evidence_bundle_reviews_v1 "
                "(id, bundle_id, decision, reviewer_id, rationale, reviewed_at, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, datetime('now'))",
                (
                    review.review_id,
                    review.bundle_id,
                    review.decision,
                    review.reviewer_id,
                    review.rationale,
                    review.reviewed_at,
                ),
            )
            connection.commit()
        except Exception:
            connection.rollback()
            raise
    return StoredBundleReview(**review.model_dump())


def get_reviewed_bundle_on_connection(
    bundle_id: str, connection: sqlite3.Connection
) -> StoredEvidenceBundle:
    """Read one verified bundle without opening a nested transaction."""

    _bundle, review = get_human_reviewed_bundle_on_connection(bundle_id, connection)
    if review.decision != "verified":
        raise EvidenceBundleError(f"evidence bundle review is {review.decision}")
    return _bundle


def get_human_reviewed_bundle_on_connection(
    bundle_id: str, connection: sqlite3.Connection
) -> tuple[StoredEvidenceBundle, StoredBundleReview]:
    """Read any human-reviewed bundle, including not-verifiable candidates."""

    review = connection.execute(
        "SELECT id, bundle_id, decision, reviewer_id, rationale, reviewed_at "
        "FROM evidence_bundle_reviews_v1 WHERE bundle_id=? "
        "ORDER BY reviewed_at DESC, id DESC LIMIT 1",
        (bundle_id,),
    ).fetchone()
    if review is None:
        raise EvidenceBundleError("evidence bundle has no human review")
    return (
        _get_bundle(connection, bundle_id),
        StoredBundleReview(
            review_id=str(review["id"]),
            bundle_id=str(review["bundle_id"]),
            decision=str(review["decision"]),
            reviewer_id=str(review["reviewer_id"]),
            rationale=str(review["rationale"]),
            reviewed_at=str(review["reviewed_at"]),
        ),
    )


def get_reviewed_bundle(bundle_id: str, *, db_path: str | Path) -> StoredEvidenceBundle:
    """Return a bundle only when its latest human review is explicitly verified."""

    with _connect(Path(db_path)) as connection:
        return get_reviewed_bundle_on_connection(bundle_id, connection)
