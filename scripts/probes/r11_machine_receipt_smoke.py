"""R11 live smoke: a REAL Core process, launched with a machine claim, records a
machine task receipt and reads it back.

The receipt carries the task conditions, the knowledge/method/tool/model versions,
the scope and the outcome, so the evidence chain is a real process request rather
than a fixture. The launch claim is `actor: machine`, which is also what the Core's
middleware uses to decide the actor - a client header cannot change it.

Exit 0 only when the receipt round-trips; prints a JSON summary (never a token).
"""

from __future__ import annotations

import contextlib
import importlib.util
import json
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


core = _load("core_client_r11", REPO / "shared" / "core_client.py")

TOKEN = "e" * 64
SESSION = "f" * 32
TASK_ID = "r11-smoke-task"


def main() -> int:
    with contextlib.suppress(Exception):
        sys.stdout.reconfigure(encoding="utf-8")
    binary = REPO / ".project-local" / "build" / "cargo" / "debug" / "archeaxis-api.exe"
    if not binary.is_file():
        print(json.dumps({"ok": False, "blocked": "core binary not built", "path": str(binary)}))
        return 2

    runtime = _load("runtime_r11_smoke", REPO / "scripts/runtime/dev.py")
    db = runtime.artifact_directory(REPO, "r11-smoke") / "core.sqlite"
    child = subprocess.Popen(
        [str(binary), str(db), "0"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        encoding="utf-8",
    )
    try:
        # `actor: machine` is the launch-session claim; the Core maps it to the
        # machine principal for every request of this session.
        child.stdin.write(json.dumps({"launch_token": TOKEN, "session_id": SESSION, "actor": "machine"}) + "\n")
        child.stdin.flush()
        child.stdin.close()  # the Core reads the claim to EOF

        line = ""
        deadline = time.time() + 15
        while time.time() < deadline:
            line = child.stdout.readline()
            if "127.0.0.1:" in line:
                break
        if "127.0.0.1:" not in line:
            print(json.dumps({"ok": False, "blocked": "core did not report readiness", "line": line[:80]}))
            return 3
        port = line.split("127.0.0.1:", 1)[1].split()[0].strip()
        base = f"http://127.0.0.1:{port}"

        receipt = {
            "task_id": TASK_ID,
            "conditions": "offline core; synthetic markdown sample",
            "model_version": "qwen3:8b",
            "scope": "run the adapter journey and report whether it completed",
            "outcome": "succeeded",
            "knowledge_version": "k_8f390d95872e39a2e2bb110b@1",
            "method_version": "core-client-journey/v1",
            "tool_version": "archeaxis-api",
        }
        write_status, write_body = core.call(base, "POST", "/api/v1/machine/tasks", TOKEN, receipt)
        read_status, readback = core.call(base, "GET", f"/api/v1/machine/tasks/{TASK_ID}", TOKEN)

        ok = write_status == 201 and read_status == 200 and isinstance(readback, dict) and readback.get("outcome") == "succeeded"
        print(json.dumps({
            "ok": ok,
            "core_port": port,
            "write_status": write_status,
            "write_body": write_body,
            "read_status": read_status,
            "readback": readback,
        }, ensure_ascii=False))
        return 0 if ok else 1
    finally:
        child.kill()
        child.wait()


if __name__ == "__main__":
    raise SystemExit(main())
