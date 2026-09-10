"""R10 live smoke: run the host adapter journey against the REAL Core process.

It spawns `archeaxis-api <db> 0` with a launch JSON on stdin (the Core's
launch-session model), reads the readiness line for its port, creates one accepted
fact, then runs `shared/core_client.run_journey` through the Core's HTTP API.

Exit 0 only when every step succeeded; the JSON receipt is printed for evidence.
No token is ever printed.
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


core = _load("core_client_smoke", REPO / "shared" / "core_client.py")

TOKEN = "c" * 64
SESSION = "d" * 32


def main() -> int:
    with __import__("contextlib").suppress(Exception):
        sys.stdout.reconfigure(encoding="utf-8")
    binary = REPO / ".project-local" / "build" / "cargo" / "debug" / "archeaxis-api.exe"
    if not binary.is_file():
        print(json.dumps({"ok": False, "blocked": "core binary not built", "path": str(binary)}))
        return 2

    run_root = REPO / ".project-local" / "runs" / "r10-smoke"
    run_root.mkdir(parents=True, exist_ok=True)
    db = run_root / f"smoke-{int(time.time())}.sqlite"
    child = subprocess.Popen(
        [str(binary), str(db), "0"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        encoding="utf-8",
    )
    try:
        child.stdin.write(json.dumps({"launch_token": TOKEN, "session_id": SESSION}) + "\n")
        child.stdin.flush()
        # The Core reads its launch claim to EOF, so stdin must be closed here or
        # it waits forever and never reports readiness.
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
        base = f"http://127.0.0.1:{port}"

        # One accepted fact so the journey's search has a current revision to cite.
        status, created = core.call(
            base,
            "POST",
            "/api/v1/knowledge-items",
            TOKEN,
            {"knowledge_type": "FACTUAL_CLAIM", "body": "smoke radius 6371 km", "status": "accepted", "created_by": "owner"},
        )
        knowledge_id = created.get("knowledge_id") if isinstance(created, dict) else None

        result = core.run_journey(
            core.call,
            base,
            TOKEN,
            "smoke.md",
            b"radius 6371 km",
            "6371",
            "card-smoke",
            "evt-smoke",
        )
        result["core_port"] = port
        result["knowledge_created_status"] = status
        result["knowledge_id"] = knowledge_id
        print(json.dumps(result, ensure_ascii=False))
        return 0 if result.get("ok") else 1
    finally:
        child.kill()
        child.wait()


if __name__ == "__main__":
    raise SystemExit(main())
