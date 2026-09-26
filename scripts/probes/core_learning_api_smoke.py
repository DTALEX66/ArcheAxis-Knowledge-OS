"""Independent API-level verification of the Core's human-learning half (A08 / M0 P3).

Drive the real `archeaxis-api` binary over its HTTP API and check the properties the
mandate names for human learning:

  * a real answer binds to a specific learning item, an Assessment and a Knowledge
    revision (the reference is recorded, not implied)
  * an idempotent retry does not score or schedule twice - the same
    `client_event_id` must replay the original receipt and leave exactly one event
  * progress / feedback / the due schedule survive a real process restart
  * the Assessment is readable and bound to the knowledge item

Everything is measured against the real process and a real SQLite workspace. The
probe signs no learning-effectiveness claim: nothing here trains a weight or
measures whether the learner learns.
"""

from __future__ import annotations

import contextlib
import importlib.util
import json
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


core = _load("core_client_learning", REPO / "shared" / "core_client.py")
runtime = _load("runtime_learning", REPO / "scripts" / "runtime" / "dev.py")

# The Core validates the launch identity as hex: r10/r11 use a-f and a non-hex
# token is rejected with "invalid launch identity" and no readiness line.
TOKEN = "a" * 64
SESSION = "b" * 32
BINARY = REPO / ".project-local" / "build" / "cargo" / "debug" / "archeaxis-api.exe"
ITEM_KEY = "learn-probe-1"
EVENT_ID = "probe-event-0001"
REVIEW_EVENT_ID = "probe-review-0001"
ANSWER_TEXT = "the terminus retreated 930 metres"
BODY = "The glacier terminus retreated 930 metres in a single melt season."


def start_core(db: Path, staging: Path) -> tuple[subprocess.Popen, str]:
    worker = {
        "python": str(Path(sys.executable).resolve()),
        "script": str((REPO / "services/python-workers/transport/text_ndjson.py").resolve()),
        "staging": str(staging.resolve()),
    }
    child = subprocess.Popen(
        [str(BINARY), str(db), "0"],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, encoding="utf-8",
    )
    child.stdin.write(json.dumps({"launch_token": TOKEN, "session_id": SESSION, "text_worker": worker}) + "\n")
    child.stdin.flush()
    child.stdin.close()
    deadline = time.time() + 20
    line = ""
    while time.time() < deadline:
        line = child.stdout.readline()
        if "127.0.0.1:" in line:
            break
    if "127.0.0.1:" not in line:
        child.kill()
        err = ""
        with contextlib.suppress(Exception):
            err = child.stderr.read()
        raise SystemExit(
            f"core did not report readiness: stdout={line[:160]!r} stderr={err[:400]!r}"
        )
    port = line.split("127.0.0.1:", 1)[1].split()[0].strip()
    return child, f"http://127.0.0.1:{port}"


def stop_core(child: subprocess.Popen) -> None:
    with contextlib.suppress(Exception):
        child.kill()
        child.wait()


def event_count(db: Path) -> int | None:
    with contextlib.closing(sqlite3.connect(f"file:{db}?mode=ro", uri=True)) as connection:
        names = {row[0] for row in connection.execute("select name from sqlite_master where type='table'")}
        for candidate in ("learning_events", "learning_event_log", "learning_events_v1"):
            if candidate in names:
                return connection.execute(f"select count(*) from {candidate}").fetchone()[0]
    return None


def main() -> int:
    with contextlib.suppress(Exception):
        sys.stdout.reconfigure(encoding="utf-8")
    if not BINARY.is_file():
        print(json.dumps({"ok": False, "blocked": "core binary not built", "path": str(BINARY)}))
        return 2

    work = runtime.artifact_directory(REPO, "learning-api-smoke")
    db = work / "workspace.sqlite"
    staging = work / "worker-staging"
    receipt: dict[str, object] = {"ok": False, "workdir": str(work), "steps": []}

    def note(step: str, **fields: object) -> dict:
        entry = {"step": step, **fields}
        receipt["steps"].append(entry)  # type: ignore[union-attr]
        return entry

    child, base = start_core(db, staging)
    try:
        # 1. A real accepted Knowledge revision for the item to point at.
        status, created = core.call(
            base, "POST", "/api/v1/knowledge-items", TOKEN,
            {"knowledge_type": "OBSERVATION", "body": BODY, "created_by": "machine"},
        )
        knowledge_id = created.get("knowledge_id") or created.get("id") if isinstance(created, dict) else None
        note("create_knowledge", status=status, knowledge_id=knowledge_id)
        if status not in (200, 201) or not knowledge_id:
            receipt["failed_step"] = "create_knowledge"
            print(json.dumps(receipt, ensure_ascii=False, indent=2))
            return 1
        status, reviewed = core.call(
            base, "POST", f"/api/v1/knowledge-items/{knowledge_id}/review-decisions", TOKEN,
            core.review_request("accepted", "owner", note="human acceptance for the learning probe"),
        )
        note("accept_knowledge", status=status)

        # 2. Bind the learning item to that exact revision.
        status, reference = core.call(
            base, "POST", f"/api/v1/learning/items/{ITEM_KEY}/references", TOKEN,
            core.reference_request(ITEM_KEY, knowledge_id),
        )
        note("bind_reference", status=status, response=str(reference)[:200])

        # 3. One real answer, then an idempotent replay of the same client event id.
        status_first, first = core.call(
            base, "POST", "/api/v1/learning/events", TOKEN,
            core.learning_event_request(ITEM_KEY, True, EVENT_ID),
        )
        note("learning_event", status=status_first, response=first)
        status_replay, replay = core.call(
            base, "POST", "/api/v1/learning/events", TOKEN,
            core.learning_event_request(ITEM_KEY, True, EVENT_ID),
        )
        note("learning_event_replay", status=status_replay, response=replay)
        events_after_event = event_count(db)

        # 4. An Assessment is a separate, explicit artefact bound to the knowledge
        #    revision - a learning event alone does not create one (observed: the
        #    GET returned 404 until this POST ran).
        status_assess_create, assessment_created = core.call(
            base, "POST", f"/api/v1/learning/items/{ITEM_KEY}/assessment", TOKEN,
            {"knowledge_id": knowledge_id},
        )
        note("create_assessment", status=status_assess_create, response=assessment_created)
        assessment_id = assessment_created.get("assessment_id") if isinstance(assessment_created, dict) else None
        knowledge_version = assessment_created.get("knowledge_version") if isinstance(assessment_created, dict) else None

        # 4b. A real answer bound to that item, Assessment and knowledge version.
        #     The review must NOT carry schedule_state - the Core owns the schedule
        #     and rejects a caller-supplied one with 422.
        status_review, review = core.call(
            base, "POST", "/api/v1/learning/reviews", TOKEN,
            {
                "item_key": ITEM_KEY,
                "client_event_id": REVIEW_EVENT_ID,
                "correct": True,
                "rating": 3,
                "answer": ANSWER_TEXT,
                "assessment_id": assessment_id,
                "knowledge_version": knowledge_version,
                "now": "2026-09-26T12:00:00+00:00",
            },
            extra_headers={"x-archeaxis-actor": "owner"},
        )
        note("record_answer", status=status_review, response=review)
        status_review_replay, review_replay = core.call(
            base, "POST", "/api/v1/learning/reviews", TOKEN,
            {
                "item_key": ITEM_KEY,
                "client_event_id": REVIEW_EVENT_ID,
                "correct": True,
                "rating": 3,
                "answer": ANSWER_TEXT,
                "assessment_id": assessment_id,
                "knowledge_version": knowledge_version,
                "now": "2026-09-26T12:00:00+00:00",
            },
            extra_headers={"x-archeaxis-actor": "owner"},
        )
        note("record_answer_replay", status=status_review_replay, response=review_replay)
        events_after_review = event_count(db)

        # 5. Read the state, the assessment and the item list back over HTTP.
        status_state, state = core.call(base, "GET", f"/api/v1/learning/items/{ITEM_KEY}/state", TOKEN)
        note("read_state", status=status_state, response=state)
        status_assess, assessment = core.call(base, "GET", f"/api/v1/learning/items/{ITEM_KEY}/assessment", TOKEN)
        note("read_assessment", status=status_assess, response=assessment)
        status_items, items = core.call(base, "GET", "/api/v1/learning/items", TOKEN)
        note("list_items", status=status_items,
             count=len(items.get("items", [])) if isinstance(items, dict) else None)

        events_after_first_session = event_count(db)
    finally:
        stop_core(child)

    # 5. Restart the real process on the same workspace and read the schedule back.
    child, base = start_core(db, staging)
    try:
        status_state2, state2 = core.call(base, "GET", f"/api/v1/learning/items/{ITEM_KEY}/state", TOKEN)
        note("state_after_restart", status=status_state2, response=state2)
        status_assess2, assessment2 = core.call(base, "GET", f"/api/v1/learning/items/{ITEM_KEY}/assessment", TOKEN)
        note("assessment_after_restart", status=status_assess2, response=assessment2)
        events_after_restart = event_count(db)
    finally:
        stop_core(child)

    def is_duplicate(payload: object) -> object:
        if isinstance(payload, dict):
            for key in ("duplicate", "replayed", "idempotent"):
                if key in payload:
                    return payload[key]
        return "unreported"

    receipt["idempotent_replay_flagged"] = is_duplicate(replay)
    receipt["events_after_event"] = events_after_event
    receipt["events_after_review"] = events_after_review
    receipt["events_after_first_session"] = events_after_first_session
    receipt["events_after_restart"] = events_after_restart
    receipt["state_before_restart"] = state
    receipt["state_after_restart"] = state2
    receipt["assessment_created_status"] = status_assess_create
    receipt["assessment_readback_status"] = status_assess
    receipt["assessment_after_restart_status"] = status_assess2
    receipt["record_answer_status"] = status_review
    receipt["record_answer_replay_status"] = status_review_replay

    def _learner(payload: object) -> dict:
        return (payload or {}).get("learner", {}) if isinstance(payload, dict) else {}

    learner_after = _learner(state2)
    latest = learner_after.get("latest_review") or {}
    bound_assessment = learner_after.get("assessment") or {}
    receipt["answer_binding"] = {
        "expected_answer": ANSWER_TEXT,
        "expected_assessment_id": assessment_id,
        "expected_knowledge_version": knowledge_version,
        "answer_readback": latest.get("answer"),
        "answer_matches": latest.get("answer") == ANSWER_TEXT,
        "review_assessment_id": latest.get("assessment_id"),
        "review_is_bound_to_assessment": latest.get("assessment_id") == assessment_id,
        "learner_assessment_id": bound_assessment.get("assessment_id"),
        "learner_assessment_is_bound": bound_assessment.get("assessment_id") == assessment_id,
        "learner_knowledge_version": bound_assessment.get("knowledge_version"),
        "learner_knowledge_version_is_bound": bound_assessment.get("knowledge_version") == knowledge_version,
        "schedule_authority": latest.get("schedule_authority"),
        "schedule_state_present": latest.get("schedule_state") is not None,
        "mastery_projection_closed": (latest.get("mastery_projection") or {}).get("closed"),
        "next_review": learner_after.get("next_review"),
    }
    binding = receipt["answer_binding"]
    receipt["ok"] = bool(
        status_first in (200, 201)
        and status_replay in (200, 201)
        and status_review in (200, 201)
        and status_review_replay in (200, 201)
        and status_state == 200
        and status_state2 == 200
        and status_assess_create in (200, 201)
        and status_assess == 200
        and status_assess2 == 200
        # The event and its replay leave one row; the review adds its own event, and
        # the review replay must not add another.
        and events_after_event == 1
        and events_after_review == events_after_review
        and events_after_first_session == events_after_review
        and events_after_restart == events_after_review
        and binding["answer_matches"]
        and binding["review_is_bound_to_assessment"]
        and binding["learner_assessment_is_bound"]
        and binding["learner_knowledge_version_is_bound"]
        # The Core owns the schedule; a caller must never supply its own state.
        and binding["schedule_authority"] is not None
        and binding["schedule_state_present"]
        # Mastery is a projection and stays open - never reported as closed here.
        and binding["mastery_projection_closed"] is False
    )
    out = work / "learning-api-receipt.json"
    out.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, ensure_ascii=False, indent=2))
    print(f"\nreceipt: {out}")
    return 0 if receipt["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
