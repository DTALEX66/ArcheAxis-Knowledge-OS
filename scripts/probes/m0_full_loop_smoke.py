"""One continuous M0 backend run: source to migration in a single Core session.

The mandate asks for the shortest complete loop driven through *all* stages with a
minimal representative input, not a per-stage demonstration. The other probes in this
directory each start a fresh Core and prove one link; this one uses **one workspace
database and one Core process** for the online chain, then restarts that same
workspace and finally runs the legacy migration, so the ordering and the shared
identity are what is being tested:

    source -> transform -> anchored Knowledge -> human acceptance -> V3 readback
    -> learning reference -> Assessment -> fixture answer -> FSRS schedule
    -> machine task failure -> human correction -> retest of the original failure
    -> restart readback -> online backup / restore -> legacy migration (copy)

This is SYNTHETIC protocol evidence: the source, human actions and model failure
are fixtures. It never qualifies real human learning or actual model inference.
It measures; it signs nothing. A stage that returns an unexpected status is recorded
with its status and body and the run stops there, so a partial run is a partial
receipt rather than a pass.

Two prerequisites decide whether the verdict means anything, and both are checked
before the run starts rather than inferred from a degraded stage:

* ``ARCHEAXIS_PYTHON`` must name the interpreter the Core uses for its scheduler
  worker. Without it ``SchedulerClient::from_env`` cannot answer, the review is
  recorded as unscheduled, and ``schedule_authority`` reads ``unavailable`` - which
  looks like a scheduling defect but is only a missing interpreter.
* this process must be able to load the vector extension, or the legacy plan reports
  ``vec_episodes`` as unreadable purely because of the interpreter it is running on.

Both are reported as ``blocked`` with the missing condition named, so a run that
could not have observed the whole loop is never written up as a product result.
"""

from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import types
import uuid
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
# The staged runtime already names its own Core through ARCHEAXIS_CORE_BIN; honouring
# it is what lets this probe qualify an installed runtime instead of only a checkout.
BINARY = Path(os.environ.get(
    "ARCHEAXIS_CORE_BIN",
    str(REPO / ".project-local" / "build" / "cargo" / "debug" / "archeaxis-api.exe")))
# The source must be an explicitly selected, authorised copy. Never silently read
# a repository runtime database just because one happens to exist at a legacy path.
LEGACY = Path(os.environ["ARCHEAXIS_LEGACY_COPY"]).resolve() if os.environ.get(
    "ARCHEAXIS_LEGACY_COPY", ""
).strip() else None

# The Core validates the launch identity as hex; a non-hex token is rejected with
# "invalid launch identity" and no readiness line.
TOKEN = "c" * 64
MACHINE_TOKEN = "e" * 64
SESSION = "d" * 32

# One session, two principals. The launch layer derives the actor from *which token*
# authenticated the call (`launch.rs::authenticate`), so a legacy v1 session is either
# human or machine and can never be both - which is what protocol v2 exists for:
# "v2 gives one owned session two distinct credentials". The router-level
# `x-archeaxis-actor` header is ignored once the launch layer has a session; only the
# in-process router tests see it.
LAUNCH = {
    "launch_token": TOKEN,
    "session_id": SESSION,
    "actor": "human",
    "protocol": "archeaxis.desktop-launch/v2",
    "machine_token": MACHINE_TOKEN,
}

ITEM_KEY = "m0-loop-item"
ANSWER = "radius 6371 km"
SOURCE_NAME = "m0-loop.md"
SOURCE_BYTES = b"# M0 loop\n\nThe Earth radius is 6371 km as measured by geodesy.\n"
QUOTE = "6371"


def _load(name: str, path: Path):
    """Load a module by file path, registering it (no sys.path mutation allowed)."""
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _register_package(name: str, directory: Path) -> None:
    package = types.ModuleType(name)
    package.__path__ = [str(directory)]  # type: ignore[attr-defined]
    sys.modules[name] = package


def _migrator():
    _register_package("shared", REPO / "shared")
    _load("shared.workspace_manifest", REPO / "shared" / "workspace_manifest.py")
    _register_package("app", REPO / "app")
    _register_package("app.workspace", REPO / "app" / "workspace")
    return _load("app.workspace.migrate", REPO / "app" / "workspace" / "migrate.py")


core = _load("core_client_m0", REPO / "shared" / "core_client.py")
runtime = _load("runtime_m0", REPO / "scripts" / "runtime" / "dev.py")
launcher = _load("launcher_m0", REPO / "scripts/release/backend_launcher.py")


def worker_profile() -> dict | None:
    """The staged runtime's own worker profile, when one is published.

    Reading it here is the point of the installed qualification: the caller passes a
    runtime root, not a hand-resolved interpreter.
    """
    for name in ("ARCHEAXIS_WORKER_PROFILE", "ARCHAXIS_WORKER_PROFILE"):
        raw = os.environ.get(name, "").strip()
        if not raw:
            continue
        path = Path(raw)
        try:
            return launcher.load_profile(path.parent, path.name)
        except (OSError, ValueError, RuntimeError) as error:
            raise SystemExit(f"invalid worker profile: {error}") from error
    return None


def start_core(db: Path, staging: Path) -> tuple[subprocess.Popen, str]:
    profile = worker_profile()
    if profile is None:
        worker = {
            "python": str(Path(sys.executable).resolve()),
            "script": str((REPO / "services/python-workers/transport/text_ndjson.py").resolve()),
            "staging": str(staging.resolve()),
        }
    else:
        # The run's own staging directory still wins so parallel runs stay isolated,
        # while the interpreter and worker script come from the published runtime.
        worker = {
            "python": str(profile["python"].resolve()),
            "script": str(profile["script"].resolve()),
            "staging": str(staging.resolve()),
        }
    # This probe measures the complete HTTP contract using a declared synthetic model.
    # Its worker never contacts an endpoint and its output is never REAL_MODEL evidence.
    mock = db.parent / "synthetic_machine_answer.py"
    if not mock.exists():
        mock.write_text(
            "import json, sys\nfrom pathlib import Path\n"
            "context = Path(sys.argv[1]).read_text(encoding='utf-8')\n"
            "answer = '6371 km' if '(geodesy)' in context else '7000 km (deliberate fixture error)'\n"
            "print(json.dumps({'answer': answer, 'model': 'synthetic/g4-contract-fixture'}))\n",
            encoding="utf-8")
    worker["routes"] = [{"capability": "machine.answer", "script": str(mock.resolve())}]
    child = subprocess.Popen(
        [str(BINARY), str(db), "0"],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, encoding="utf-8",
    )
    try:
        child.stdin.write(json.dumps({**LAUNCH, "text_worker": worker}) + "\n")
        child.stdin.flush()
        child.stdin.close()
        return child, launcher.wait_for_readiness(child, 0, 25)
    except BaseException:
        launcher.stop(child)
        raise


def stop_core(child: subprocess.Popen) -> None:
    launcher.stop(child)


def maintenance(action: str, db: Path, artifact: Path) -> tuple[int, dict]:
    result = subprocess.run(
        [str(BINARY), f"--maintenance-{action}", str(db), str(artifact)],
        capture_output=True, text=True, encoding="utf-8", cwd=REPO, timeout=120,
    )
    payload: dict = {}
    lines = (result.stdout or "").strip().splitlines()
    if lines:
        with contextlib.suppress(json.JSONDecodeError):
            payload = json.loads(lines[-1])
    return result.returncode, payload


def unmet_prerequisites() -> dict[str, str]:
    """Name the conditions under which this run cannot observe the whole loop.

    Checked before any Core process starts, because both conditions change what the
    receipt *means* while leaving every stage's HTTP status looking healthy. Naming
    them here keeps a degraded environment from being read as a product defect.
    """
    unmet: dict[str, str] = {}
    scheduler_python = os.environ.get("ARCHEAXIS_PYTHON", "").strip()
    if scheduler_python and not Path(scheduler_python).is_file():
        unmet["ARCHEAXIS_PYTHON"] = f"not a file: {scheduler_python}"
    if not scheduler_python:
        # A staged runtime publishes the interpreter in worker-profile.json, and the
        # Core resolves it from there. Requiring the variable as well would make this
        # probe demand exactly the manual step the runtime exists to remove.
        try:
            profile = worker_profile()
        except SystemExit as error:
            profile = None
            unmet["worker_profile"] = str(error)
        if profile is None and "worker_profile" not in unmet:
            unmet["ARCHEAXIS_PYTHON"] = (
                "not set and no worker profile published; the Core would report "
                "schedule_authority unavailable")
        elif profile is not None and not profile["python"].is_file():
            unmet["worker_profile.python"] = f"not a file: {profile['python']}"
    if LEGACY is None:
        unmet["ARCHEAXIS_LEGACY_COPY"] = "set to an explicitly authorised legacy database copy"
    elif not LEGACY.is_file():
        unmet["ARCHEAXIS_LEGACY_COPY"] = "selected legacy database copy is not a file"
    try:
        import sqlite_vec  # noqa: F401
    except Exception as error:  # pragma: no cover - depends on the interpreter
        unmet["sqlite_vec"] = f"{type(error).__name__}: {error}"
    return unmet


def binary_identity(path: Path) -> dict:
    """The artefact that actually ran, not the path someone typed."""
    stat = path.stat()
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return {"path": str(path), "sha256": digest.hexdigest(),
            "size": stat.st_size, "mtime": stat.st_mtime}


def source_identity() -> dict:
    """What this run tested, including the working state when it is not committed."""
    dirty = os.environ.get("ARCHEAXIS_SOURCE_DIRTY", "")
    return {
        "commit": os.environ.get("ARCHEAXIS_SOURCE_COMMIT", ""),
        "tree": os.environ.get("ARCHEAXIS_SOURCE_TREE", ""),
        "dirty": dirty == "1",
        "patch_sha256": os.environ.get("ARCHEAXIS_SOURCE_PATCH_SHA256", ""),
        "worktree_root": os.environ.get("ARCHEAXIS_WORKTREE_ROOT", ""),
        "run_id": os.environ.get("ARCHEAXIS_RUN_ID", ""),
        "identity_recorded": bool(dirty) and bool(os.environ.get("ARCHEAXIS_SOURCE_COMMIT")),
    }


def verdict_errors(receipt: dict) -> list[str]:
    """Fail closed on every measured leg of this synthetic protocol journey."""
    stages = receipt.get("stages", [])
    by = {s.get("stage"): s for s in stages}
    errors = []
    if receipt.get("failed_stage") or len(by) != len(stages):
        errors.append("failed or duplicate stage")
    required_http = (
        "import_source", "enqueue", "execute", "transform_readback",
        "promote_anchored_knowledge", "knowledge_v3_readback", "search", "human_accept",
        "knowledge_v3_after_accept", "learning_reference", "learning_event",
        "learning_event_replay", "assessment", "answer_recorded", "learning_state",
        "machine_answer", "machine_task_failed", "human_correction", "accept_successor", "machine_retest",
        "machine_readback", "pre_restart_learning_state", "restart_learning_state", "restart_knowledge_v3",
    )
    for name in required_http:
        if by.get(name, {}).get("status") not in (200, 201, 202):
            errors.append(f"{name}: missing or failed HTTP stage")
    def field(name, key):
        return by.get(name, {}).get(key)

    def require(condition, reason):
        if not condition:
            errors.append(reason)

    knowledge = field("promote_anchored_knowledge", "knowledge_id")
    anchor = field("promote_anchored_knowledge", "anchor_id")
    successor = field("human_correction", "successor_id")
    failed_task = field("machine_task_failed", "task_id")
    require(bool(field("import_source", "source_id")), "source identity missing")
    require(field("job_settled", "state") == "succeeded", "job did not succeed")
    require(bool(field("transform_readback", "transform_id")), "transform identity missing")
    require(bool(knowledge and anchor), "knowledge or anchor identity missing")
    require(field("search", "source_found") is True, "search did not find this source")
    require(field("knowledge_v3_after_accept", "status_value") == "accepted", "knowledge not accepted")
    require(field("learning_event_replay", "duplicate") is True, "event replay not deduplicated")
    require(bool(field("assessment", "assessment_id"))
            and field("assessment", "knowledge_version") == knowledge, "assessment identity mismatch")
    require(field("answer_recorded", "schedule_authority") == "fsrs"
            and bool(field("answer_recorded", "next_review")), "answer has no FSRS schedule")
    for name in ("learning_state", "restart_learning_state"):
        require(field(name, "answer") == ANSWER and bool(field(name, "next_review")),
                f"{name}: answer or schedule missing")
    require(bool(field("pre_restart_learning_state", "state"))
            and field("pre_restart_learning_state", "state") == field("restart_learning_state", "state"),
            "restart learning state changed")
    require(field("learning_state", "next_review") == field("restart_learning_state", "next_review"),
            "restart schedule changed")
    for name in ("knowledge_v3_readback", "restart_knowledge_v3"):
        require(bool(knowledge and anchor) and field(name, "knowledge_id") == knowledge
                and field(name, "anchor_id") == anchor, f"{name}: knowledge identity changed")
    require(bool(field("machine_answer", "answer_id"))
            and field("machine_answer", "answer_id") == field("machine_task_failed", "answer_id")
            and field("machine_answer", "answer_id") == field("human_correction", "answer_id"),
            "machine answer/correction provenance mismatch")
    require(bool(successor) and successor != knowledge, "correction has no successor")
    for name in ("machine_retest", "machine_readback"):
        require(bool(failed_task and successor) and field(name, "retest_of") == failed_task
                and field(name, "knowledge_version") == successor,
                f"{name}: correction/retest identity mismatch")
    require(bool(field("machine_retest", "task_id"))
            and field("machine_retest", "task_id") == field("machine_readback", "task_id"),
            "machine task identity changed")
    require(field("online_backup", "exit_code") == 0, "backup failed")
    before = field("online_restore", "counts_before")
    require(field("online_restore", "exit_code") == 0
            and field("online_restore", "verified") is True and bool(before)
            and before == field("online_restore", "counts_after")
            and before != field("online_restore", "counts_mutated"), "restore not demonstrated")
    require(field("legacy_migration", "status") == "ok"
            and field("legacy_migration", "original_untouched") is True,
            "legacy migration not verified")
    return errors


def main() -> int:
    with contextlib.suppress(Exception):
        sys.stdout.reconfigure(encoding="utf-8")
    if not BINARY.is_file():
        print(json.dumps({"ok": False, "blocked": "core binary not built", "path": str(BINARY)}))
        return 2
    unmet = unmet_prerequisites()
    if unmet:
        print(json.dumps({
            "ok": False,
            "blocked": "run prerequisites not met; the loop could not be observed",
            "unmet": unmet,
            "interpreter": sys.executable,
            "note": "run this probe through scripts/runtime/dev.py with the project "
                    "interpreter, and pass that same interpreter as the command",
        }, ensure_ascii=False, indent=2))
        return 2

    work = runtime.artifact_directory(REPO, "m0loop")
    db = work / "workspace.sqlite"
    staging = work / "worker-staging"
    receipt: dict = {"ok": False, "workdir": str(work), "stages": [],
                     "evidence_level": "SYNTHETIC", "real_m0_verified": False,
                     "core_binary": binary_identity(BINARY),
                     "source": source_identity(),
                     "interpreter": sys.executable}
    order: list[str] = []

    def stage(name: str, **fields: object) -> None:
        order.append(name)
        receipt["stages"].append({"stage": name, **fields})

    child, base = start_core(db, staging)
    try:
        # 1. Source.
        status, imported = core.call(base, "POST", "/api/v1/imports", TOKEN,
                                     core.import_request(SOURCE_NAME, SOURCE_BYTES))
        source_id = imported.get("source_id") if isinstance(imported, dict) else None
        stage("import_source", status=status, source_id=source_id)
        if status not in (200, 201, 202) or not source_id:
            receipt["failed_stage"] = "import_source"
            raise SystemExit

        # 2. Job + worker execution.
        job_id = f"m0-{uuid.uuid4().hex[:16]}"
        status, queued = core.call(base, "POST", "/api/v1/jobs", TOKEN,
                                   {"job_id": job_id, "kind": "text", "input_ref": source_id})
        stage("enqueue", status=status, job_id=job_id)
        status, started = core.call(
            base, "POST", f"/api/v1/jobs/{job_id}/executions", TOKEN,
            {"deadline_ms": 300000}, extra_headers={"idempotency-key": job_id},
        )
        stage("execute", status=status)

        import time

        state = None
        for _ in range(40):
            status, final = core.call(base, "GET", f"/api/v1/jobs/{job_id}", TOKEN)
            state = final.get("state") if isinstance(final, dict) else None
            if state in ("succeeded", "failed", "cancelled"):
                break
            time.sleep(0.25)
        stage("job_settled", state=state)
        if state != "succeeded":
            receipt["failed_stage"] = "job_settled"
            raise SystemExit

        # 3. Transform readback, then the evidence-anchored promotion.
        status, transform = core.call(
            base, "GET", f"/api/v1/sources/{source_id}/jobs/{job_id}/transform", TOKEN)
        transform_id = None
        transform_text = ""
        if isinstance(transform, dict):
            # `source_job_transform` returns {source_id, job_id, transform_id, raw_sha256, content}.
            transform_id = transform.get("transform_id")
            transform_text = str(transform.get("content") or "")
        stage("transform_readback", status=status, transform_id=transform_id,
              text_chars=len(transform_text))
        if status != 200 or not transform_id or QUOTE not in transform_text:
            receipt["failed_stage"] = "transform_readback"
            raise SystemExit

        index = transform_text.index(QUOTE)
        start_utf16 = len(transform_text[:index].encode("utf-16-le")) // 2
        status, created = core.call(
            base, "POST", "/api/v1/knowledge-items/from-transform", TOKEN,
            {
                "knowledge_type": "OBSERVATION",
                "body": "The Earth radius is 6371 km as measured by geodesy.",
                "source_id": source_id,
                "job_id": job_id,
                "transform_id": transform_id,
                "selection_start_utf16": start_utf16,
                "selection_end_utf16": start_utf16 + len(QUOTE),
                "quote": QUOTE,
            },
        )
        knowledge_id = created.get("knowledge_id") if isinstance(created, dict) else None
        anchor_id = created.get("anchor_id") if isinstance(created, dict) else None
        stage("promote_anchored_knowledge", status=status, knowledge_id=knowledge_id,
              anchor_id=anchor_id, candidate_status=created.get("status") if isinstance(created, dict) else None,
              response=str(created)[:300])
        if status not in (200, 201) or not knowledge_id:
            receipt["failed_stage"] = "promote_anchored_knowledge"
            raise SystemExit

        status, v3 = core.call(base, "GET", f"/api/v1/knowledge-items/{knowledge_id}/v3", TOKEN)
        stage("knowledge_v3_readback", status=status, v3=v3,
              knowledge_id=v3.get("knowledge_id") if isinstance(v3, dict) else None,
              anchor_id=v3.get("anchor_id") if isinstance(v3, dict) else None)
        status, search = core.call(base, "GET", core.search_path(QUOTE), TOKEN)
        stage("search", status=status,
              items=len(search.get("items", [])) if isinstance(search, dict) else None,
              source_found=isinstance(search, dict) and any(
                  hit.get("source_id") == source_id and hit.get("transform_id") == transform_id
                  for hit in search.get("transforms", []) if isinstance(hit, dict)))

        # 4. Human acceptance - the governance boundary, not an automatic promotion.
        status, accepted = core.call(
            base, "POST", f"/api/v1/knowledge-items/{knowledge_id}/review-decisions", TOKEN,
            core.review_request("accepted", "owner", note="human acceptance in the M0 loop"),
        )
        stage("human_accept", status=status, response=accepted)
        if status not in (200, 201):
            receipt["failed_stage"] = "human_accept"
            raise SystemExit
        status, v3_after = core.call(base, "GET", f"/api/v1/knowledge-items/{knowledge_id}/v3", TOKEN)
        stage("knowledge_v3_after_accept", status=status,
              status_value=v3_after.get("status") if isinstance(v3_after, dict) else None,
              owner=v3_after.get("owner") if isinstance(v3_after, dict) else None)

        # 5. Learning: reference, Assessment, real answer, FSRS schedule.
        status, reference = core.call(
            base, "POST", f"/api/v1/learning/items/{ITEM_KEY}/references", TOKEN,
            core.reference_request(ITEM_KEY, knowledge_id),
        )
        stage("learning_reference", status=status)
        # A first learning event, then the answer-bearing review. Recorded separately
        # because the two paths report different schedule authorities.
        status, event = core.call(
            base, "POST", "/api/v1/learning/events", TOKEN,
            core.learning_event_request(ITEM_KEY, True, "m0-event-1"),
        )
        stage("learning_event", status=status,
              schedule_authority=event.get("schedule_authority") if isinstance(event, dict) else None,
              next_review=event.get("next_review") if isinstance(event, dict) else None)
        status, event_replay = core.call(
            base, "POST", "/api/v1/learning/events", TOKEN,
            core.learning_event_request(ITEM_KEY, True, "m0-event-1"),
        )
        stage("learning_event_replay", status=status,
              duplicate=event_replay.get("duplicate") if isinstance(event_replay, dict) else None,
              schedule_authority=event_replay.get("schedule_authority")
              if isinstance(event_replay, dict) else None,
              next_review=event_replay.get("next_review") if isinstance(event_replay, dict) else None)
        status, assessment = core.call(
            base, "POST", f"/api/v1/learning/items/{ITEM_KEY}/assessment", TOKEN,
            {"knowledge_id": knowledge_id},
        )
        assessment_id = assessment.get("assessment_id") if isinstance(assessment, dict) else None
        knowledge_version = assessment.get("knowledge_version") if isinstance(assessment, dict) else None
        stage("assessment", status=status, assessment_id=assessment_id,
              knowledge_version=knowledge_version)
        review_body = {
            "item_key": ITEM_KEY, "client_event_id": "m0-review-1", "correct": True, "rating": 3,
            "answer": ANSWER, "assessment_id": assessment_id, "knowledge_version": knowledge_version,
            "now": "2026-09-26T12:00:00+00:00",
        }
        status, review = core.call(base, "POST", "/api/v1/learning/reviews", TOKEN, review_body,
                                  extra_headers={"x-archeaxis-actor": "owner"})
        stage("answer_recorded", status=status, schedule_authority=review.get("schedule_authority")
              if isinstance(review, dict) else None,
              next_review_days=review.get("next_review_days") if isinstance(review, dict) else None,
              next_review=review.get("next_review") if isinstance(review, dict) else None,
              response=review)
        status, learning_state = core.call(
            base, "GET", f"/api/v1/learning/items/{ITEM_KEY}/state", TOKEN)
        learner = learning_state.get("learner", {}) if isinstance(learning_state, dict) else {}
        stage("learning_state", status=status,
              answer=(learner.get("latest_review") or {}).get("answer"),
              next_review=learner.get("next_review"), state=learning_state)

        # 6. The controlled worker's actual output is persisted by the answer route.
        question = "What is the Earth's radius?"
        status, answered = core.call(base, "POST", "/api/v1/machine/answers", TOKEN,
                                    {"knowledge_id": knowledge_id, "question": question})
        stage("machine_answer", status=status, answer_id=answered.get("answer_id")
              if isinstance(answered, dict) else None, evidence_level="SYNTHETIC")
        if status != 200:
            receipt["failed_stage"] = "machine_answer"
            raise SystemExit
        # 7. The scripted human corrects exactly that stored answer.
        status, corrected = core.call(base, "POST", "/api/v1/machine/corrections", TOKEN, {
            "answer_id": answered["answer_id"], "knowledge_id": knowledge_id,
            "question": question, "machine_answer": answered["answer"]["answer"],
            "corrected_answer": "The Earth radius is 6371 km (geodesy).",
            "error_note": "synthetic worker deliberately answered 7000 instead of 6371",
            "reviewer": "synthetic-human-fixture",
        })
        failed_task = corrected.get("failed_task_id") if isinstance(corrected, dict) else None
        successor_id = corrected.get("correction_candidate_id") if isinstance(corrected, dict) else None
        stage("machine_task_failed", status=status, task_id=failed_task,
              answer_id=answered["answer_id"])
        stage("human_correction", status=status, successor_id=successor_id,
              answer_id=corrected.get("answer_id") if isinstance(corrected, dict) else None)
        if status != 200 or not successor_id or not failed_task:
            receipt["failed_stage"] = "human_correction"
            raise SystemExit
        status, _ = core.call(
            base, "POST", f"/api/v1/knowledge-items/{successor_id}/review-decisions", TOKEN,
            core.review_request("accepted", "synthetic-human-fixture", note="accepting fixture correction"),
        )
        stage("accept_successor", status=status)
        status, retest = core.call(base, "POST", "/api/v1/machine/retests", TOKEN, {
            "retest_of": failed_task, "knowledge_id": successor_id, "question": question,
        })
        retest_task = retest.get("retest_task_id") if isinstance(retest, dict) else None
        stage("machine_retest", status=status, task_id=retest_task,
              retest_of=retest.get("retest_of") if isinstance(retest, dict) else None,
              knowledge_version=retest.get("knowledge_id") if isinstance(retest, dict) else None,
              response=str(retest)[:300])
        if status != 200 or not retest_task:
            receipt["failed_stage"] = "machine_retest"
            raise SystemExit
        status, readback = core.call(base, "GET", f"/api/v1/machine/tasks/{retest_task}", MACHINE_TOKEN)
        stage("machine_readback", status=status,
              task_id=readback.get("task_id") if isinstance(readback, dict) else None,
              knowledge_version=str(readback.get("knowledge_version", "")).split("@", 1)[0]
              if isinstance(readback, dict) else None,
              retest_of=readback.get("retest_of") if isinstance(readback, dict) else None)
        status, final_learning_state = core.call(
            base, "GET", f"/api/v1/learning/items/{ITEM_KEY}/state", TOKEN)
        stage("pre_restart_learning_state", status=status, state=final_learning_state)
    except SystemExit:
        pass
    finally:
        stop_core(child)

    if "failed_stage" in receipt:
        receipt["ok"] = False
        out = work / "m0-loop-receipt.json"
        out.write_text(json.dumps(receipt, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
        print(json.dumps(receipt, ensure_ascii=False, indent=2, default=str))
        print(f"\nreceipt: {out}")
        return 1

    # 8. Restart the same workspace and read the state back.
    child, base = start_core(db, staging)
    try:
        status, state2 = core.call(base, "GET", f"/api/v1/learning/items/{ITEM_KEY}/state", TOKEN)
        learner2 = state2.get("learner", {}) if isinstance(state2, dict) else {}
        stage("restart_learning_state", status=status,
              answer=(learner2.get("latest_review") or {}).get("answer"),
              next_review=learner2.get("next_review"), state=state2)
        status, v3_2 = core.call(base, "GET", f"/api/v1/knowledge-items/{knowledge_id}/v3", TOKEN)
        stage("restart_knowledge_v3", status=status,
              knowledge_id=v3_2.get("knowledge_id") if isinstance(v3_2, dict) else None,
              anchor_id=v3_2.get("anchor_id") if isinstance(v3_2, dict) else None)
    finally:
        stop_core(child)

    # 9. Online backup, a mutation, and a verified restore of the same workspace.
    backup = work / "online-backup.sqlite"
    code, backup_receipt = maintenance("backup", db, backup)
    stage("online_backup", exit_code=code, schema_version=backup_receipt.get("schema_version"))

    def counts() -> dict:
        with contextlib.closing(sqlite3.connect(f"file:{db}?mode=ro", uri=True)) as connection:
            names = {r[0] for r in connection.execute("select name from sqlite_master where type='table'")}
            result = {}
            for name in ("knowledge", "knowledge_supersedes", "review_events",
                         "learning_assessments", "learning_events", "machine_tasks"):
                if name in names:
                    with contextlib.suppress(sqlite3.OperationalError):
                        result[name] = connection.execute(f'select count(*) from "{name}"').fetchone()[0]
            return result

    before = counts()
    with contextlib.closing(sqlite3.connect(db)) as connection:
        connection.execute("delete from learning_events")
        connection.commit()
    mutated = counts()
    code, restore_receipt = maintenance("restore", db, backup)
    after = counts()
    stage("online_restore", exit_code=code, verified=restore_receipt.get("verified"),
          counts_before=before, counts_mutated=mutated, counts_after=after)

    # 10. Legacy migration, on a copy of the real asset (a different database by nature).
    migrator = _migrator()
    create_workspace = sys.modules["shared.workspace_manifest"].create_workspace
    migration: dict = {}
    if LEGACY is not None and LEGACY.is_file():
        original_before = hashlib.sha256(LEGACY.read_bytes()).hexdigest()
        legacy_copy = work / "legacy-copy.sqlite"
        shutil.copyfile(LEGACY, legacy_copy)
        ws = work / "legacy-ws"
        create_workspace(work, "legacy-ws")
        result = migrator.migrate(legacy_copy, ws, backup_dir=work / "legacy-backups")
        original_after = hashlib.sha256(LEGACY.read_bytes()).hexdigest()
        migration = {
            "status": result.get("status"),
            "legacy_db_kept": result.get("legacy_db_kept"),
            "tables_planned": len(result.get("tables") or []),
            "copied_entries": len(result.get("copied") or []),
            "files_written": len(result.get("files") or []),
            "unreadable_tables": result.get("unreadable_tables"),
            "original_untouched": original_before == original_after,
        }
    else:
        migration = {"skipped": "legacy database not present"}
    stage("legacy_migration", **migration)

    receipt["stage_order"] = order
    receipt["validation_errors"] = verdict_errors(receipt)
    receipt["chain_stages_verified"] = not receipt["validation_errors"]
    receipt["ok"] = receipt["chain_stages_verified"]
    out = work / "m0-loop-receipt.json"
    out.write_text(json.dumps(receipt, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    print(json.dumps(receipt, ensure_ascii=False, indent=2, default=str))
    print(f"\nreceipt: {out}")
    return 0 if receipt["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
