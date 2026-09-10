"""R10 host panel smoke: a real Core, a real panel server, real HTTP reads.

Launches the real `archeaxis-api` (see `scripts/probes/r10_core_journey_smoke.py` for
the launch-claim details), drives one real journey through `shared/core_client.py` so
the item has genuine learner history, then serves `scripts/host/journey_panel.py` and
fetches the page and both JSON endpoints over HTTP.

The receipt proves the host-facing surface, not the DeepTutor screen: DeepTutor is an
immutable external dependency and this repository never patches it.
"""

from __future__ import annotations

import contextlib
import importlib.util
import json
import os
import secrets
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CORE_BINARY = REPO / ".project-local" / "build" / "cargo" / "debug" / "archeaxis-api.exe"


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


core_client = load("core_client_smoke", REPO / "shared" / "core_client.py")
panel = load("journey_panel_smoke", REPO / "scripts" / "host" / "journey_panel.py")


def free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def wait_ready(process: subprocess.Popen, seconds: float = 25.0) -> int | None:
    deadline = time.time() + seconds
    while time.time() < deadline:
        line = process.stdout.readline()
        if not line:
            if process.poll() is not None:
                return None
            continue
        if "127.0.0.1:" in line:
            return int(line.split("127.0.0.1:", 1)[1].split()[0].strip())
    return None


def get(url: str) -> tuple[int, object]:
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            return response.status, response.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode("utf-8", "replace")
    except (urllib.error.URLError, OSError) as error:
        return 0, str(error)


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        with contextlib.suppress(Exception):
            stream.reconfigure(encoding="utf-8")
    workdir = REPO / ".project-local" / "runs" / "host-panel-smoke"
    workdir.mkdir(parents=True, exist_ok=True)
    db = workdir / "core.sqlite"
    core_port = free_port()
    panel_port = free_port()
    receipt: dict = {"core_binary": str(CORE_BINARY), "db": str(db)}

    if not CORE_BINARY.is_file():
        print(json.dumps({**receipt, "ok": False, "reason": "core binary is not built"}, ensure_ascii=False))
        return 2

    claim = {"launch_token": secrets.token_hex(32), "session_id": secrets.token_hex(16)}
    core = subprocess.Popen(
        [str(CORE_BINARY), str(db), str(core_port)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
    )
    core.stdin.write(json.dumps(claim) + "\n")
    core.stdin.flush()
    core.stdin.close()

    httpd = None
    try:
        ready = wait_ready(core)
        receipt["core_ready_port"] = ready
        if ready is None:
            receipt.update({"ok": False, "reason": "the Core did not report readiness"})
            print(json.dumps(receipt, ensure_ascii=False))
            return 3
        base = f"http://127.0.0.1:{ready}"
        token = claim["launch_token"]

        # a real journey so the item has genuine learner history to project
        item_key = "card-host-panel"
        journey = core_client.run_journey(
            core_client.call,
            base,
            token,
            "host-panel-sample.md",
            "Panels in a host UI read the Core; nothing is written anywhere else.\n".encode("utf-8"),
            "host UI",
            item_key,
            "host-panel-event-1",
        )
        receipt["journey"] = {k: journey.get(k) for k in ("ok", "failed_step", "steps")}

        os.environ["ARCHEAXIS_LAUNCH_TOKEN"] = token
        httpd = panel.serve(base, item_key, panel_port, "ARCHEAXIS_LAUNCH_TOKEN")
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        panel_url = f"http://127.0.0.1:{panel_port}"
        receipt["panel_url"] = panel_url

        page_status, page = get(panel_url + "/")
        receipt["page_status"] = page_status
        receipt["page_has_both_panels"] = ("学习者记录（人类）" in page) and ("机器能力收据（AI）" in page)

        health_status, health = get(panel_url + "/api/health")
        receipt["health_status"] = health_status
        receipt["health"] = json.loads(health) if isinstance(health, str) and health.startswith("{") else health

        state_status, state_raw = get(panel_url + "/api/state?item_key=" + item_key)
        state = json.loads(state_raw)
        receipt["state_status"] = state_status
        receipt["learner"] = state.get("learner")
        receipt["machine"] = state.get("machine")
        receipt["note"] = state.get("note")

        # the honest negative: an unreachable Core must not render zeros
        off_status, off_raw = panel.build_state(f"http://127.0.0.1:{free_port()}", item_key, token)
        off = off_raw
        receipt["unreachable"] = {
            "http_status": off_status,
            "core": off["core"],
            "learner": off["learner"],
            "machine": off["machine"],
        }

        ok = (
            page_status == 200
            and receipt["page_has_both_panels"]
            and health_status == 200
            and receipt["health"].get("reachable") is True
            and state_status == 200
            and isinstance(receipt["learner"], dict)
            and receipt["learner"].get("event_count", 0) >= 1
            and receipt["machine"].get("status") == "not_recorded"
            and off_status == 503
            and receipt["unreachable"]["learner"] is None
        )
        receipt["ok"] = bool(ok)
        print(json.dumps(receipt, ensure_ascii=False, indent=2))
        return 0 if ok else 4
    finally:
        if httpd is not None:
            httpd.shutdown()
            httpd.server_close()
        core.kill()
        core.wait()


if __name__ == "__main__":
    raise SystemExit(main())
