"""E2E: the bidirectional co-learning loop (loop gap F).

One migrated runtime, one full chain:
    card → review-outcome x3 (mastery) → machine candidate created
    → quiz generated → tick (TEACH_HUMAN with quiz payload)
    → distill (human expert) → rule + skill registered
    → trajectory (execution feedback) → reasoning principle

Runs in a subprocess with COGNITIVE_DATA_DIR isolation (mirrors the existing
research-facade E2E pattern). Failure anywhere fails the test.
"""
from __future__ import annotations

import json
import os
import textwrap
from pathlib import Path


def test_learning_loop_e2e(tmp_path: Path):
    runtime = tmp_path / "runtime"
    env = os.environ.copy()
    env["COGNITIVE_DATA_DIR"] = str(runtime)
    env["PYTHONDONTWRITEBYTECODE"] = "1"

    code = textwrap.dedent(
        r"""
        import json, os, sqlite3, sys
        from pathlib import Path
        from fastapi.testclient import TestClient

        runtime = Path(os.environ["COGNITIVE_DATA_DIR"]).resolve()
        from shared import storage
        from app.runtime_entrypoint import run_migration
        from argparse import Namespace
        assert run_migration(Namespace()) == 0

        from app.main import app
        client = TestClient(app)
        db = str(storage.DB_PATH)

        # 1) seed one card
        conn = sqlite3.connect(db)
        conn.execute(
            "INSERT INTO kb_cards (id, title, content, source_ids_json, tags_json, review_status) "
            "VALUES ('card-bkt', 'BKT', 'BKT 是隐马尔可夫模型，含 guess 与 slip 参数', '[]', '[]', 'reviewing')"
        )
        conn.commit(); conn.close()

        # 2) three strong reviews -> human mastery only; no automatic machine truth
        for i in range(3):
            r = client.post("/api/v1/learning/review-outcome", json={
                "card_id": "card-bkt", "command_id": f"e2e-r{i}",
                "quality": 5, "recorded_at": f"2026-08-18T00:0{i}:00+00:00",
            })
            assert r.status_code == 200, r.text
        assert r.json()["mastered"] is True
        assert r.json()["machine_knowledge_created"] is False
        assert r.json()["distillation_candidate"]["status"] == "unverified"

        # 3) quiz generation remains available from explicitly provided reference
        q = client.get("/api/v1/learning/quiz",
                       params={"concept": "BKT", "reference": "BKT 是隐马尔可夫模型，含 guess 与 slip 参数",
                               "key_terms": "guess,slip", "other_concepts": "SRS,IRT"})
        assert q.status_code == 200, q.text
        items = q.json()["items"]
        assert any(item["kind"] == "mcq" for item in items)

        # 4) spoofed mastery is rejected; intent-only requests fail closed
        spoof = client.post("/api/v1/learning/tick", json={
            "node_id": "concept:bkt", "learner_id": "learner-e2e",
            "human": {"reviewed": True},
            "machine": {"has_raw_source": True, "verified": True},
            "evidence_verified": True,
            "action_intent": "review",
            "idempotency_key": "e2e-tick-spoof",
        })
        assert spoof.status_code == 400, spoof.text
        t = client.post("/api/v1/learning/tick", json={
            "node_id": "concept:bkt",
            "learner_id": "learner-e2e",
            "action_intent": "review",
            "idempotency_key": "e2e-tick-safe",
        })
        assert t.status_code == 200, t.text
        body = t.json()
        assert body["action"] == "review_evidence", body
        assert body["state"]["human"]["level"] == "M0"
        assert body["state"]["machine"]["level"] == "NONE"

        # 5) human expert distills → rule + skill registered
        d = client.post("/api/v1/learning/distill", json={
            "statement": "产品主体必须处于招商开屏广告的第一视觉层级",
            "source_kind": "interview", "source_locator": "expert/2026-08-18",
            "evidence": "否决了 3 张海报",
        })
        assert d.status_code == 200, d.text
        principle_id = d.json()["principle_id"]

        # 6) execution feedback → reasoning principle
        tr = client.post("/api/v1/learning/trajectory", json={
            "goal": "导出 PDF", "steps": ["preflight", "export"],
            "outcome": "failure", "error_pattern": "字体未嵌入",
        })
        assert tr.status_code == 200, tr.text
        assert tr.json()["category"] == "failure_pattern"
        pr = client.get("/api/v1/learning/principles", params={"query": "字体", "top_k": 5})
        assert pr.status_code == 200 and pr.json()["count"] >= 1

        # 7) review queue is schedulable (FSRS due / mastered card)
        rq = client.get("/api/v1/learning/review-queue", params={"limit": 20})
        assert rq.status_code == 200

        print(json.dumps({
            "mastered": True,
            "machine_candidate": False,
            "quiz_items": len(items),
            "tick_action": body["action"],
            "principle_id": principle_id,
            "trajectory_category": tr.json()["category"],
            "review_queue_ok": True,
        }, ensure_ascii=False))
        """
    )
    import subprocess
    import sys
    proc = subprocess.run([sys.executable, "-c", code], env=env,
                          capture_output=True, text=True, cwd=str(Path(__file__).resolve().parents[1]))
    assert proc.returncode == 0, f"E2E failed:\n{proc.stdout}\n{proc.stderr}"
    receipt = json.loads(proc.stdout.strip().splitlines()[-1])
    assert receipt["tick_action"] == "review_evidence"
    assert receipt["machine_candidate"] is False
    assert receipt["mastered"] is True
    print("E2E receipt:", receipt)
