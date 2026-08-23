"""Federation record types: evidence / learning / provenance / rights (AA-P0-002)."""
from __future__ import annotations

import inspect
import sqlite3

import pytest
from pydantic import ValidationError

from app.contracts.federation_v1 import (
    EvidenceIntakeV1,
    LearningRecordV1,
    ProvenanceRecordV1,
    RightsRecordV1,
)
from app.federation import service


def test_record_evidence(tmp_path):
    db = tmp_path / "fed.sqlite"
    rec = EvidenceIntakeV1(evidence_id="ev-1", source_ref="provenance://ceshi/pdf/oxford",
                           anchor={"page": 3, "region": [1, 2, 3, 4]},
                           content_hash="abc123", rights="internal-use", verified=False)
    rid = service.record_evidence(db, rec)
    assert rid == "ev-1"
    rows = service.list_records(db, "evidence")
    assert len(rows) == 1
    assert rows[0]["source_ref"] == "provenance://ceshi/pdf/oxford"


def test_record_learning(tmp_path):
    db = tmp_path / "fed.sqlite"
    rec = LearningRecordV1(record_id="lr-1", concept="三段论", kind="quiz",
                           outcome={"score": 0.8, "answered": 5},
                           source_ref="provenance://ceshi/pdf/oxford")
    service.record_learning(db, rec)
    rows = service.list_records(db, "learning")
    assert len(rows) == 1 and rows[0]["kind"] == "quiz"


def test_record_provenance(tmp_path):
    db = tmp_path / "fed.sqlite"
    rec = ProvenanceRecordV1(record_id="pr-1", entity_id="cand-1", event="promoted",
                             actor="human-reviewer", at="2026-08-20T00:00:00Z")
    service.record_provenance(db, rec)
    rows = service.list_records(db, "provenance")
    assert len(rows) == 1 and rows[0]["event"] == "promoted"


def test_provenance_correction_is_a_new_reasoned_event(tmp_path):
    db = tmp_path / "fed.sqlite"
    original = ProvenanceRecordV1(
        record_id="pr-1", entity_id="cand-1", event="created",
        actor="human-reviewer", at="2026-08-20T00:00:00Z",
    )
    correction = ProvenanceRecordV1(
        record_id="pr-2", entity_id="cand-1", event="superseded",
        actor="human-reviewer", at="2026-08-20T00:01:00Z", parent_id="pr-1",
        reason="a newer source revision corrected the claim",
    )

    service.record_provenance(db, original)
    service.record_provenance(db, correction)

    rows = service.list_records(db, "provenance")
    assert {row["record_id"] for row in rows} == {"pr-1", "pr-2"}
    corrected = next(row for row in rows if row["record_id"] == "pr-2")
    assert corrected["parent_id"] == "pr-1"
    assert corrected["actor"] == "human-reviewer"
    assert corrected["reason"] == "a newer source revision corrected the claim"


@pytest.mark.parametrize(
    "payload, message",
    [
        (
            {
                "record_id": "pr-2", "entity_id": "cand-1", "event": "superseded",
                "actor": "human-reviewer", "at": "2026-08-20T00:01:00Z",
                "reason": "correction without predecessor",
            },
            "parent_id",
        ),
        (
            {
                "record_id": "pr-2", "entity_id": "cand-1", "event": "revoked",
                "actor": "human-reviewer", "at": "2026-08-20T00:01:00Z", "parent_id": "pr-1",
            },
            "reason",
        ),
    ],
)
def test_provenance_correction_requires_parent_and_reason(payload, message):
    with pytest.raises(ValidationError, match=message):
        ProvenanceRecordV1(**payload)


def test_provenance_reason_forward_migration_preserves_records_after_restart(tmp_path):
    db = tmp_path / "legacy-fed.sqlite"
    with sqlite3.connect(db) as connection:
        connection.executescript(
            """
            CREATE TABLE federation_provenance_records_v1 (
                record_id TEXT PRIMARY KEY, entity_id TEXT NOT NULL, event TEXT NOT NULL,
                actor TEXT NOT NULL, at TEXT NOT NULL, parent_id TEXT, created_at TEXT NOT NULL
            );
            INSERT INTO federation_provenance_records_v1 VALUES
                ('pr-1', 'cand-1', 'created', 'human-reviewer', '2026-08-20T00:00:00Z', NULL, '2026-08-20T00:00:00Z');
            """
        )

    service.record_provenance(
        db,
        ProvenanceRecordV1(
            record_id="pr-2", entity_id="cand-1", event="revoked",
            actor="human-reviewer", at="2026-08-20T00:01:00Z", parent_id="pr-1",
            reason="the source licence was withdrawn",
        ),
    )

    with sqlite3.connect(db) as connection:
        columns = {row[1] for row in connection.execute("PRAGMA table_info(federation_provenance_records_v1)")}
        persisted = connection.execute(
            "SELECT parent_id, reason FROM federation_provenance_records_v1 WHERE record_id='pr-2'"
        ).fetchone()
    assert "reason" in columns
    assert persisted == ("pr-1", "the source licence was withdrawn")
    assert {row["record_id"] for row in service.list_records(db, "provenance")} == {"pr-1", "pr-2"}


def test_record_rights(tmp_path):
    db = tmp_path / "fed.sqlite"
    rec = RightsRecordV1(record_id="rr-1", entity_id="asset-1", rights="cc-by-4.0",
                         scope="internal", source_ref="provenance://designlab/method/card-12")
    service.record_rights(db, rec)
    rows = service.list_records(db, "rights")
    assert len(rows) == 1 and rows[0]["rights"] == "cc-by-4.0"


def test_record_ids_are_append_only(tmp_path):
    db = tmp_path / "fed.sqlite"
    rec = RightsRecordV1(record_id="rr-1", entity_id="asset-1", rights="cc-by-4.0")
    service.record_rights(db, rec)
    with pytest.raises(service.FederationError, match="append-only"):
        service.record_rights(db, rec)


def test_record_storage_rejects_direct_mutation_and_deletion(tmp_path):
    db = tmp_path / "fed.sqlite"
    service.record_rights(
        db,
        RightsRecordV1(record_id="rr-1", entity_id="asset-1", rights="cc-by-4.0"),
    )

    with sqlite3.connect(db) as connection:
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute(
                "UPDATE federation_rights_records_v1 SET rights='proprietary' WHERE record_id='rr-1'"
            )
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute(
                "DELETE FROM federation_rights_records_v1 WHERE record_id='rr-1'"
            )


def test_append_only_writer_does_not_issue_replace_sql():
    source = inspect.getsource(service._append_record)
    assert "INSERT INTO" in source
    assert "OR REPLACE" not in source
