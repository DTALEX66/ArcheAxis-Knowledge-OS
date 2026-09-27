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
import re
import secrets
import socket
import stat
import subprocess
import threading
import time
import urllib.error
import urllib.request
from contextlib import suppress
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PROFILE_NAME = "worker-profile.json"
PROFILE_SCHEMA = "archeaxis.worker-profile/v1"
CORE_RELATIVE = Path("core") / "archeaxis-api.exe"
LAUNCH_PROTOCOL = "archeaxis.desktop-launch/v2"
READY_MARKER = "127.0.0.1:"
STARTUP_TIMEOUT_SECONDS = 30.0
PRIVATE_NAMES = set([".git", ".codex", ".dsh", ".zcode", ".hermes", ".openhuman", ".claude", ".agents", ".agent", ".cursor", ".continue", ".aider", ".gemini", ".opencode", ".openhands", ".cline", ".roo", ".kilocode", ".windsurf", ".copilot", ".ssh", ".aws", ".azure", ".gnupg", "agent-private", "private-agent-state", "sessions", "memories", "keychain", "credentials", "auth", "browser-data", ".npmrc", ".pypirc", ".netrc"])


class LaunchFailure(Exception):  # noqa: N818 - retained public exception contract
    """A named startup failure; the message says which component failed."""


def safe_path(root: Path, value: str) -> Path:
    spelling = value.replace("\\", "/")
    if not value.strip() or spelling.lower().startswith("e:") or spelling.startswith("//") or ".." in spelling.split("/"):
        raise LaunchFailure("unsafe worker profile path")
    path = Path(os.path.abspath(root / value))
    full = str(path).replace("\\", "/").lower()
    if full.startswith(("e:", "//")) or any(part in PRIVATE_NAMES or part.startswith(".env") for part in full.split("/")) or "/.project-local/agents/" in full:
        raise LaunchFailure("protected worker profile path")
    for part in (*reversed(path.parents), path):
        try:
            info = part.lstat()
        except (FileNotFoundError, NotADirectoryError):
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise LaunchFailure("linked worker profile path")
    return path


def load_profile(root: Path, explicit_path: str | None = None) -> dict:
    path = safe_path(root, explicit_path if explicit_path is not None else PROFILE_NAME)
    if not path.is_file():
        raise LaunchFailure(f"worker profile is missing: {path}")
    try:
        if path.stat().st_size > 16384:
            raise LaunchFailure("worker profile exceeds limit")

        def unique(pairs):
            document = {}
            for key, value in pairs:
                if key in document:
                    raise LaunchFailure("duplicate worker profile field")
                document[key] = value
            return document

        document = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique)
    except (json.JSONDecodeError, UnicodeError, OSError) as error:
        raise LaunchFailure("worker profile is not valid readable JSON") from error
    if not isinstance(document, dict) or set(document) != {"schema", "python", "script", "staging"}:
        raise LaunchFailure("unsupported or incomplete worker profile fields")
    if document.get("schema") != PROFILE_SCHEMA:
        raise LaunchFailure(
            f"worker profile schema is not {PROFILE_SCHEMA}: {document.get('schema')!r}")
    resolved = {}
    for key in ("python", "script", "staging"):
        value = document.get(key)
        if not isinstance(value, str) or not value.strip():
            raise LaunchFailure(f"worker profile has no {key}: {path}")
        resolved[key] = safe_path(path.parent, value)
    require_file(resolved["python"], "worker interpreter")
    require_file(resolved["script"], "worker script")
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
    environment.pop("ARCHAXIS_PYTHON", None)
    environment.pop("PYTHONPATH", None)
    environment.pop("PYTHONHOME", None)
    environment["PYTHONNOUSERSITE"] = "1"
    environment["ARCHEAXIS_BACKEND_ROOT"] = str(root)
    environment["ARCHEAXIS_WORKER_PROFILE"] = str(root / PROFILE_NAME)
    environment["ARCHAXIS_WORKER_PROFILE"] = str(root / PROFILE_NAME)
    scheduler = str(root / "workers" / "learning" / "worker_schedule.py")
    environment["ARCHEAXIS_SCHEDULER_WORKER"] = scheduler
    environment["ARCHAXIS_SCHEDULER_WORKER"] = scheduler
    environment["ARCHEAXIS_CORE_BIN"] = str(root / CORE_RELATIVE)
    environment["ARCHAXIS_CORE_BIN"] = str(root / CORE_RELATIVE)
    return environment


def start(data_root: Path, port: int) -> tuple[subprocess.Popen, str, dict, dict]:
    core = require_file(safe_path(ROOT, str(CORE_RELATIVE)), "Core executable")
    profile = load_profile(ROOT)
    require_file(profile["python"], "scheduler interpreter (from worker profile)")
    require_file(profile["script"], "text worker script (from worker profile)")

    data_root = safe_path(ROOT, str(data_root))
    staging = safe_path(data_root, "worker-staging")
    workspace = safe_path(data_root, "workspace.sqlite")
    data_root.mkdir(parents=True, exist_ok=True)
    staging.mkdir(parents=True, exist_ok=True)

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
    try:
        assert child.stdin is not None
        child.stdin.write(json.dumps(launch) + "\n")
        child.stdin.flush()
        child.stdin.close()
        base = wait_for_readiness(child, port, STARTUP_TIMEOUT_SECONDS)
        receipt = {"core": str(core), "workspace": str(workspace), "port": port,
                   "text_worker": launch["text_worker"]}
        tokens = {"x-archeaxis-launch-token": launch["launch_token"],
                  "x-archeaxis-machine-token": launch["machine_token"]}
        return child, base, receipt, tokens
    except BaseException:
        stop(child)
        raise


def wait_for_readiness(child: subprocess.Popen, port: int, timeout: float) -> str:
    """Drain both pipes for the child's lifetime; return only a validated URL.

    Port zero accepts the OS-selected loopback port. On failure the owned child
    is terminated and reaped. The caller owns stop(child) after successful use.
    """
    ready = threading.Event()
    readiness = []
    stream_failed = threading.Event()

    def drain(stream, capture=False):
        # Bounded buffer, including a child that never emits a newline. Never echo
        # child output: it may contain the private stdin handshake.
        line = ""
        try:
            while character := stream.read(1):
                if character == "\n":
                    if capture and not readiness and READY_MARKER in line:
                        readiness.append(line)
                        ready.set()
                    line = ""
                elif capture:
                    line = (line + character)[-4096:]
        except (OSError, UnicodeError):
            stream_failed.set()
            ready.set()
        finally:
            with suppress(OSError):
                stream.close()

    readers = [threading.Thread(target=drain, args=(child.stdout, True), daemon=True),
               threading.Thread(target=drain, args=(child.stderr,), daemon=True)]
    child._archeaxis_readers = readers
    for reader in readers:
        reader.start()
    try:
        deadline = time.monotonic() + timeout
        while not ready.wait(min(0.05, max(0, deadline - time.monotonic()))):
            if child.poll() is not None:
                raise LaunchFailure(f"Core exited before becoming ready (exit {child.returncode})")
            if time.monotonic() >= deadline:
                raise LaunchFailure(f"Core did not report readiness within {timeout:g}s")
        # Accept only this launch's loopback endpoint; arbitrary output never enters
        # the public receipt, even when a compromised child echoes its handshake.
        if stream_failed.is_set():
            raise LaunchFailure("Core output stream failed")
        match = re.fullmatch(r"archeaxis-api ready on http://127\.0\.0\.1:([0-9]{1,5})", readiness[0].strip())
        if match is None or not 1 <= int(match[1]) <= 65535 or (port and int(match[1]) != port):
            raise LaunchFailure("Core reported invalid readiness endpoint")
        return f"http://127.0.0.1:{int(match[1])}"
    except BaseException:
        stop(child)
        raise


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
    try:
        if child.poll() is None:
            child.terminate()
            try:
                child.wait(timeout=15)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait(timeout=15)
        return child.returncode or 0
    finally:
        for reader in getattr(child, "_archeaxis_readers", []):
            reader.join(timeout=1)
        for stream in (child.stdin, child.stdout, child.stderr):
            if stream is not None and not stream.closed:
                with suppress(OSError):
                    stream.close()


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
        child, base, receipt, tokens = start(safe_path(ROOT, str(args.data_root)), port)
    except (LaunchFailure, OSError) as error:
        print(json.dumps({"ok": False, "failure": str(error)}, ensure_ascii=False, indent=2))
        return 2

    receipt["base_url"] = base
    if args.smoke:
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
    try:
        print(json.dumps(receipt, ensure_ascii=False, indent=2), flush=True)
        return child.wait()
    except KeyboardInterrupt:
        return 130
    finally:
        stop(child)


if __name__ == "__main__":
    raise SystemExit(main())
