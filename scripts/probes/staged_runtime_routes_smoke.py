"""End-to-end: a staged profile's declared routes let a real Core convert non-text.

Rounds 3 and 4 added two halves that were tested separately:

* the Core registers a capability route when the launch declares one;
* `load_profile` reads a `routes` list from a staged `worker-profile.json` and
  `start()` forwards it.

This probe joins them against one real staged tree, because two green halves can still
fail to meet. It builds a runtime root in the project-local ignored area, writes a
profile whose routes are derived by the stager's own `present_routes`, starts the Core
through the launcher's own `start()`, and runs a canvas job over HTTP.

Nothing here is a fixture of the *product*: the Core is the built binary, the worker is
the real `worker_canvas.py`, the input is the repository's verified golden canvas
fixture, and the profile is read by the shipped reader. The staged tree itself is
minimal (Core + workers + profile) because the full stager refuses linked donors, which
is a packaging detail this probe is not testing.
"""

from __future__ import annotations

import base64
import contextlib
import importlib.util
import json
import shutil
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
LAUNCHER = REPO / "scripts" / "release" / "backend_launcher.py"
STAGER = REPO / "scripts" / "release" / "stage_backend_runtime.py"
FIXTURE = REPO / "tests" / "fixtures" / "golden" / "learning-evidence.canvas"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


launcher = _load("launcher_staged", LAUNCHER)
stager = _load("stager_staged", STAGER)
core_client = _load("core_client_staged", REPO / "shared" / "core_client.py")


def build_staged_tree(root: Path, core_binary: Path) -> Path:
    """A minimal runtime root: core/, workers/, runtime/, worker-profile.json."""
    (root / "core").mkdir(parents=True, exist_ok=True)
    shutil.copy2(core_binary, root / "core" / "archeaxis-api.exe")
    (root / "runtime").mkdir(parents=True, exist_ok=True)
    interpreter = Path(sys.executable)
    (root / "runtime" / interpreter.name).write_bytes(b"")
    shutil.copy2(interpreter, root / "runtime" / interpreter.name)
    shutil.copytree(REPO / "services" / "python-workers", root / "workers")
    (root / "data").mkdir(parents=True, exist_ok=True)
    profile = {
        "schema": stager.PROFILE_SCHEMA,
        "python": f"runtime/{interpreter.name}",
        "script": stager.TEXT_WORKER_RELATIVE,
        "staging": "data/worker-staging",
        "routes": stager.present_routes(root),
    }
    (root / "worker-profile.json").write_text(
        json.dumps(profile, indent=2) + "\n", encoding="utf-8", newline="\n")
    return root / "worker-profile.json"


def main() -> int:
    with contextlib.suppress(Exception):
        sys.stdout.reconfigure(encoding="utf-8")
    core_binary = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    if core_binary is None or not core_binary.is_file():
        print(json.dumps({"ok": False, "blocked": "pass the built Core binary as argv[1]"}))
        return 2
    if not FIXTURE.is_file():
        print(json.dumps({"ok": False, "blocked": "golden canvas fixture missing"}))
        return 2

    root = REPO / ".project-local" / "runs" / "staged-routes"
    if root.exists():
        shutil.rmtree(root, ignore_errors=True)
    profile_path = build_staged_tree(root, core_binary)

    receipt: dict = {
        "ok": False,
        "staged_root": str(root),
        "core_binary": str(core_binary),
        "evidence_level": "REAL_STAGED_RUNTIME",
    }
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    receipt["declared_routes"] = profile.get("routes", [])

    # Resolve through the shipped reader, exactly as the runtime does.
    resolved = launcher.load_profile(root)
    receipt["resolved_routes"] = [
        {"capability": r["capability"], "script": str(r["script"])} for r in resolved["routes"]
    ]

    # `start()` reads ROOT for the Core path, so point it at the staged tree.
    launcher.ROOT = root
    child, base, start_receipt, tokens = launcher.start(root / "data", 0)
    try:
        status, version = core_client.call(base, "GET", "/api/v1/system/version",
                                           launcher.credential(tokens, "human")["x-archeaxis-launch-token"])
        receipt["system_version_status"] = status
        payload = FIXTURE.read_bytes()
        status, imported = core_client.call(
            base, "POST", "/api/v1/imports",
            launcher.credential(tokens, "human")["x-archeaxis-launch-token"],
            core_client.import_request("learning-evidence.canvas", payload))
        source_id = imported.get("source_id") if isinstance(imported, dict) else None
        receipt["import"] = {"status": status, "source_id": source_id}
        if not source_id:
            receipt["blocked"] = "import refused"
            print(json.dumps(receipt, ensure_ascii=False, indent=2))
            return 1

        job_id = "staged-canvas"
        token = launcher.credential(tokens, "human")["x-archeaxis-launch-token"]
        core_client.call(base, "POST", "/api/v1/jobs", token,
                         {"job_id": job_id, "kind": "canvas", "input_ref": source_id})
        core_client.call(base, "POST", f"/api/v1/jobs/{job_id}/executions", token,
                         {"deadline_ms": 120000}, extra_headers={"idempotency-key": job_id})
        state = None
        for _ in range(120):
            _, final = core_client.call(base, "GET", f"/api/v1/jobs/{job_id}", token)
            state = final.get("state") if isinstance(final, dict) else None
            if state in ("succeeded", "failed", "cancelled"):
                break
            time.sleep(0.25)
        receipt["job_state"] = state
        if isinstance(final, dict) and final.get("error"):
            receipt["error"] = final["error"]
    finally:
        launcher.stop(child)

    receipt["ok"] = receipt.get("job_state") == "succeeded"
    out = root / "staged-routes-receipt.json"
    out.write_text(json.dumps(receipt, ensure_ascii=False, indent=2, default=str) + "\n",
                   encoding="utf-8")
    print(json.dumps(receipt, ensure_ascii=False, indent=2, default=str))
    print(f"\nreceipt: {out}")
    return 0 if receipt["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
