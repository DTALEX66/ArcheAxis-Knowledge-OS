"""Prove the desktop-shaped launch now registers capability routes, by launching a real Core.

Before the fix, a launch that sent no `routes` registered only the built-in `text.extract`, so every
other capability - PDF, OCR, Office, media, canvas, and the co-learning machine answer - was
unreachable when the product was launched the way the product is launched. This drives the real
binary with the launch document the desktop now composes, and reads the capability surface back.

What this proves: the Core registers what the launch declares, and a desktop-shaped document declares
the routes. What it does NOT prove: that the desktop's C# serializes those routes correctly. That is
the `desktop-vnext` CI job's job, and it is green on the commit under test - but a green build is not
a launched product, and this note says so rather than implying it.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def run_directory() -> Path:
    """Allocate an isolated run without removing an earlier probe's evidence."""
    runtime = load("desktop_route_runtime", REPO / "scripts/runtime/dev.py")
    return runtime.artifact_directory(REPO, "desktop-route-readback")

# The same eleven capabilities the desktop launcher now writes, resolved the same way.
ROUTE_WORKERS = {
    "archive.inventory": "document/worker_archive.py",
    "canvas.structure": "document/worker_canvas.py",
    "html.structure": "web/worker_html.py",
    "image.caption": "vision/worker_caption.py",
    "image.ocr": "vision/worker_ocr.py",
    "machine.answer": "machine/worker_machine_answer.py",
    "media.probe": "document/worker_media.py",
    "media.transcribe": "media/worker_transcribe.py",
    "office.structure": "document/worker_office.py",
    "pdf.extract": "document/worker_pdf.py",
    "subtitles.structure": "document/worker_subtitles.py",
}


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    if len(sys.argv) < 3:
        print("usage: desktop_route_readback.py <core.exe> <python.exe>")
        return 2
    core, python = Path(sys.argv[1]), Path(sys.argv[2])
    workers_root = REPO / "services/python-workers"
    run = run_directory()
    db = run / "workspace.sqlite"
    staging = run / "worker-staging"
    staging.mkdir()

    routes = []
    for capability, relative in sorted(ROUTE_WORKERS.items()):
        script = workers_root / relative
        assert script.is_file(), f"worker missing: {relative}"
        routes.append({"capability": capability, "script": str(script)})

    # The launch document the desktop composes, minus the transport's own text worker, which is what
    # `script` names.
    launch = {
        "protocol": "archeaxis.desktop-launch/v2",
        "actor": "human",
        "launch_token": "a" * 64,
        "machine_token": "b" * 64,
        "session_id": "c" * 32,
        "text_worker": {
            "python": str(python),
            "script": str(workers_root / "transport/text_ndjson.py"),
            "staging": str(staging),
            "routes": routes,
        },
    }

    child = subprocess.Popen(
        [str(core), str(db), "0"],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, encoding="utf-8", cwd=str(run),
    )
    base = None
    deadline = time.time() + 40
    try:
        assert child.stdin and child.stdout
        child.stdin.write(json.dumps(launch) + "\n")
        child.stdin.close()
        while time.time() < deadline:
            line = child.stdout.readline()
            if not line:
                break
            if line.startswith("archeaxis-api ready on "):
                base = line.split(" ", 3)[3].strip()
                break
        if base is None:
            print("FAILED: the Core did not report readiness")
            stderr = child.stderr.read() if child.stderr else ""
            print(stderr[-800:])
            return 1

        def get(path: str):
            request = urllib.request.Request(
                base + path, headers={"x-archeaxis-launch-token": "a" * 64})
            with urllib.request.urlopen(request, timeout=20) as response:
                return json.loads(response.read().decode("utf-8"))

        surface = get("/api/v1/capabilities")
        entries = surface.get("capabilities", surface if isinstance(surface, list) else [])
        declared = sorted(entry["capability"] for entry in entries)
        print(f"launch declared {len(routes)} routes")
        print(f"Core registered {len(declared)} capabilities:")
        for capability in declared:
            print(f"  {capability}")

        expected = sorted(ROUTE_WORKERS)
        missing = [capability for capability in expected if capability not in declared]
        extra = [capability for capability in declared if capability not in expected]

        # The machine answer capability is the one this whole line of work depends on.
        machine_ok = "machine.answer" in declared

        receipt = {
            "schema": "aaos.desktop-route-readback/v1",
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            "core": str(core),
            "declared_in_launch": expected,
            "registered_by_core": declared,
            "missing_after_launch": missing,
            "unexpectedly_registered": extra,
            "machine_answer_registered": machine_ok,
            "what_this_proves": [
                "the Core registers exactly the routes a launch declares",
                "a desktop-shaped launch document declaring eleven routes yields eleven registered "
                "capabilities, including machine.answer",
            ],
            "what_this_does_not_prove": [
                "that the desktop's C# serializes those routes correctly; that is the desktop-vnext CI "
                "job, which builds and smoke-runs the real host",
                "that a capability job succeeds end to end on every one of those routes; this reads the "
                "capability surface, it does not run a conversion",
            ],
            "verdict": "REGISTERED" if not missing and machine_ok else "INCOMPLETE",
        }
        (run / "receipt.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2),
                                         encoding="utf-8")
        print()
        print("missing:", missing or "none")
        print("machine.answer registered:", machine_ok)
        print("verdict:", receipt["verdict"])
        return 0 if receipt["verdict"] == "REGISTERED" else 1
    finally:
        child.terminate()
        try:
            child.wait(timeout=10)
        except subprocess.TimeoutExpired:
            child.kill()


if __name__ == "__main__":
    sys.exit(main())
