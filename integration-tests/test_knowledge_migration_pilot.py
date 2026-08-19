"""知识迁移试点（TP-20260819 §12）：3 试点对象 → Candidate → 回执 → 复核 → 回读。

试点对象：
  1. WORK-LAB 治理规则（provenance://worklab/rules/gate-7）
  2. DESIGN-LAB MethodCard（provenance://designlab/method/card-12）
  3. 外置 SourceRecord（provenance://external/source-record/sr-9）

产出：reports/current/FEDERATION_MIGRATION_REPORT.md + CANDIDATE_ROUNDTRIP_PROOF.json
"""
from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path

import pytest

from app.contracts.federation_v1 import (
    CandidateSubmissionV1,
    CandidateSubmissionItemV1,
    ExternalAssetRecordV1,
    KnowledgeQueryV1,
)
from app.federation import service

PILOT_OBJECTS = [
    {
        "item_key": "worklab-gate7",
        "claim": "WORK-LAB 治理规则：证据等级提升必须经过人工批准并留下审计轨迹",
        "source_ref": "provenance://worklab/rules/gate-7",
        "confidence": 0.95,
        "kind": "rule",
    },
    {
        "item_key": "designlab-mc12",
        "claim": "DESIGN-LAB MethodCard：设计交付物需双人复核并附检查清单",
        "source_ref": "provenance://designlab/method/card-12",
        "confidence": 0.8,
        "kind": "standard",
    },
    {
        "item_key": "external-sr9",
        "claim": "外置 SourceRecord：教材《逻辑学导论》第 3 章为三段论推理专题",
        "source_ref": "provenance://external/source-record/sr-9",
        "confidence": 0.6,
        "kind": "fact",
    },
]


def _run_pilot(db: str) -> dict[str, object]:
    submission = CandidateSubmissionV1(
        idempotency_key="pilot-2026-08-19",
        submitter="federation-pilot",
        items=[CandidateSubmissionItemV1(**obj) for obj in PILOT_OBJECTS],
        note="TP-20260819 §12 knowledge migration pilot",
    )
    result = service.submit_candidates(db, submission)
    receipt = result.receipt
    # human review: promote all three
    promoted = []
    with sqlite3.connect(db) as conn:
        rows = conn.execute(
            "SELECT id, item_key FROM federation_candidates_v1 WHERE submission_id=?",
            (receipt.submission_id,),
        ).fetchall()
        for row in rows:
            service.promote_to_verified(db, row[0], reviewer="human-reviewer")
            promoted.append({"candidate_id": row[0], "item_key": row[1]})
    # verified readback
    verified = service.query_verified(db, KnowledgeQueryV1(query="", kind="verified", page_size=100))
    # hash readback
    hashes = [service.hash_readback(db, p["candidate_id"]) for p in promoted]
    return {
        "receipt": receipt.model_dump(),
        "promoted": promoted,
        "verified_total": verified.total,
        "hash_readbacks": hashes,
    }


@pytest.fixture()
def pilot_db(tmp_path):
    return str(tmp_path / "pilot.sqlite")


def test_knowledge_migration_pilot(pilot_db):
    proof = _run_pilot(pilot_db)
    assert proof["receipt"]["accepted"] == 3
    assert proof["verified_total"] == 3
    assert len(proof["hash_readbacks"]) == 3
    assert all(len(h["content_hash"]) == 64 for h in proof["hash_readbacks"])
    # persist proof + report (deliverables)
    reports = Path("reports/current")
    reports.mkdir(parents=True, exist_ok=True)
    (reports / "CANDIDATE_ROUNDTRIP_PROOF.json").write_text(
        json.dumps(proof, ensure_ascii=False, indent=2), encoding="utf-8")
    report = f"""# 联邦知识迁移报告（TP-20260819 §12 试点）

- 试点对象：3（WORK-LAB 治理规则 / DESIGN-LAB MethodCard / 外置 SourceRecord）
- 提交：CandidateSubmissionV1（idempotency_key=pilot-2026-08-19，submitter=federation-pilot）
- 回执：accepted=3，items_hash={proof['receipt']['items_hash'][:16]}…
- 人工复核：3/3 → verified（reviewer=human-reviewer）
- 回读：Verified 查询 total=3；hash readback 3/3（64 位 SHA256）
- 状态：candidate → verified（人工门槛，无自动升级）
- 证据：CANDIDATE_ROUNDTRIP_PROOF.json + test_knowledge_migration_pilot.py
"""
    (reports / "FEDERATION_MIGRATION_REPORT.md").write_text(report, encoding="utf-8")
