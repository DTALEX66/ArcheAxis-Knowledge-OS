"""Q13 fault injection over the real candidate Core and worker protocol.

Fault shims live in a new data root, import the candidate transport, then inject
one hang or abrupt worker exit. Candidate files are never edited. Measurements
are Core API integration, not installed UI cold-start or whole-process memory.
"""
from __future__ import annotations

import argparse
import ctypes
import json
import os
import secrets
import subprocess
import time
import uuid
from ctypes import wintypes
from pathlib import Path

import aaos01_office_runtime_loop as office

REPO = Path(__file__).resolve().parents[2]
BUDGETS = {"core_readiness_seconds": 10, "fault_settlement_seconds": 8,
           "recovery_job_seconds": 5, "timeout_deadline_ms": 1000,
           "cancel_deadline_ms": 30000, "fault_fixture_hang_seconds": 30,
           "worker_observation_seconds": 8}
TERMINAL = {"succeeded", "failed", "rejected", "cancelled"}


def alive(pid):
    """Windows read-only process query; os.kill(pid, 0) is unsafe on Windows."""
    if os.name != "nt":
        try:
            os.kill(pid, 0)
            return True
        except ProcessLookupError:
            return False
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = kernel.OpenProcess(0x1000, False, pid)
    if not handle:
        error = ctypes.get_last_error()
        if error == 87:
            return False
        raise OSError(error, "cannot query owned worker liveness")
    try:
        code = wintypes.DWORD()
        if not kernel.GetExitCodeProcess(handle, ctypes.byref(code)):
            raise ctypes.WinError(ctypes.get_last_error())
        return code.value == 259
    finally:
        kernel.CloseHandle(handle)


def start(candidate, work, script, launcher):
    profile = launcher.load_profile(candidate)
    token = secrets.token_hex(32)
    staging = work / "worker-staging"
    staging.mkdir()
    launch = {"launch_token": token, "machine_token": secrets.token_hex(32),
              "session_id": secrets.token_hex(16), "actor": "human",
              "protocol": launcher.LAUNCH_PROTOCOL,
              "text_worker": {"python": str(profile["python"]), "script": str(script), "staging": str(staging)}}
    before = time.monotonic()
    child = subprocess.Popen([str(candidate / "core/archeaxis-api.exe"), str(work / "workspace.sqlite"), "0"],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, encoding="utf-8", cwd=candidate, env=launcher.build_environment(candidate))
    try:
        child.stdin.write(json.dumps(launch) + "\n")
        child.stdin.close()
        base = launcher.wait_for_readiness(child, 0, BUDGETS["core_readiness_seconds"])
        seconds = time.monotonic() - before
        assert seconds <= BUDGETS["core_readiness_seconds"], "Core launch/readiness exceeded predeclared budget"
        return child, base, token, seconds
    except BaseException:
        launcher.stop(child)
        raise


def shim(candidate, work, mode):
    path = work / "fault_worker.py"
    marker = work / "worker-started.json"
    source = f'''import importlib.util,json,os,time
from pathlib import Path
transport=Path({str(candidate / "workers/transport/text_ndjson.py")!r})
spec=importlib.util.spec_from_file_location("candidate_transport",transport)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
original=module._run_route
marker=Path({str(marker)!r})
def injected(*args,**kwargs):
    if not marker.exists():
        temporary=marker.with_suffix(".tmp")
        temporary.write_text(json.dumps({{"pid":os.getpid(),"parent_pid":os.getppid(),"mode":{mode!r}}}),encoding="utf-8")
        temporary.replace(marker)
        if {mode!r}=="crash": os._exit(37)
        time.sleep({BUDGETS["fault_fixture_hang_seconds"]})
    return original(*args,**kwargs)
module._run_route=injected
raise SystemExit(module.main())
'''
    path.write_text(source, encoding="utf-8")
    return path, marker


def begin(client, base, token, payload, deadline):
    status, imported = client.call(base, "POST", "/api/v1/imports", token, client.import_request("fault.txt", payload))
    assert status == 202, imported
    job = "fault-" + uuid.uuid4().hex
    status, queued = client.call(base, "POST", "/api/v1/jobs", token,
                                 {"job_id": job, "kind": "text", "input_ref": imported["source_id"]})
    assert status == 202, queued
    status, executed = client.call(base, "POST", f"/api/v1/jobs/{job}/executions", token,
                                   {"deadline_ms": deadline}, extra_headers={"idempotency-key": job})
    assert status == 202, executed
    return job, executed["request_id"]


def settle(client, base, token, job, seconds):
    before = time.monotonic()
    while time.monotonic() - before <= seconds:
        status, body = client.call(base, "GET", f"/api/v1/jobs/{job}", token)
        assert status == 200, body
        if body.get("state") in TERMINAL:
            return body, time.monotonic() - before
        time.sleep(.05)
    raise TimeoutError(f"job did not settle within predeclared {seconds}s budget")


def case(candidate, root, mode, launcher, client, dev):
    work = root / mode
    work.mkdir()
    record = {"case": mode, "ok": False, "failure_class": "INJECTED_FIXTURE" if mode != "invalid_input" else "REAL_INVALID_BYTES"}
    child = None
    try:
        script, marker = shim(candidate, work, mode) if mode != "invalid_input" else (
            candidate / "workers/transport/text_ndjson.py", None)
        child, base, token, seconds = start(candidate, work, script, launcher)
        record.update(core_pid=child.pid, core_readiness_seconds=seconds,
                      fault_script=office.identity(script))
        payload = b"\xff\xfe\x00" if mode == "invalid_input" else b"Golden fault source"
        deadline = BUDGETS["timeout_deadline_ms"] if mode == "timeout" else BUDGETS["cancel_deadline_ms"]
        job, request = begin(client, base, token, payload, deadline)
        record["job_id"] = job
        if mode == "cancel":
            end = time.monotonic() + BUDGETS["worker_observation_seconds"]
            while not marker.is_file() and time.monotonic() < end:
                time.sleep(.02)
            assert marker.is_file(), "fault worker was not observed before cancellation"
            status, cancelled = client.call(base, "POST", f"/api/v1/jobs/{job}/executions/{request}/cancel", token, {})
            assert status == 202 and cancelled["cancel_requested"], cancelled
            record["cancel"] = cancelled
        final, seconds = settle(client, base, token, job, BUDGETS["fault_settlement_seconds"])
        record["fault_final"] = final
        record["fault_settlement_seconds"] = seconds
        expected = "cancelled" if mode == "cancel" else "failed"
        assert final["state"] == expected, final
        if mode == "timeout":
            assert "deadline exceeded" in str(final.get("error")), final
        if mode == "crash":
            assert "closed stdout" in str(final.get("error")), final
        if mode == "invalid_input":
            assert "invalid UTF-16" in str(final.get("error")), final
        for kind in ("text", "document_structure", "loss_report"):
            status, response = client.call(base, "GET", f"/api/v1/jobs/{job}/outputs/{kind}", token)
            assert status == 404, response
        record["no_outputs_published"] = True
        if marker is not None:
            observed = json.loads(marker.read_text(encoding="utf-8"))
            assert observed["parent_pid"] == child.pid
            record["owned_worker"] = observed
            end = time.monotonic() + 2
            while alive(observed["pid"]) and time.monotonic() < end:
                time.sleep(.05)
            assert not alive(observed["pid"]), "owned fault worker survived terminal state"
            record["fault_worker_exited"] = True
        recovery_started = time.monotonic()
        recovery, _ = begin(client, base, token, b"Golden recovery source", 30000)
        final, _ = settle(client, base, token, recovery, BUDGETS["recovery_job_seconds"])
        seconds = time.monotonic() - recovery_started
        assert seconds <= BUDGETS["recovery_job_seconds"], "Recovery import/queue/execution exceeded predeclared budget"
        assert final["state"] == "succeeded", final
        status, text = client.call(base, "GET", f"/api/v1/jobs/{recovery}/outputs/text", token)
        assert status == 200 and text["content"] == "Golden recovery source", text
        record["recovery"] = {"job_id": recovery, "state": final["state"], "seconds": seconds}
        record["ok"] = True
    except Exception as error:
        record["error"] = f"{type(error).__name__}: {error}"
    finally:
        if child is not None:
            try:
                dev.stop_owned_process(child)
                launcher.stop(child)
                record["core_stopped"] = child.poll() is not None
                record["cleanup_scope"] = "Only this probe's live Core PID and descendants"
            except Exception as error:
                record["ok"] = False
                record["cleanup_error"] = f"{type(error).__name__}: {error}"
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", required=True, type=Path)
    args = parser.parse_args()
    candidate = args.candidate.resolve()
    work = REPO / ".project-local/task-runtime/aaos01-fault" / uuid.uuid4().hex
    work.mkdir(parents=True)
    conditions = {"budgets": BUDGETS, "scope": "One real Core per fault case; API only, no UI startup P95 or whole-process memory claim",
                  "fault_modes": ["timeout", "cancel", "worker abrupt exit 37", "invalid UTF16 bytes"],
                  "candidate": str(candidate), "cache_condition": "OS caches unspecified; fresh data root per case"}
    (work / "conditions-before-run.json").write_text(json.dumps(conditions, indent=2), encoding="utf-8")
    launcher = office.load("fault_launcher", REPO / "scripts/release/backend_launcher.py")
    client = office.load("fault_client", REPO / "shared/core_client.py")
    dev = office.load("fault_dev", REPO / "scripts/runtime/dev.py")
    receipt = {"ok": False, "task": "Q13", "conditions": conditions,
               "evidence_level": "REAL_CORE_EXECUTION_WITH_INJECTED_WORKER_FAULTS",
               "candidate_manifest": office.identity(candidate / "backend-runtime-manifest.json"),
               "core": office.identity(candidate / "core/archeaxis-api.exe"),
               "transport": office.identity(candidate / "workers/transport/text_ndjson.py"), "results": []}
    dirty, patch_sha = dev.worktree_identity(REPO)
    receipt["source"] = {"commit": dev.git(REPO, "rev-parse", "HEAD"), "dirty": dirty, "patch_sha256": patch_sha}
    for mode in ("timeout", "cancel", "crash", "invalid_input"):
        receipt["results"].append(case(candidate, work, mode, launcher, client, dev))
    receipt["ok"] = all(record["ok"] for record in receipt["results"])
    path = work / "receipt.json"
    path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": receipt["ok"], "receipt": str(path), "results": receipt["results"]}))
    return 0 if receipt["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
