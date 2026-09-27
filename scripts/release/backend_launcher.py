"""Start the staged backend runtime from its own root.

This is the formal entry point of a staged runtime. It resolves every component from
the runtime root it lives in - never from a checkout, a project virtualenv, an
editable install or an inherited `PYTHONPATH` - and it never asks the operator to
resolve an interpreter: the scheduler interpreter comes from `worker-profile.json`,
which is what the Core reads.

    runtime/python.exe start-backend.py --data-root <dir> [--port N] [--smoke]

`--smoke` performs the first exchange, reports health, and shuts the Core down.

Every failure names the component that failed. There is no fallback that reports
success: a missing interpreter, worker or Core, a bad profile, a port conflict and an
early exit are all distinguishable, and none of them is silently downgraded.
"""

from __future__ import annotations

import argparse
import json
import os
import secrets
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PROFILE_NAME = "worker-profile.json"
PROFILE_SCHEMA = "archeaxis.worker-profile/v1"
CORE_RELATIVE = Path("core") / "archeaxis-api.exe"
LAUNCH_PROTOCOL = "archeaxis.desktop-launch/v2"
READY_MARKER = "127.0.0.1:"
STARTUP_TIMEOUT_SECONDS = 30.0


class LaunchFailure(Exception):
    """A named startup failure; the message says which component failed."""


def load_profile(root: Path) -> dict:
    path = root / PROFILE_NAME
    if not path.is_file():
        raise LaunchFailure(f"worker profile is missing: {path}")
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise LaunchFailure(f"worker profile is not valid JSON: {path}: {error}") from error
    if document.get("schema") != PROFILE_SCHEMA:
        raise LaunchFailure(
            f"worker profile schema is not {PROFILE_SCHEMA}: {document.get('schema')!r}")
    resolved = {}
    for key in ("python", "script", "staging"):
        value = document.get(key)
        if not isinstance(value, str) or not value.strip():
            raise LaunchFailure(f"worker profile has no {key}: {path}")
        candidate = Path(value)
        resolved[key] = candidate if candidate.is_absolute() else root / candidate
    return resolved


def require_file(path: Path, what: str) -> Path:
    if not path.is_file():
        raise LaunchFailure(f"{what} is missing: {path}")
    return path


def free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


def build_environment(root: Path) -> dict:
    """Only runtime locations are exported. The interpreter is not among them.

    `ARCHEAXIS_PYTHON` is deliberately *not* set: the Core resolves the scheduler
    interpreter from the profile, which is the whole point of the profile existing.
    An inherited value is removed so a developer shell cannot mask a broken runtime.
    """
    environment = dict(os.environ)
    environment.pop("ARCHEAXIS_PYTHON", None)
    environment["ARCHEAXIS_BACKEND_ROOT"] = str(root)
    environment["ARCHEAXIS_WORKER_PROFILE"] = str(root / PROFILE_NAME)
    environment["ARCHAXIS_WORKER_PROFILE"] = str(root / PROFILE_NAME)
    scheduler = str(root / "workers" / "learning" / "worker_schedule.py")
    environment["ARCHEAXIS_SCHEDULER_WORKER"] = scheduler
    environment["ARCHAXIS_SCHEDULER_WORKER"] = scheduler
    environment["ARCHEAXIS_CORE_BIN"] = str(root / CORE_RELATIVE)
    environment["ARCHAXIS_CORE_BIN"] = str(root / CORE_RELATIVE)
    return environment


def start(data_root: Path, port: int) -> tuple[subprocess.Popen, str, dict]:
    core = require_file(ROOT / CORE_RELATIVE, "Core executable")
    profile = load_profile(ROOT)
    require_file(profile["python"], "scheduler interpreter (from worker profile)")
    require_file(profile["script"], "text worker script (from worker profile)")

    data_root.mkdir(parents=True, exist_ok=True)
    staging = data_root / "worker-staging"
    staging.mkdir(parents=True, exist_ok=True)
    workspace = data_root / "workspace.sqlite"

    launch = {
        "launch_token": secrets.token_hex(32),
        "session_id": secrets.token_hex(16),
        "actor": "human",
        "protocol": LAUNCH_PROTOCOL,
        "machine_token": secrets.token_hex(32),
        "text_worker": {
            "python": str(profile["python"]),
            "script": str(profile["script"]),
            "staging": str(staging),
        },
    }
    child = subprocess.Popen(
        [str(core), str(workspace), str(port)],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, encoding="utf-8", cwd=str(ROOT),
        env=build_environment(ROOT),
    )
    assert child.stdin is not None and child.stdout is not None
    child.stdin.write(json.dumps(launch) + "\n")
    child.stdin.flush()
    child.stdin.close()

    deadline = time.time() + STARTUP_TIMEOUT_SECONDS
    line = ""
    while time.time() < deadline:
        if child.poll() is not None:
            stderr = (child.stderr.read() if child.stderr else "") or ""
            raise LaunchFailure(
                f"Core exited before becoming ready (exit {child.returncode}): "
                f"{stderr.strip()[:400] or 'no stderr'}")
        line = child.stdout.readline()
        if READY_MARKER in line:
            break
        if not line and child.poll() is not None:
            stderr = (child.stderr.read() if child.stderr else "") or ""
            raise LaunchFailure(
                f"Core exited before becoming ready (exit {child.returncode}): "
                f"{stderr.strip()[:400] or 'no stderr'}")
    if READY_MARKER not in line:
        child.kill()
        raise LaunchFailure(f"Core did not report readiness within "
                            f"{STARTUP_TIMEOUT_SECONDS:.0f}s (last output: {line.strip()[:200]!r})")
    # The readiness line already carries the full authority; rebuilding it from the
    # port alone produced `http://50595`, which is not a URL.
    authority = line.split(READY_MARKER, 1)[1].split()[0].strip()
    base = f"http://{READY_MARKER}{authority}"
    receipt = {"core": str(core), "workspace": str(workspace), "port": port,
               "ready_line": line.strip(), "text_worker": launch["text_worker"],
               "session_id": launch["session_id"],
               "launch_token": launch["launch_token"],
               "machine_token": launch["machine_token"]}
    return child, base, receipt


def call(base: str, method: str, path: str, body: dict | None = None,
         tokens: dict | None = None) -> tuple[int, object]:
    """Every route is authenticated per request by the launch layer.

    The Core matches `x-archeaxis-launch-token` against the token it accepted on
    stdin and answers `AAK-AUTH-001` otherwise, so a caller that forgets it sees a
    bare 401 rather than a startup problem.
    """
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request = urllib.request.Request(base + path, data=data, method=method)
    if data is not None:
        request.add_header("content-type", "application/json")
    for name, value in (tokens or {}).items():
        request.add_header(name, value)
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            payload = response.read().decode("utf-8")
            return response.status, json.loads(payload) if payload else {}
    except urllib.error.HTTPError as error:
        payload = error.read().decode("utf-8")
        try:
            return error.code, json.loads(payload)
        except json.JSONDecodeError:
            return error.code, payload


def stop(child: subprocess.Popen) -> int:
    if child.poll() is None:
        child.terminate()
        try:
            return child.wait(timeout=15)
        except subprocess.TimeoutExpired:
            child.kill()
            return child.wait(timeout=15)
    return child.returncode or 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, default=ROOT / "data")
    parser.add_argument("--port", type=int, default=0,
                        help="0 (default) lets the OS choose a free port")
    parser.add_argument("--smoke", action="store_true",
                        help="after readiness, call the first exchange and shut down")
    args = parser.parse_args()

    port = args.port or free_port()
    try:
        child, base, receipt = start(args.data_root.resolve(), port)
    except LaunchFailure as error:
        print(json.dumps({"ok": False, "failure": str(error)}, ensure_ascii=False, indent=2))
        return 2

    receipt["base_url"] = base
    if args.smoke:
        tokens = {"x-archeaxis-launch-token": receipt.pop("launch_token"),
                  "x-archeaxis-machine-token": receipt.pop("machine_token")}
        receipt.pop("session_id", None)
        try:
            status, version = call(base, "GET", "/api/v1/system/version", tokens=tokens)
            receipt["system_version"] = {"status": status, "body": version}
            status, info = call(base, "GET", "/api/v1/workspaces/info", tokens=tokens)
            receipt["workspaces_info"] = {"status": status, "body": info}
        finally:
            receipt["exit_code"] = stop(child)
        receipt["ok"] = (
            isinstance(receipt.get("system_version"), dict)
            and receipt["system_version"]["status"] == 200
            and isinstance(receipt.get("workspaces_info"), dict)
            and receipt["workspaces_info"]["status"] == 200
        )
        receipt["shutdown"] = "terminated"
        print(json.dumps(receipt, ensure_ascii=False, indent=2))
        return 0 if receipt["ok"] else 1

    receipt["ok"] = True
    print(json.dumps(receipt, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
