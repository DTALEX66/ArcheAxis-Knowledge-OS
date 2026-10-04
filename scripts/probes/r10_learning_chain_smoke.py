"""R10 live smoke for the LEARNING chain: the segment the conversion probe never reaches.

Scope, stated so it cannot be over-read:
  * reachability, then one accepted fact recorded for a human actor;
  * a learning event for an item built from that fact, carrying a persistent client event id;
  * the reference recording which revision the item was built from;
  * and the item state read back from the Core.

What it deliberately does not do, and the receipt says so rather than implying wholeness:
  * it never reviews knowledge. core_client.review_request covers accepted, rejected,
    deprecated and modified, and that is a human act - a journey performing it would be
    grading its own work.
  * it does not record an answer and feedback pair, which needs the assessment path and is
    not covered by this slice.

Exit 0 only when every step succeeded. No token is printed.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
TOKEN = "c" * 64
SESSION = "d" * 32
ITEM_KEY = "card-learning-smoke"
CLIENT_EVENT_ID = "learning-smoke-1"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


core = _load("core_client_learning_smoke", REPO / "shared" / "core_client.py")


def main() -> int:
    with __import__("contextlib").suppress(Exception):
        sys.stdout.reconfigure(encoding="utf-8")
    print("module:", core.__file__)
    binary = REPO / ".project-local" / "build" / "cargo" / "debug" / "archeaxis-api.exe"
    if not binary.is_file():
        print(json.dumps({"ok": False, "blocked": "core binary not built", "path": str(binary)}))
        return 2

    runtime = _load("runtime_r10_learning", REPO / "scripts/runtime/dev.py")
    workdir = runtime.artifact_directory(REPO, "r10-learning")
    db = workdir / "core.sqlite"
    worker = {
        "python": str(Path(sys.executable).resolve()),
        "script": str((REPO / "services/python-workers/transport/text_ndjson.py").resolve()),
        "staging": str((workdir / "worker-staging").resolve()),
    }
    child = subprocess.Popen(
        [str(binary), str(db), "0"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        encoding="utf-8",
    )
    steps: list[dict] = []

    def step(call, base, name, method, path, body=None):
        status, payload = call(base, method, path, TOKEN, body)
        steps.append({"step": name, "method": method, "path": path, "status": status})
        return status, payload

    try:
        child.stdin.write(
            json.dumps({"launch_token": TOKEN, "session_id": SESSION, "text_worker": worker}) + "\n"
        )
        child.stdin.flush()
        child.stdin.close()
        deadline = time.time() + 15
        line = ""
        while time.time() < deadline:
            line = child.stdout.readline()
            if "127.0.0.1:" in line:
                break
        if "127.0.0.1:" not in line:
            print(json.dumps({"ok": False, "blocked": "core did not report readiness", "line": line[:80]}))
            return 3
        port = line.split("127.0.0.1:", 1)[1].split()[0].strip()
        base = "http://127.0.0.1:" + port

        result: dict = {"ok": False, "failed_step": None, "scope": "real_learning_chain_probe",
                        "steps": steps, "core_port": port,
                        "not_covered": ["human knowledge review"]}

        status, version = step(core.call, base, "reachability", "GET", "/api/v1/system/version")
        if status != 200:
            result["failed_step"] = "reachability"
            return _finish(result, workdir, steps)

        status, created = step(
            core.call, base, "accepted_fact", "POST", "/api/v1/knowledge-items",
            {"knowledge_type": "FACTUAL_CLAIM", "body": "radius 6371 km",
             "status": "accepted", "created_by": "owner"},
        )
        if not 200 <= status < 300:
            result["failed_step"] = "accepted_fact"
            result["payload"] = created
            return _finish(result, workdir, steps)
        knowledge_id = (created or {}).get("knowledge_id") if isinstance(created, dict) else None
        if not knowledge_id:
            result["failed_step"] = "accepted_fact: no knowledge_id returned"
            result["payload"] = created
            return _finish(result, workdir, steps)

        status, event = step(
            core.call, base, "learning_event", "POST", "/api/v1/learning/events",
            core.learning_event_request(ITEM_KEY, True, CLIENT_EVENT_ID),
        )
        if not 200 <= status < 300:
            result["failed_step"] = "learning_event"
            result["payload"] = event
            return _finish(result, workdir, steps)

        status, reference = step(
            core.call, base, "reference", "POST",
            "/api/v1/learning/items/" + ITEM_KEY + "/references",
            core.reference_request(ITEM_KEY, knowledge_id),
        )
        if not 200 <= status < 300:
            result["failed_step"] = "reference"
            result["payload"] = reference
            return _finish(result, workdir, steps)

        status, assessment = step(
            core.call, base, "assessment", "POST",
            "/api/v1/learning/items/" + ITEM_KEY + "/assessment",
            {"knowledge_id": knowledge_id},
        )
        if not 200 <= status < 300:
            result["failed_step"] = "assessment"
            result["payload"] = assessment
            return _finish(result, workdir, steps)
        assessment_id = (assessment or {}).get("assessment_id") if isinstance(assessment, dict) else None
        knowledge_version = (assessment or {}).get("knowledge_version") if isinstance(assessment, dict) else None

        # The answer. This is the learner answering the item, not a review of the knowledge:
        # review_request() would be the human act of accepting or rejecting a claim.
        status, answered = step(
            core.call, base, "answer", "POST", "/api/v1/learning/reviews",
            {
                "item_key": ITEM_KEY,
                "client_event_id": CLIENT_EVENT_ID + "-answer",
                "assessment_id": assessment_id,
                "knowledge_version": knowledge_version,
                "answer": "6371",
                "correct": True,
            },
        )
        if not 200 <= status < 300:
            result["failed_step"] = "answer"
            result["payload"] = answered
            return _finish(result, workdir, steps)

        status, state = step(
            core.call, base, "item_state", "GET",
            "/api/v1/learning/items/" + ITEM_KEY + "/state",
        )
        if status != 200:
            result["failed_step"] = "item_state"
            result["payload"] = state
            return _finish(result, workdir, steps)

        result["ok"] = True
        result["knowledge_id"] = knowledge_id
        # The reply to the answer is the feedback: the schedule and projection the Core returned.
        # Its keys are recorded rather than a guessed field, for the reason the state keys are.
        result["answer_keys"] = sorted(answered.keys()) if isinstance(answered, dict) else None
        result["assessment_keys"] = (
            sorted(assessment.keys()) if isinstance(assessment, dict) else None
        )
        # The state readback answered 200 and is the last step. Its body is not re-asserted
        # here: guessing at the shape once produced two null fields that read as "the item has
        # no known reference" when the truth was that the extraction was wrong.
        result["state_keys"] = sorted(state.keys()) if isinstance(state, dict) else None
        return _finish(result, workdir, steps)
    finally:
        child.kill()
        child.wait()


def _finish(result: dict, workdir: Path, steps: list[dict]) -> int:
    receipt_path = workdir / "r10-learning-chain.json"
    receipt_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    result["receipt_path"] = str(receipt_path)
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
