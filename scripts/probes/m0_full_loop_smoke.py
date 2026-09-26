"""One continuous M0 backend run: source to migration in a single Core session.

The mandate asks for the shortest complete loop driven through *all* stages with a
minimal representative input, not a per-stage demonstration. The other probes in this
directory each start a fresh Core and prove one link; this one uses **one workspace
database and one Core process** for the online chain, then restarts that same
workspace and finally runs the legacy migration, so the ordering and the shared
identity are what is being tested:

    source -> transform -> anchored Knowledge -> human acceptance -> V3 readback
    -> learning reference -> Assessment -> real answer -> FSRS schedule
    -> machine task failure -> human correction -> retest of the original failure
    -> restart readback -> online backup / restore -> legacy migration (copy)

It measures; it signs nothing. A stage that returns an unexpected status is recorded
with its status and body and the run stops there, so a partial run is a partial
receipt rather than a pass.
"""

from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import json
import shutil
import sqlite3
import subprocess
import sys
import types
import uuid
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
BINARY = REPO / ".project-local" / "build" / "cargo" / "debug" / "archeaxis-api.exe"
LEGACY = REPO / "data" / "cognitive_os.sqlite"

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
    child.stdin.write(json.dumps({**LAUNCH, "text_worker": worker}) + "\n")
    child.stdin.flush()
    child.stdin.close()
    import time

    deadline = time.time() + 25
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
        raise SystemExit(f"core not ready: stdout={line[:120]!r} stderr={err[:300]!r}")
    return child, f"http://127.0.0.1:{line.split('127.0.0.1:', 1)[1].split()[0].strip()}"


def stop_core(child: subprocess.Popen) -> None:
    with contextlib.suppress(Exception):
        child.kill()
        child.wait()


def maintenance(action: str, db: Path, artifact: Path) -> tuple[int, dict]:
    result = subprocess.run(
        [str(BINARY), f"--maintenance-{action}", str(db), str(artifact)],
        capture_output=True, text=True, encoding="utf-8", cwd=REPO,
    )
    payload: dict = {}
    lines = (result.stdout or "").strip().splitlines()
    if lines:
        with contextlib.suppress(json.JSONDecodeError):
            payload = json.loads(lines[-1])
    return result.returncode, payload


def main() -> int:
    with contextlib.suppress(Exception):
        sys.stdout.reconfigure(encoding="utf-8")
    if not BINARY.is_file():
        print(json.dumps({"ok": False, "blocked": "core binary not built", "path": str(BINARY)}))
        return 2

    work = REPO / ".project-local" / "m0loop" / uuid.uuid4().hex[:8]
    work.mkdir(parents=True, exist_ok=True)
    db = work / "workspace.sqlite"
    staging = work / "worker-staging"
    receipt: dict = {"ok": False, "workdir": str(work), "stages": []}
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
        stage("knowledge_v3_readback", status=status, v3=v3)
        status, search = core.call(base, "GET", core.search_path(QUOTE), TOKEN)
        stage("search", status=status,
              items=len(search.get("items", [])) if isinstance(search, dict) else None)

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
              next_review=learner.get("next_review"))

        # 6. Machine failure on the same accepted knowledge version.
        failed_task = f"m0-machine-{uuid.uuid4().hex[:8]}"
        status, failed = core.call(
            base, "POST", "/api/v1/machine/tasks", MACHINE_TOKEN,
            {
                "task_id": failed_task, "conditions": "fixed sample",
                "knowledge_version": knowledge_id, "method_version": "method-1",
                "tool_version": "tool-1", "model_version": "stub/local-stub",
                "scope": "one extraction task", "outcome": "failed",
                "failure": "declared stub model, no real inference performed",
            },

        )
        stage("machine_task_failed", status=status, task_id=failed_task,
              response=str(failed)[:300])

        # 7. Human correction creates a successor revision; retest points at the original failure.
        status, corrected = core.call(
            base, "POST", f"/api/v1/knowledge-items/{knowledge_id}/review-decisions", TOKEN,
            core.review_request("modified", "owner", new_body="The Earth radius is 6371 km (geodesy).",
                                note="human correction after the machine failure"),
        )
        successor_id = corrected.get("knowledge_id") if isinstance(corrected, dict) else None
        stage("human_correction", status=status, successor_id=successor_id)
        if successor_id:
            status, _ = core.call(
                base, "POST", f"/api/v1/knowledge-items/{successor_id}/review-decisions", TOKEN,
                core.review_request("accepted", "owner", note="accepting the corrected revision"),
            )
            stage("accept_successor", status=status)

        retest_task = f"m0-retest-{uuid.uuid4().hex[:8]}"
        status, retest = core.call(
            base, "POST", "/api/v1/machine/tasks", MACHINE_TOKEN,
            {
                "task_id": retest_task, "conditions": "fixed sample after human correction",
                "knowledge_version": successor_id or knowledge_id, "method_version": "method-1",
                "tool_version": "tool-1", "model_version": "stub/local-stub",
                "scope": "one extraction task", "outcome": "succeeded",
                "retest_of": failed_task,
            },

        )
        stage("machine_retest", status=status, task_id=retest_task, retest_of=failed_task,
              response=str(retest)[:300])
        status, readback = core.call(base, "GET", f"/api/v1/machine/tasks/{retest_task}", MACHINE_TOKEN)
        stage("machine_readback", status=status,
              retest_of=readback.get("retest_of") if isinstance(readback, dict) else None)
    except SystemExit:
        pass
    finally:
        stop_core(child)

    if "failed_stage" in receipt:
        stop_core
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
              next_review=learner2.get("next_review"))
        status, v3_2 = core.call(base, "GET", f"/api/v1/knowledge-items/{knowledge_id}/v3", TOKEN)
        stage("restart_knowledge_v3", status=status,
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
            for name in ("knowledge_items", "learning_events", "machine_tasks"):
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
    if LEGACY.is_file():
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
    # The verdict must not be satisfied by only the last two stages: a run where the
    # machine principal was rejected still restored and migrated cleanly, so each
    # stage that carries chain meaning is required explicitly.
    def status_of(name: str) -> object:
        for entry in receipt["stages"]:
            if entry.get("stage") == name:
                return entry.get("status") or entry.get("state")
        return None

    machine_ok = (
        status_of("machine_task_failed") in (200, 201)
        and status_of("machine_retest") in (200, 201)
        and status_of("machine_readback") == 200
    )
    schedule_ok = any(
        entry.get("schedule_authority") == "fsrs"
        for entry in receipt["stages"]
        if "schedule_authority" in entry
    )
    receipt["machine_principal_accepted"] = machine_ok
    receipt["fsrs_schedule_observed"] = schedule_ok
    # Two verdicts, kept apart on purpose. `chain_stages_verified` says every stage of
    # the loop ran and the persistence legs held. `ok` additionally requires the FSRS
    # schedule the dedicated learning probe observes - it is NOT observed on this path,
    # where the same review returns schedule_authority "unavailable" with
    # next_review_days -2 and schedule_state null, so the strict verdict is false and
    # the deviation is a recorded open question rather than a silent pass.
    receipt["chain_stages_verified"] = bool(
        "failed_stage" not in receipt
        and not receipt.get("failed_stage")
        and status_of("promote_anchored_knowledge") in (200, 201)
        and status_of("human_accept") in (200, 201)
        and status_of("answer_recorded") in (200, 201)
        and machine_ok
        and restore_receipt.get("verified") is True
        and after == before
        and migration.get("original_untouched", False)
        and migration.get("status") == "ok"
    )
    receipt["ok"] = bool(receipt["chain_stages_verified"] and schedule_ok)
    out = work / "m0-loop-receipt.json"
    out.write_text(json.dumps(receipt, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    print(json.dumps(receipt, ensure_ascii=False, indent=2, default=str))
    print(f"\nreceipt: {out}")
    return 0 if receipt["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
