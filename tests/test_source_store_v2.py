"""Durable Source/Anchor/PROV V2 storage and stale-state readback."""
from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from app.contracts.source_anchor_v2 import (
    AnchorV2,
    ProvenanceActivityV2,
    SourceObjectV2,
    TextQuoteSelector,
)
from app.evidence.source_store_v2 import SourceConflictError, SourceStoreV2
from shared.migration_runner import MigrationOperator


def _db(tmp_path: Path) -> Path:
    db = tmp_path / "source.sqlite"
    db.touch()
    MigrationOperator(db_path=db, backup_dir=tmp_path / "backups").apply(
        "knowledge-governance.sqlite"
    )
    return db


def _source(version: int, content: bytes) -> SourceObjectV2:
    return SourceObjectV2(
        source_id="source-a",
        version=version,
        sha256=hashlib.sha256(content).hexdigest(),
        byte_size=len(content),
        media_type="text/plain",
        rights_status="owned",
        original_retained=True,
        created_at=f"2026-08-27T00:0{version}:00+00:00",
    )


def test_source_versions_are_append_only_and_exact_retries_are_idempotent(
    tmp_path: Path,
) -> None:
    store = SourceStoreV2(_db(tmp_path))
    first = _source(1, b"v1")
    assert store.put_source(first) == first
    assert store.put_source(first) == first

    with pytest.raises(SourceConflictError, match="version"):
        store.put_source(_source(1, b"different"))


def test_new_source_version_marks_old_anchor_stale(tmp_path: Path) -> None:
    store = SourceStoreV2(_db(tmp_path))
    store.put_source(_source(1, b"v1"))
    anchor = AnchorV2(
        anchor_id="anchor-a",
        source_id="source-a",
        source_version=1,
        selector=TextQuoteSelector(exact="v1"),
        created_at="2026-08-27T00:01:00+00:00",
    )
    store.put_anchor(anchor)
    assert store.resolve_anchor("anchor-a")["state"] == "CURRENT"

    store.put_source(_source(2, b"v2"))
    resolved = store.resolve_anchor("anchor-a")
    assert resolved["state"] == "STALE"
    assert resolved["source_version"] == 1
    assert resolved["latest_source_version"] == 2


def test_provenance_activity_is_recorded_and_read_back(tmp_path: Path) -> None:
    store = SourceStoreV2(_db(tmp_path))
    store.put_source(_source(1, b"v1"))
    activity = ProvenanceActivityV2(
        activity_id="activity-a",
        activity_type="extract",
        used=["source-a@1"],
        generated=["anchor-a"],
        agent="archeaxis:test",
        started_at="2026-08-27T00:01:00+00:00",
        ended_at="2026-08-27T00:02:00+00:00",
    )
    readback = store.record_provenance(activity, source_id="source-a", source_version=1)

    assert readback["activity_id"] == "activity-a"
    assert readback["agent"] == "archeaxis:test"
    assert readback["used"] == ["source-a@1"]
