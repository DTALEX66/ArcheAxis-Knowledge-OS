"""Prepare a source-bound product candidate, then record only an explicit owner decision.

Preparation never accepts knowledge and does not count as human review.
Session credentials stay in memory; receipt contains no credentials.
"""

from __future__ import annotations

import argparse
import json
import time
import uuid
from pathlib import Path

import aaos01_office_runtime_loop as office


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--receipt", type=Path)
    parser.add_argument("--owner-decision", choices=["accepted", "rejected"])
    args = parser.parse_args()
    if bool(args.receipt) != bool(args.owner_decision):
        parser.error("decision requires the exact prepared receipt")
    candidate = args.candidate.resolve()
    launcher = office.load("owner_candidate_launcher", candidate / "start-backend.py")
    client = office.load("owner_candidate_client", office.REPO / "shared/core_client.py")
    if args.receipt:
        receipt = json.loads(args.receipt.read_text(encoding="utf-8"))
        work = Path(receipt["work"])
        assert receipt["status"] == "awaiting_owner_decision", "decision already recorded"
    else:
        work = office.REPO / ".project-local/task-runtime/aaos01-owner-review" / uuid.uuid4().hex
        work.mkdir(parents=True)
        receipt = {
            "status": "preparing",
            "work": str(work),
            "candidate": str(candidate),
            "evidence_level": "REAL_SOURCE_BOUND_PRODUCT_CANDIDATE_NOT_YET_HUMAN_REVIEWED",
        }
    child = None
    try:
        child, base, launch, tokens = launcher.start(work, 0)

        def call(method, path, body=None, expected=200):
            status, value = client.call(base, method, path, tokens["human"], body)
            assert status == expected, (status, value)
            return value

        if not args.receipt:
            source = office.REPO / "docs/authority/taskpack-1004-aaos01/01_完整执行任务书.md"
            imported = call(
                "POST",
                "/api/v1/imports",
                client.import_request(source.name, source.read_bytes()),
                202,
            )
            job = "owner_" + uuid.uuid4().hex
            call(
                "POST",
                "/api/v1/jobs",
                {"job_id": job, "kind": "text", "input_ref": imported["source_id"]},
                202,
            )
            status, value = client.call(
                base,
                "POST",
                f"/api/v1/jobs/{job}/executions",
                tokens["human"],
                {"deadline_ms": 30000},
                extra_headers={"idempotency-key": job},
            )
            assert status == 202, (status, value)
            until = time.monotonic() + 35
            while time.monotonic() < until:
                state = call("GET", f"/api/v1/jobs/{job}")
                if state["state"] in {"succeeded", "failed", "cancelled"}:
                    break
                time.sleep(0.1)
            assert state["state"] == "succeeded", state
            transform = call("GET", f"/api/v1/sources/{imported['source_id']}/jobs/{job}/transform")
            content = transform["content"]
            quote = next(line for line in content.splitlines() if "最终二进制内 SQLite" in line)
            start = content.index(quote)
            begin = len(content[:start].encode("utf-16-le")) // 2
            end = begin + len(quote.encode("utf-16-le")) // 2
            body = "AAOS-01 要核验最终二进制内 SQLite 的实际版本；WAL-reset 修复版本为 3.51.3 及之后，另有 3.44.6/3.50.7 回移植。必须使用合格版本及单写者/协调 checkpoint。"
            result = call(
                "POST",
                "/api/v1/knowledge-items/from-transform",
                {
                    "knowledge_type": "OBSERVATION",
                    "body": body,
                    "source_id": imported["source_id"],
                    "job_id": job,
                    "transform_id": transform["transform_id"],
                    "selection_start_utf16": begin,
                    "selection_end_utf16": end,
                    "quote": quote,
                },
                201,
            )
            knowledge = call("GET", f"/api/v1/knowledge-items/{result['knowledge_id']}/v3")
            qualification = call(
                "GET", f"/api/v1/knowledge-items/{result['knowledge_id']}/qualification"
            )
            assert knowledge["status"] == "candidate"
            receipt.update(
                status="awaiting_owner_decision",
                source=office.identity(source),
                imported=imported,
                job_id=job,
                source_quote=quote,
                candidate_body=body,
                knowledge=knowledge,
                qualification=qualification,
            )
        else:
            prior = receipt["knowledge"]
            current = call("GET", f"/api/v1/knowledge-items/{prior['knowledge_id']}/v3")
            assert (
                current["version"] == prior["version"]
                and current["body"] == receipt["candidate_body"]
            ), "candidate changed; owner must review again"
            review = call(
                "POST",
                f"/api/v1/knowledge/{prior['knowledge_id']}/review/versioned",
                {
                    "expected_version": current["version"],
                    "action": args.owner_decision,
                    "reviewer": "owner-authorized",
                    "note": "Owner explicitly decided this exact prepared candidate in the active task.",
                },
            )
            receipt.update(
                status="owner_decision_recorded", owner_decision=args.owner_decision, review=review
            )
            receipt["readback"] = call("GET", f"/api/v1/knowledge-items/{prior['knowledge_id']}/v3")
            assert receipt["readback"]["status"] == args.owner_decision
    finally:
        if child is not None:
            launcher.stop(child)
        destination = args.receipt or work / "receipt.json"
        destination.write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8")
        print(
            json.dumps(
                {"status": receipt["status"], "receipt": str(destination)}, ensure_ascii=False
            )
        )


if __name__ == "__main__":
    main()
