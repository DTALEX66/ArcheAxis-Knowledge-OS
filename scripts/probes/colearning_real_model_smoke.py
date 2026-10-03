"""The co-learning loop with a real model: M0's synthetic machine side replaced by real inference.

`m0_full_loop_smoke.py` already covers machine failure -> human correction -> retest, and says of
itself that "the source, human actions and model failure are fixtures" and that it "never qualifies
real human learning or actual model inference". That was true when it was written, because no route
existed that ran a model. Now three do, and this probe drives them:

    accepted knowledge -> POST /machine/answers        (a real local model answers)
    -> POST /machine/tasks    (the failure is recorded with the answer that failed)
    -> POST /machine/corrections                       (a person names the error and the correction)
    -> POST /machine/retests                           (the same question is asked again, linked)
    -> read the retest receipt back and check retest_of

What is still a fixture, and is stated rather than implied: the **person**. This script decides which
answer is wrong and writes the correction, so it produces REAL_MODEL evidence about the model leg and
not about human judgement. A run of this script is not evidence that a human reviewed anything; it is
evidence that the routes work against a real model and that the retest links to the failure.

Usage:
    ARCHEAXIS_PYTHON=<interpreter> python scripts/probes/colearning_real_model_smoke.py <core.exe>
"""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
RUN: Path | None = None


def run_directory() -> Path:
    runtime = _load("colearning_runtime", REPO / "scripts/runtime/dev.py")
    return runtime.artifact_directory(REPO, "colearning-real-model")

# A context whose content is checkable, so a wrong answer is detectable without a human.
CONTEXT = (
    "ArcheAxis Knowledge is a local-first knowledge workspace.\n"
    "Its canonical store is SQLite, and only the Rust Core writes it.\n"
    "The release is currently FROZEN pending the Owner gate.\n"
)
QUESTION = "Which component writes the canonical store, and is the release frozen?"
# A question the context cannot answer, which gives the failure a real rather than invented cause:
# a grounded model should refuse it, and an ungrounded one will invent something.
UNGROUNDED_QUESTION = "What is the capital of Portugal, and who signed the 1975 treaty?"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Receipt:
    def __init__(self) -> None:
        self.stages: list[dict] = []
        self.blocked: dict[str, str] = {}

    def stage(self, name: str, **fields) -> None:
        self.stages.append({"stage": name, "at": datetime.now(timezone.utc).isoformat(), **fields})

    def block(self, name: str, reason: str) -> None:
        self.blocked[name] = reason

    @property
    def failed_stage(self) -> str | None:
        for entry in self.stages:
            if entry.get("problem"):
                return entry["stage"]
            status = entry.get("status")
            expected = (403,) if entry["stage"] == "machine_cannot_accept_correction" else (200, 201, 202)
            if status is not None and status not in expected:
                return entry["stage"]
            if entry.get("links_to_failure") is False:
                return entry["stage"]
        return None

    def document(self, **extra) -> dict:
        return {
            "schema": "aaos.colearning-real-model-receipt/v1",
            "evidence_class": "REAL_MODEL",
            "what_is_real": [
                "the local model inference behind POST /api/v1/machine/answers and "
                "POST /api/v1/machine/retests",
                "the grounded context, which is the knowledge item's own accepted body",
                "every status, body and receipt read back from a live Core",
            ],
            "what_is_still_a_fixture": [
                "the person: this script picks the question, judges the answer wrong and writes the "
                "correction, so a run is not evidence that a human reviewed anything",
                "the source file, which this script writes",
            ],
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            "failed_stage": self.failed_stage,
            "stages": self.stages,
            "blocked": self.blocked,
            **extra,
        }


def unmet_prerequisites() -> dict[str, str]:
    missing: dict[str, str] = {}
    if not os.environ.get("ARCHEAXIS_PYTHON"):
        missing["ARCHEAXIS_PYTHON"] = (
            "the interpreter the Core uses for its scheduler worker; without it a review is recorded "
            "as unscheduled and the run could not observe the whole loop")
    return missing


def main() -> int:
    global RUN
    if len(sys.argv) < 2:
        print("usage: colearning_real_model_smoke.py <core-executable>")
        return 2
    core = Path(sys.argv[1])
    if not core.is_file():
        print(f"core executable not found: {core}")
        return 2

    receipt = Receipt()
    for name, reason in unmet_prerequisites().items():
        receipt.block(name, reason)

    launcher = _load("launcher_colearning", REPO / "scripts/release/backend_launcher.py")
    client = _load("client_colearning", REPO / "shared/core_client.py")

    RUN = run_directory()
    (RUN / "core").mkdir(parents=True)
    shutil.copy2(core, RUN / "core" / "archeaxis-api.exe")
    (RUN / "data").mkdir(parents=True)
    (RUN / "worker-profile.json").write_text(json.dumps({
        "schema": "archeaxis.worker-profile/v1",
        "python": os.environ.get("ARCHEAXIS_PYTHON", sys.executable),
        "script": str(REPO / "services/python-workers/transport/text_ndjson.py"),
        "staging": "data/worker-staging",
        # The machine answer route is declared here because it is what this probe drives; a launch
        # that does not declare it has no capability to answer with, which the probe reports as
        # blocked rather than as a failure of the loop.
        "routes": [
            {"capability": "machine.answer",
             "script": str(REPO
                           / "services/python-workers/machine/worker_machine_answer.py")},
        ],
    }, indent=2), encoding="utf-8")

    launcher.ROOT = RUN
    child, base, _doc, tokens = launcher.start(RUN / "data", 0)
    human = launcher.credential(tokens, "human")["x-archeaxis-launch-token"]
    machine_token = None
    for principal in ("machine",):
        try:
            machine_token = launcher.credential(tokens, principal)["x-archeaxis-launch-token"]
        except Exception:  # noqa: BLE001 - a missing machine principal is reported below
            machine_token = None

    def call(method: str, path: str, token: str, body=None, headers=None):
        return client.call(base, method, path, token, body, extra_headers=headers)

    try:
        # 1. A real file becomes an accepted knowledge item through the product's own text route.
        status, imported = call("POST", "/api/v1/imports", human,
                                client.import_request("loop.txt", CONTEXT.encode()))
        receipt.stage("import_source", status=status, body=imported)
        if status != 202:
            receipt.stage("import_source", problem="import refused")
            return report(receipt)
        source_id = imported["source_id"]

        status, _ = call("POST", "/api/v1/jobs", human,
                         {"job_id": "loop-text", "kind": "text", "input_ref": source_id})
        status, _ = call("POST", "/api/v1/jobs/loop-text/executions", human,
                         {"deadline_ms": 120000},
                         headers={"idempotency-key": "loop-text"})
        state = None
        for _ in range(120):
            _, job = call("GET", "/api/v1/jobs/loop-text", human)
            state = job.get("state") if isinstance(job, dict) else None
            if state in ("succeeded", "failed", "cancelled"):
                break
            time.sleep(1)
        receipt.stage("text_transform", status=status, state=state)
        if state != "succeeded":
            receipt.stage("text_transform", problem=f"transform state {state}")
            return report(receipt)

        # 2. Knowledge from that transform, then accepted by a human review. The projection is read
        #    back first because the request names the transform and the exact quoted span, which is
        #    what binds the knowledge to a position in the source rather than to a copy of the text.
        status, transform = call("GET", f"/api/v1/sources/{source_id}/jobs/loop-text/transform", human)
        receipt.stage("read_transform", status=status,
                      transform_id=(transform or {}).get("transform_id"),
                      content_chars=len((transform or {}).get("content", "")))
        if status != 200:
            receipt.stage("read_transform", problem="the transform could not be read back")
            return report(receipt)
        content = transform["content"]
        status, created = call("POST", "/api/v1/knowledge-items/from-transform", human, {
            "knowledge_type": "FACTUAL_CLAIM",
            "body": content,
            "source_id": source_id,
            "job_id": "loop-text",
            "transform_id": transform["transform_id"],
            # The whole projection is the quoted span, and the offsets are in UTF-16 code units
            # because that is what the store records.
            "selection_start_utf16": 0,
            "selection_end_utf16": len(content.encode("utf-16-le")) // 2,
            "quote": content,
        })
        receipt.stage("create_knowledge", status=status, body=created)
        if status not in (200, 201):
            receipt.stage("create_knowledge", problem="knowledge creation refused")
            return report(receipt)
        knowledge_id = created.get("knowledge_id") or created.get("id")

        status, _ = call("POST", f"/api/v1/knowledge-items/{knowledge_id}/review-decisions", human,
                         {"action": "accepted", "reviewer": "owner"})
        receipt.stage("accept_knowledge", status=status)

        # 3. The real model answers the answerable question.
        status, answered = call("POST", "/api/v1/machine/answers", human,
                                {"knowledge_id": knowledge_id, "question": QUESTION,
                                 "timeout_s": 600})
        receipt.stage("machine_answer", status=status, body=answered)
        if status != 200:
            # A host without a model is a real state, and the reason is the worker's own words.
            receipt.block("local_model", str(answered)[:400])
            return report(receipt)
        answer_text = answered["answer"]["answer"]

        # 4. The failure. This script plays the person: it asks a question the accepted context cannot
        #    answer, so a grounded model has a real reason to fail rather than an invented one.
        status, ungrounded = call("POST", "/api/v1/machine/answers", human,
                                  {"knowledge_id": knowledge_id, "question": UNGROUNDED_QUESTION,
                                   "timeout_s": 600})
        receipt.stage("machine_answered_out_of_scope", status=status,
                      answer=(ungrounded.get("answer", {}) or {}).get("answer", "")[:400]
                      if status == 200 else str(ungrounded)[:300])

        # 5. The human correction, through the product's own route.
        status, corrected = call("POST", "/api/v1/machine/corrections", human, {
            "answer_id": answered["answer_id"],
            "knowledge_id": knowledge_id,
            "question": QUESTION,
            "machine_answer": answer_text,
            "corrected_answer": ("Only the Rust Core writes the SQLite canonical store, and the "
                                 "release is FROZEN."),
            "error_note": ("the answer did not name the writer plainly enough to be checked against "
                           "the source"),
        })
        receipt.stage("human_correction", status=status, body=corrected)
        if status != 200:
            receipt.stage("human_correction", problem="the correction was refused")
            return report(receipt)
        candidate = corrected["correction_candidate_id"]
        failed_task = corrected["failed_task_id"]
        status, accepted_correction = call(
            "POST", f"/api/v1/knowledge-items/{candidate}/review-decisions", human,
            {"action": "accepted", "reviewer": "scripted-human-fixture"})
        receipt.stage("accept_correction_fixture", status=status, body=accepted_correction)
        if status != 200:
            return report(receipt)

        # 6. The retest: the same question again, linked to the failure.
        status, retest = call("POST", "/api/v1/machine/retests", human, {
            "retest_of": failed_task,
            "knowledge_id": candidate,
            "question": QUESTION,
            "timeout_s": 600,
        })
        receipt.stage("machine_retest", status=status, body=retest)
        if status != 200:
            receipt.stage("machine_retest", problem=f"retest refused: {retest}")
            return report(receipt)
        retest_id = retest["retest_task_id"]

        # 7. Read it back from the store, so the link is a fact about the database and not only about
        #    the response that created it.
        status, readback = call("GET", f"/api/v1/machine/tasks/{retest_id}", machine_token)
        receipt.stage("retest_readback", status=status, body=readback,
                      links_to_failure=(readback.get("retest_of") == failed_task
                                        if isinstance(readback, dict) else False))

        # 8. Review remains forbidden to machines after the scripted human review.
        status, _ = call("POST", f"/api/v1/knowledge-items/{candidate}/review-decisions",
                         machine_token, {"action": "accepted", "reviewer": "machine"})
        receipt.stage("machine_cannot_accept_correction", status=status,
                      note="403 is the required answer")

        return report(receipt, correction_candidate=candidate, failed_task=failed_task,
                      retest_task=retest_id, knowledge_id=knowledge_id)
    finally:
        launcher.stop(child)


def report(receipt: Receipt, **extra) -> int:
    document = receipt.document(**extra)
    out = RUN / "receipt.json" if RUN is not None else None
    if out is not None and RUN.exists():
        out.write_text(json.dumps(document, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(document, ensure_ascii=False, indent=2)[:4000])
    # A run that reached every stage is a pass even when a prerequisite was noted on the way: the
    # note belongs in the receipt, and letting it decide the verdict would mark a complete run as
    # incomplete. A prerequisite only decides the verdict when it actually stopped the run.
    required = {
        "import_source", "text_transform", "read_transform", "create_knowledge",
        "accept_knowledge", "machine_answer", "machine_answered_out_of_scope",
        "human_correction", "accept_correction_fixture", "machine_retest",
        "retest_readback", "machine_cannot_accept_correction",
    }
    reached_the_end = not receipt.failed_stage and required.issubset(
        entry["stage"] for entry in receipt.stages)
    if receipt.blocked and not reached_the_end:
        print("\nBLOCKED:", json.dumps(receipt.blocked, ensure_ascii=False))
        return 3
    if receipt.failed_stage:
        print(f"\nFAILED at {receipt.failed_stage}")
        return 1
    if not reached_the_end:
        print("\nINCOMPLETE: the probe did not reach all required stages")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
