"""Run the DeepTutor grading journey against a real archeaxis-api process.

This is the reproducible form of the manual real-Core run: it starts the Core
binary with a finite launch document on stdin, walks material -> imported practice
question -> grants -> activity/attempt -> formal practice-grade -> read-only
disposition, restarts the process on the same workspace, and checks that the
disposition survives and the same event replays as a duplicate.

It uses only the standard library and never loads a model or the network. The
material and answers are synthetic. CI has no built Core binary, so this runs as a
qualification command against a binary the caller names; a skip is not evidence.

Usage:
  python -B scripts/ci/real_core_grading_journey.py \
      --core-exe .project-local/build/cargo/debug/archeaxis-api.exe \
      --workspace-dir .project-local/runs/<run>/real-core-journey \
      --receipt <dir>/journey-receipt.json
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import http.client
import json
import queue
import secrets
import sqlite3
import subprocess
import sys
import threading
import time
from pathlib import Path

TEXT_WORKER = "services/python-workers/transport/text_ndjson.py"
PRACTICE_WORKER = "services/learning-providers/deeptutor/practice_host_worker.py"
QUESTION_BANK = (
    '[{"question":"Which option?","question_type":"single_choice",'
    '"options":{"A":"first","B":"second"},"correct_answer":"B",'
    '"explanation":"SYNTHETIC_PRIVATE_EXPLANATION"}]'
)


class CoreFailure(RuntimeError):
    pass


def _reader(stream, sink: queue.Queue) -> None:
    for line in stream:
        sink.put(line.rstrip("\n"))
    sink.put(None)


class Core:
    def __init__(self, exe: Path, workspace: Path, python: Path) -> None:
        self.exe = exe
        self.workspace = workspace
        self.python = python
        self.proc: subprocess.Popen[str] | None = None
        self.port = 0
        self.token = secrets.token_hex(32)
        self.machine_token = secrets.token_hex(32)
        while self.machine_token == self.token:
            self.machine_token = secrets.token_hex(32)
        self.logs: list[str] = []

    def _launch_document(self) -> dict:
        root = Path(__file__).resolve().parents[2]
        staging = self.workspace / "staging"
        staging.mkdir(parents=True, exist_ok=True)
        return {
            "launch_token": self.token,
            "session_id": secrets.token_hex(16),
            "actor": "human",
            "protocol": "archeaxis.desktop-launch/v2",
            "machine_token": self.machine_token,
            "text_worker": {
                "python": str(self.python),
                "script": str(root / TEXT_WORKER),
                "staging": str(staging.resolve()),
                "routes": [
                    {"capability": "deeptutor.practice.import", "script": str(root / PRACTICE_WORKER)}
                ],
            },
            "openmaic_node_worker": None,
            "document_check_config": None,
            "document_check_config_error": None,
        }

    def start(self, timeout: float = 60.0) -> None:
        database = (self.workspace / "workspace.sqlite").resolve()
        launch = self.workspace / f"launch-{secrets.token_hex(4)}.json"
        launch.write_text(json.dumps(self._launch_document()), encoding="utf-8")
        self.proc = subprocess.Popen(
            [str(self.exe), str(database), "0"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.proc.stdin.write(launch.read_text(encoding="utf-8"))
        self.proc.stdin.close()
        out: queue.Queue = queue.Queue()
        err: queue.Queue = queue.Queue()
        threading.Thread(target=_reader, args=(self.proc.stdout, out), daemon=True).start()
        threading.Thread(target=_reader, args=(self.proc.stderr, err), daemon=True).start()
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                line = out.get(timeout=0.5)
            except queue.Empty:
                line = ""
            if line is None:
                break
            if line:
                self.logs.append(line)
            if "ready on http://" in line:
                self.port = int(line.rsplit(":", 1)[1])
                return
        stderr = []
        while not err.empty():
            value = err.get_nowait()
            if value:
                stderr.append(value)
        raise CoreFailure(f"core did not become ready; stdout={self.logs[-5:]}; stderr={stderr[-5:]}")

    def stop(self) -> None:
        if self.proc is None:
            return
        self.proc.terminate()
        try:
            self.proc.wait(timeout=15)
        except subprocess.TimeoutExpired:
            self.proc.kill()
            self.proc.wait(timeout=15)
        self.proc = None

    @property
    def url(self) -> str:
        return f"127.0.0.1:{self.port}"

    def request(
        self,
        method: str,
        path: str,
        body: dict | None = None,
        token: str | None = None,
    ) -> tuple[int, dict]:
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=60)
        payload = None if body is None else json.dumps(body, separators=(",", ":"))
        connection.request(
            method,
            path,
            body=payload,
            headers={
                "content-type": "application/json",
                "x-archeaxis-launch-token": token or self.token,
            },
        )
        response = connection.getresponse()
        raw = response.read()
        connection.close()
        try:
            parsed = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            parsed = {"raw": raw.decode("utf-8", "replace")}
        return response.status, parsed


def snapshot(document: dict, body: dict) -> dict:
    return {
        "document_id": body["document_id"],
        "version": body["version"],
        "content_sha256": body["content_sha256"],
    }


def expect(step: str, actual: int, expected: int, body: dict) -> dict:
    if actual != expected:
        raise CoreFailure(f"{step}: expected {expected}, got {actual}: {json.dumps(body)[:600]}")
    return body


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def patch_stale_dispatch(database: Path, activity: str, attempt: str, event: str) -> None:
    """Rewrite the completed claim as a dispatch from a previous process.

    The Core must be stopped. The claim stays internally consistent (the event index
    points at the rewritten bytes, the dispatch second predates the grace window), so
    a restarted Core can only finalize it - never trust it as a completed grade.
    """
    attempt_key = "provider_grade_attempt_" + _digest(activity + "\0" + attempt)
    event_key = "provider_grade_event_" + _digest(event)
    dispatch_key = "provider_grade_dispatch_" + _digest(event)
    connection = sqlite3.connect(database)
    try:
        row = connection.execute(
            "SELECT value FROM workspace_meta WHERE key=?", (attempt_key,)
        ).fetchone()
        if row is None:
            raise CoreFailure("grade claim disappeared before the stale-dispatch phase")
        claim = json.loads(row[0])
        claim["state"] = "DISPATCHED"
        # The stored member stays present with a null value: the custom deserializer
        # requires it, exactly like a live dispatch whose result has not arrived.
        claim["result_sha256"] = None
        raw = json.dumps(claim, separators=(",", ":"), ensure_ascii=False)
        connection.execute(
            "UPDATE workspace_meta SET value=? WHERE key=?", (raw, attempt_key)
        )
        index_row = connection.execute(
            "SELECT value FROM workspace_meta WHERE key=?", (event_key,)
        ).fetchone()
        if index_row is None:
            raise CoreFailure("grade event index disappeared before the stale-dispatch phase")
        index = json.loads(index_row[0])
        index["claim_sha256"] = hashlib.sha256(raw.encode()).hexdigest()
        connection.execute(
            "UPDATE workspace_meta SET value=? WHERE key=?",
            (json.dumps(index, separators=(",", ":")), event_key),
        )
        connection.execute(
            "UPDATE workspace_meta SET value=? WHERE key=?",
            (str(int(time.time()) - 1_000), dispatch_key),
        )
        # A real dispatch that never received a result leaves its attempt in the
        # pre-result state; the schema check requires exactly this shape.
        connection.execute(
            "UPDATE learning_provider_attempts SET state='pending', client_event_id=NULL, "
            "result_json=NULL, result_sha256=NULL, client_cancel_id=NULL, completed_at=NULL "
            "WHERE activity_id=? AND attempt_id=?",
            (activity, attempt),
        )
        connection.commit()
    finally:
        connection.close()



def run_journey(core: Core) -> dict:
    steps: list[dict] = []
    root = Path(__file__).resolve().parents[2]

    core.start()
    status, version = core.request("GET", "/api/v1/system/version")
    expect("version", status, 200, version)
    steps.append({"step": "version", "status": status, "runtime": version.get("runtime")})

    # The formal route guards must hold in the real process, where the actor is
    # derived from the launch credentials instead of an injected test header.
    probe = {
        "activity_id": "missing_activity",
        "attempt_id": "missing_attempt",
        "request": {
            "client_event_id": "missing_event",
            "question_document": {
                "document_id": "missing_question",
                "version": 1,
                "content_sha256": "a" * 64,
            },
            "question_grant": {
                "document_id": "missing_grant",
                "version": 1,
                "content_sha256": "b" * 64,
            },
            "answer": "A",
        },
    }
    grade_path = "/api/v1/learning/deeptutor/practice-grade"
    status, _ = core.request("POST", grade_path, probe, token=core.machine_token)
    if status != 403:
        raise CoreFailure(f"machine credential was not refused on the grading route: {status}")
    steps.append({"step": "machine credential refused on grading route", "status": status})
    status, unknown = core.request("POST", grade_path, probe)
    if status != 404:
        raise CoreFailure(f"missing activity was not reported not-found: {status} {unknown}")
    steps.append({"step": "unknown activity refused", "status": status})
    oversized = json.loads(json.dumps(probe))
    oversized["request"]["answer"] = "x" * 40_000
    status, _ = core.request("POST", grade_path, oversized)
    if status != 413:
        raise CoreFailure(f"oversize grade body was not rejected at the route limit: {status}")
    steps.append({"step": "oversize grade body refused", "status": status})


    status, material = core.request(
        "POST",
        "/api/v1/documents",
        {"title": "Real Core journey material", "editor_json": {"type": "doc", "content": []}},
    )
    expect("material create", status, 201, material)
    material_snapshot = snapshot(material, material)
    steps.append({"step": "material document", "status": status, "document_id": material_snapshot["document_id"]})

    status, imported_source = core.request(
        "POST",
        "/api/v1/imports",
        {
            "name": "synthetic.json",
            "content_base64": base64.b64encode(QUESTION_BANK.encode()).decode(),
        },
    )
    expect("source import", status, 202, imported_source)
    steps.append(
        {
            "step": "source import",
            "status": status,
            "source_id": imported_source["source_id"],
            "sha256": imported_source["sha256"],
        }
    )

    status, imported = core.request(
        "POST",
        "/api/v1/learning/deeptutor/practice-import",
        {
            "request_id": "auto_import",
            "source_id": imported_source["source_id"],
            "source_sha256": imported_source["sha256"],
            "source_duplicate": False,
            "source_format": "json",
            "source_row": 1,
            "material_snapshot": material_snapshot,
            "question_id": "synthetic_question",
            "create_request_id": "auto_create",
            "title": "Auto practice",
        },
    )
    expect("practice import", status, 200, imported)
    question_snapshot = imported["question_document"]
    view = imported["question_view"]
    if "correct_answer" in view.get("question", {}) or "SYNTHETIC_PRIVATE_EXPLANATION" in json.dumps(view):
        raise CoreFailure("the limited question view leaked the answer key")
    question_version = view["question_version"]
    steps.append(
        {
            "step": "practice import",
            "status": status,
            "question_document": question_snapshot["document_id"],
            "question_version": question_version,
            "answer_key_absent": True,
        }
    )

    grants = []
    for title, target in (("material grant", material_snapshot), ("question grant", question_snapshot)):
        status, grant = core.request(
            "POST",
            "/api/v1/documents",
            {
                "title": title,
                "editor_json": {
                    "type": "doc",
                    "content": [],
                    "attrs": {
                        "archeaxis_provider_material_grant": {
                            "schema": "archeaxis.provider-material-grant/v1",
                            "purpose": "practice",
                            "consumer": "deeptutor",
                            "operations": ["practice"],
                            "material": target,
                            "authorization_basis": "SYNTHETIC explicit human authorization",
                            "expires_at": None,
                            "state": "granted",
                        }
                    },
                },
            },
        )
        expect(title, status, 201, grant)
        grants.append(grant)
    steps.append({"step": "version-bound grants", "status": "201,201"})

    status, created = core.request(
        "POST",
        "/api/v1/learning/provider-activities",
        {
            "activity_id": "auto_activity",
            "material": material_snapshot,
            "provider": {"id": "deeptutor", "version": "1.7.1"},
            "question": {"question_id": "synthetic_question", "question_version": question_version},
            "grant": snapshot(grants[0], grants[0]),
        },
    )
    expect("activity create", status, 201, created)
    status, attempt = core.request(
        "POST",
        "/api/v1/learning/provider-activities/auto_activity/attempts",
        {"attempt_id": "auto_attempt"},
    )
    expect("attempt", status, 201, attempt)
    steps.append({"step": "activity and attempt", "status": "201,201"})

    grade_body = {
        "activity_id": "auto_activity",
        "attempt_id": "auto_attempt",
        "request": {
            "client_event_id": "auto_grade",
            "question_document": snapshot(question_snapshot, question_snapshot),
            "question_grant": snapshot(grants[1], grants[1]),
            "answer": "B",
        },
    }
    status, graded = core.request("POST", "/api/v1/learning/deeptutor/practice-grade", grade_body)
    expect("practice grade", status, 201, graded)
    if graded.get("provider_correct") is not True:
        raise CoreFailure(f"expected provider_correct=true: {graded}")
    steps.append(
        {
            "step": "practice grade",
            "status": status,
            "provider_correct": True,
            "provider_result_verification": graded.get("provider_result_verification"),
            "upstream_member_sha256": graded.get("grade_evidence", {}).get("upstream_member_sha256"),
        }
    )

    status, history = core.request("GET", "/api/v1/learning/provider-activities/auto_activity")
    expect("activity read", status, 200, history)
    disposition = history["attempts"][0]["grade_disposition"]
    if disposition["state"] != "COMPLETED" or not disposition.get("dispatched_at_unix"):
        raise CoreFailure(f"unexpected disposition: {disposition}")
    steps.append(
        {
            "step": "activity read disposition",
            "status": status,
            "state": disposition["state"],
            "dispatched_at_unix": disposition["dispatched_at_unix"],
        }
    )

    core.stop()
    core.start()
    steps.append({"step": "Core restart on same workspace", "status": "ready"})
    status, restarted = core.request("GET", "/api/v1/learning/provider-activities/auto_activity")
    expect("activity read after restart", status, 200, restarted)
    after = restarted["attempts"][0]["grade_disposition"]
    if after != disposition:
        raise CoreFailure(f"disposition changed after restart: {disposition} -> {after}")
    steps.append(
        {
            "step": "disposition after restart",
            "status": status,
            "state": after["state"],
            "dispatched_at_unix": after["dispatched_at_unix"],
        }
    )

    status, replay = core.request("POST", "/api/v1/learning/deeptutor/practice-grade", grade_body)
    expect("practice grade replay", status, 200, replay)
    if replay.get("duplicate") is not True or replay.get("provider_correct") is not True:
        raise CoreFailure(f"unexpected replay: {replay}")
    steps.append(
        {
            "step": "same-event replay after restart",
            "status": status,
            "duplicate": True,
            "provider_correct": True,
        }
    )
    core.stop()

    # A dispatch left over from a previous process and older than the maximum budget
    # cannot complete: a restarted Core finalizes it once as UNKNOWN, and the event
    # never gets a second grader run.
    patch_stale_dispatch(
        core.workspace / "workspace.sqlite", "auto_activity", "auto_attempt", "auto_grade"
    )
    steps.append(
        {"step": "simulate stale dispatch from a previous process", "status": "PATCHED"}
    )
    core.start()
    status, finalized = core.request("GET", "/api/v1/learning/provider-activities/auto_activity")
    expect("activity read after stale dispatch", status, 200, finalized)
    final = finalized["attempts"][0]["grade_disposition"]
    if final["state"] != "UNKNOWN":
        raise CoreFailure(f"startup finalization did not abandon the stale dispatch: {final}")
    steps.append(
        {
            "step": "startup finalization of stale dispatch",
            "status": status,
            "state": final["state"],
        }
    )
    core.stop()

    return {
        "schema": "aaos.real-core-process-journey/v1",
        "executed_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "core_exe": str(core.exe),
        "core_exe_bytes": core.exe.stat().st_size,
        "python": str(core.python),
        "workspace_db": str((core.workspace / "workspace.sqlite").resolve()),
        "steps": steps,
        "boundary": (
            "Real Core process, real HTTP, real Core SQLite writer and fixed workers on "
            "synthetic material with no model or network. Not an installed package, not the "
            "Tauri host, not real user data and not Owner acceptance."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--core-exe", required=True, type=Path)
    parser.add_argument("--workspace-dir", required=True, type=Path)
    parser.add_argument("--python", type=Path, default=None)
    parser.add_argument("--receipt", type=Path, default=None)
    args = parser.parse_args(argv)

    if not args.core_exe.is_file():
        print(f"core binary not found: {args.core_exe}", file=sys.stderr)
        return 2
    python = args.python or Path(sys.executable)
    if not python.is_file():
        print(f"python interpreter not found: {python}", file=sys.stderr)
        return 2

    args.workspace_dir.mkdir(parents=True, exist_ok=True)
    core = Core(args.core_exe.resolve(), args.workspace_dir.resolve(), python.resolve())
    try:
        receipt = run_journey(core)
    except CoreFailure as error:
        print(f"real-core journey failed: {error}", file=sys.stderr)
        core.stop()
        return 1
    finally:
        core.stop()
    text = json.dumps(receipt, ensure_ascii=False, indent=2) + "\n"
    if args.receipt:
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        args.receipt.write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
