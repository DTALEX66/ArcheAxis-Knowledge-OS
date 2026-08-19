"""Federation record types: evidence / learning / provenance / rights (AA-P0-002)."""
from __future__ import annotations

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


def test_record_rights(tmp_path):
    db = tmp_path / "fed.sqlite"
    rec = RightsRecordV1(record_id="rr-1", entity_id="asset-1", rights="cc-by-4.0",
                         scope="internal", source_ref="provenance://designlab/method/card-12")
    service.record_rights(db, rec)
    rows = service.list_records(db, "rights")
    assert len(rows) == 1 and rows[0]["rights"] == "cc-by-4.0"
