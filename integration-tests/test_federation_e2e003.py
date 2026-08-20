"""E2E-003: governed knowledge query + Candidate Receipt roundtrip (HTTP).

Full federation chain through the real FastAPI router:
submit batch → receipt readback → human verify → verified query → hash readback.
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.contracts.federation_v1 import CandidateSubmissionV1, CandidateSubmissionItemV1
from app.main import app

client = TestClient(app)


@pytest.fixture()
def fed_db(tmp_path):
    old = os.environ.get("ARCHEAXIS_DATA_DIR")
    old_token = os.environ.get("ARCHEAXIS_DESKTOP_LAUNCH_TOKEN")
    os.environ["ARCHEAXIS_DATA_DIR"] = str(tmp_path)
    os.environ["ARCHEAXIS_DESKTOP_LAUNCH_TOKEN"] = "e2e-003-launch-token"
    yield tmp_path / "archeaxis.sqlite"
    if old is None:
        os.environ.pop("ARCHEAXIS_DATA_DIR", None)
    else:
        os.environ["ARCHEAXIS_DATA_DIR"] = old
    if old_token is None:
        os.environ.pop("ARCHEAXIS_DESKTOP_LAUNCH_TOKEN", None)
    else:
        os.environ["ARCHEAXIS_DESKTOP_LAUNCH_TOKEN"] = old_token


def _headers(actor: str, *scopes: str) -> dict[str, str]:
    return {
        "x-archeaxis-launch-token": "e2e-003-launch-token",
        "x-archeaxis-actor": actor,
        "x-archeaxis-scopes": " ".join(scopes),
    }


def test_e2e003_federation_roundtrip(fed_db):
    # 1) batch candidate submission (WORK-LAB -> ArcheAxis)
    payload = CandidateSubmissionV1(
        idempotency_key="e2e-003-key",
        submitter="worklab-agent",
        items=[
            CandidateSubmissionItemV1(
                item_key="r1", claim="WORK-LAB 治理规则：证据等级提升需人工批准",
                source_ref="provenance://worklab/rules/gate-7", confidence=0.9, kind="rule",
            ),
            CandidateSubmissionItemV1(
                item_key="m1", claim="DESIGN-LAB MethodCard：设计交付需双人复核",
                source_ref="provenance://designlab/method/card-12", confidence=0.7, kind="standard",
            ),
        ],
    )
    submit_headers = _headers("worklab-agent", "federation.write")
    resp = client.post(
        "/api/v1/federation/candidates", json=payload.model_dump(), headers=submit_headers
    )
    assert resp.status_code == 200
    receipt = resp.json()["receipt"]
    assert receipt["status"] == "accepted"
    assert receipt["accepted"] == 2

    # idempotency: same key -> duplicate
    resp2 = client.post(
        "/api/v1/federation/candidates", json=payload.model_dump(), headers=submit_headers
    )
    assert resp2.status_code == 200
    assert resp2.json()["duplicate"] is True

    # 2) receipt readback
    rr = client.get(f"/api/v1/federation/candidates/{receipt['submission_id']}/receipt")
    assert rr.status_code == 200
    assert rr.json()["receipt"]["items_hash"] == receipt["items_hash"]

    # 3) human verify (governed promotion)
    import sqlite3
    with sqlite3.connect(fed_db) as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS federation_candidates_v1 (
            id TEXT PRIMARY KEY, submission_id TEXT NOT NULL, idempotency_key TEXT NOT NULL,
            item_key TEXT NOT NULL, submitter TEXT NOT NULL, claim TEXT NOT NULL,
            source_ref TEXT NOT NULL, confidence REAL NOT NULL DEFAULT 0.5,
            kind TEXT NOT NULL DEFAULT 'fact', rights TEXT NOT NULL DEFAULT 'unspecified',
            status TEXT NOT NULL DEFAULT 'candidate', verified_at TEXT, reviewer TEXT,
            created_at TEXT NOT NULL, UNIQUE (idempotency_key, item_key));
        """)
        row = conn.execute("SELECT id FROM federation_candidates_v1 WHERE item_key='r1'").fetchone()
        cand_id = row[0]
    vr = client.post(
        f"/api/v1/federation/candidates/{cand_id}/review",
        json={
            "decision": "verified",
            "reviewer_id": "human-reviewer",
            "rationale": "e2e human verification",
            "expected_version": 1,
            "idempotency_key": "e2e-003-review-r1",
        },
        headers=_headers("human-reviewer", "evidence.review"),
    )
    assert vr.status_code == 200
    assert vr.json()["status"] == "verified"

    # 4) governed query: verified only
    q = client.get("/api/v1/federation/knowledge", params={"query": "治理规则", "kind": "verified"})
    assert q.status_code == 200
    data = q.json()
    assert data["total"] >= 1
    assert data["items"][0]["status"] == "verified"
    assert data["items"][0]["reviewer"] == "human-reviewer"

    # 5) hash readback
    h = client.get(f"/api/v1/federation/records/{cand_id}/hash")
    assert h.status_code == 200
    assert len(h.json()["content_hash"]) == 64
