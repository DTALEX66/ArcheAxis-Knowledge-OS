"""AXR-060-303 persisted, human-governed EvidenceBundle ledger."""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path

import pytest
from pydantic import ValidationError


def _migrated_database(tmp_path: Path) -> Path:
    from shared.migration_runner import MigrationOperator

    database = tmp_path / "knowledge.sqlite"
    database.touch()
    MigrationOperator(db_path=database, backup_dir=tmp_path / "backups").apply(
        "knowledge-governance.sqlite"
    )
    return database


def _entry(
    entry_id: str,
    *,
    relation_kind: str = "supports",
    source_lineage: str = "publisher-a",
    source_kind: str = "document",
    raw_sha256: str | None = None,
):
    from app.evidence.ledger import EvidenceBundleEntry

    return EvidenceBundleEntry(
        entry_id=entry_id,
        relation_kind=relation_kind,
        raw_sha256=raw_sha256 or sha256(entry_id.encode("utf-8")).hexdigest(),
        source_revision="2026-08-20T00:00:00Z",
        anchor={"page": 3, "quote": "evidence text"},
        source_lineage=source_lineage,
        source_kind=source_kind,
        valid_from="2026-08-20T00:00:00Z",
        valid_to=None,
        scope="education",
        rights="cc-by-4.0",
    )


def test_persisted_bundle_keeps_anchor_rights_scope_and_timing_after_readback(tmp_path: Path):
    from app.evidence.ledger import EvidenceBundleDraft, get_bundle, store_bundle

    database = _migrated_database(tmp_path)
    stored = store_bundle(
        EvidenceBundleDraft(
            bundle_id="bundle-1",
            claim_id="claim-1",
            entries=[
                _entry("entry-a", source_lineage="publisher-a"),
                _entry("entry-b", relation_kind="unknown", source_lineage="publisher-b"),
            ],
        ),
        db_path=database,
    )

    restored = get_bundle(stored.bundle_id, db_path=database)
    assert restored.fingerprint == stored.fingerprint
    assert restored.entries[0].anchor == {"page": 3, "quote": "evidence text"}
    assert restored.entries[0].rights == "cc-by-4.0"
    assert restored.entries[0].scope == "education"
    assert restored.entries[0].valid_from == "2026-08-20T00:00:00Z"
    assert {entry.relation_kind for entry in restored.entries} == {"supports", "unknown"}


def test_verified_bundle_requires_independent_sources_and_rejects_single_web_model_or_ocr(tmp_path: Path):
    from app.evidence.ledger import (
        BundleReview,
        EvidenceBundleDraft,
        EvidenceBundleError,
        review_bundle,
        store_bundle,
    )

    database = _migrated_database(tmp_path)
    store_bundle(
        EvidenceBundleDraft(bundle_id="single-web", claim_id="claim-1", entries=[_entry("entry-c", source_kind="web")]),
        db_path=database,
    )

    with pytest.raises(EvidenceBundleError, match="independent source lineages"):
        review_bundle(
            BundleReview(
                review_id="review-1", bundle_id="single-web", decision="verified",
                reviewer_id="human-1", rationale="one page is sufficient", reviewed_at="2026-08-20T01:00:00Z",
            ),
            db_path=database,
        )

    for source_kind in ("model_output", "ocr"):
        bundle_id = f"single-{source_kind}"
        store_bundle(
            EvidenceBundleDraft(bundle_id=bundle_id, claim_id="claim-1", entries=[_entry(f"entry-{source_kind[-1]}", source_kind=source_kind)]),
            db_path=database,
        )
        with pytest.raises(EvidenceBundleError, match="independent source lineages"):
            review_bundle(
                BundleReview(
                    review_id=f"review-{source_kind}", bundle_id=bundle_id, decision="verified",
                    reviewer_id="human-1", rationale="one source", reviewed_at="2026-08-20T01:00:00Z",
                ),
                db_path=database,
            )


def test_human_reviewed_bundle_is_verified_and_not_verifiable_never_upgrades(tmp_path: Path):
    from app.evidence.ledger import (
        BundleReview,
        EvidenceBundleDraft,
        EvidenceBundleError,
        get_reviewed_bundle,
        review_bundle,
        store_bundle,
    )

    database = _migrated_database(tmp_path)
    store_bundle(
        EvidenceBundleDraft(
            bundle_id="bundle-verified", claim_id="claim-1",
            entries=[_entry("entry-d", source_lineage="publisher-a"), _entry("entry-e", source_lineage="publisher-b")],
        ),
        db_path=database,
    )
    reviewed = review_bundle(
        BundleReview(
            review_id="review-verified", bundle_id="bundle-verified", decision="verified",
            reviewer_id="human-1", rationale="independent source review", reviewed_at="2026-08-20T01:00:00Z",
        ),
        db_path=database,
    )
    assert reviewed.decision == "verified"
    assert get_reviewed_bundle("bundle-verified", db_path=database).fingerprint

    store_bundle(
        EvidenceBundleDraft(bundle_id="bundle-private", claim_id="claim-private", entries=[_entry("entry-f")]),
        db_path=database,
    )
    review_bundle(
        BundleReview(
            review_id="review-private", bundle_id="bundle-private", decision="not_verifiable",
            reviewer_id="human-1", rationale="private subjective statement", reviewed_at="2026-08-20T01:00:00Z",
        ),
        db_path=database,
    )
    with pytest.raises(EvidenceBundleError, match="not_verifiable"):
        get_reviewed_bundle("bundle-private", db_path=database)


def test_bundle_identity_cannot_be_overwritten(tmp_path: Path):
    from app.evidence.ledger import EvidenceBundleDraft, EvidenceBundleError, store_bundle

    database = _migrated_database(tmp_path)
    store_bundle(EvidenceBundleDraft(bundle_id="bundle-immutable", claim_id="claim-1", entries=[_entry("entry-g")]), db_path=database)
    with pytest.raises(EvidenceBundleError, match="different content"):
        store_bundle(EvidenceBundleDraft(bundle_id="bundle-immutable", claim_id="claim-1", entries=[_entry("entry-h")]), db_path=database)


def test_entry_rejects_invalid_hash_and_inverted_validity_window():
    from app.evidence.ledger import EvidenceBundleEntry

    with pytest.raises(ValidationError, match="raw_sha256"):
        _entry("entry-valid", raw_sha256="z" * 64)
    with pytest.raises(ValidationError, match="valid_to"):
        EvidenceBundleEntry(
            entry_id="entry-time",
            relation_kind="supports",
            raw_sha256=sha256(b"entry-time").hexdigest(),
            source_revision="2026-08-20T00:00:00Z",
            anchor={"page": 3},
            source_lineage="publisher-a",
            source_kind="document",
            valid_from="2026-08-21T00:00:00Z",
            valid_to="2026-08-20T00:00:00Z",
            scope="education",
            rights="cc-by-4.0",
        )
