"""ArcheAxis one-command launcher and diagnostics (R13 seed).

Does what a candidate package entry point must do, without pretending to be one:

  python scripts/launch/core_launch.py --check    dependency + port diagnostics
  python scripts/launch/core_launch.py --probe    launch the Core, report its
                                                  readiness port, then stop it
  python scripts/launch/core_launch.py            start the Core and keep it in
                                                  the foreground until interrupted

Every path is resolved relative to the repository root, never from an installer
directory, and no path is guessed from a shell. A missing dependency is reported
as a named failure with an exit code, never as an empty success.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import secrets
import socket
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CORE_BINARY = REPO / ".project-local" / "build" / "cargo" / "debug" / "archeaxis-api.exe"


def free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def port_in_use(port: int) -> bool:
    with socket.socket() as probe:
        probe.settimeout(0.5)
        return probe.connect_ex(("127.0.0.1", port)) == 0


def dependencies() -> list[dict]:
    """The things the Core needs before it can serve, checked by name."""
    checks = [
        ("core binary", CORE_BINARY.is_file(), str(CORE_BINARY)),
        ("python interpreter", Path(sys.executable).is_file(), sys.executable),
        ("text worker", (REPO / "services/python-workers/document/worker_text.py").is_file(), "worker_text.py"),
        ("pdf worker", (REPO / "services/python-workers/document/worker_pdf.py").is_file(), "worker_pdf.py"),
        ("ocr worker", (REPO / "services/python-workers/vision/worker_ocr.py").is_file(), "worker_ocr.py"),
        ("pdf engine", _importable("pymupdf") or _importable("fitz"), "pymupdf"),
        ("ocr engine", _which("tesseract"), "tesseract executable"),
        (
            "ocr language data",
            (REPO / "tools/tesseract/tessdata/eng.traineddata").is_file(),
            "tools/tesseract/tessdata/eng.traineddata",
        ),
        ("cargo wrapper", (REPO / ".project-local/runs/cargo-full-workspace.bat").is_file(), "cargo-full-workspace.bat"),
    ]
    return [{"name": name, "ok": bool(ok), "detail": detail} for name, ok, detail in checks]


def _importable(name: str) -> bool:
    try:
        __import__(name)
        return True
    except ImportError:
        return False


def _which(name: str) -> bool:
    from shutil import which

    return which(name) is not None


def spawn_core(db: Path, port: int) -> tuple[subprocess.Popen, dict]:
    """Start the Core with a fresh launch claim and return (process, claim)."""
    claim = {
        "launch_token": secrets.token_hex(32),
        "session_id": secrets.token_hex(16),
    }
    child = subprocess.Popen(
        [str(CORE_BINARY), str(db), str(port)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
    )
    child.stdin.write(json.dumps(claim) + "\n")
    child.stdin.flush()
    child.stdin.close()  # the Core reads its claim to EOF
    return child, claim


def wait_ready(child: subprocess.Popen, seconds: float = 20.0) -> str | None:
    deadline = time.time() + seconds
    while time.time() < deadline:
        line = child.stdout.readline()
        if not line:
            if child.poll() is not None:
                return None
            continue
        if "127.0.0.1:" in line:
            return line.split("127.0.0.1:", 1)[1].split()[0].strip()
    return None


def main() -> int:
    with contextlib.suppress(Exception):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="dependency and port diagnostics only")
    parser.add_argument("--probe", action="store_true", help="launch, report the readiness port, then stop")
    parser.add_argument("--db", type=Path, default=REPO / ".project-local" / "runs" / "launch" / "core.sqlite")
    parser.add_argument("--port", type=int, default=0)
    args = parser.parse_args()

    report: dict = {"repository": str(REPO)}
    checks = dependencies()
    report["dependencies"] = checks
    report["dependencies_ok"] = all(c["ok"] for c in checks)

    for name, port in (("deeptutor backend", 8001), ("deeptutor frontend", 3782), ("ollama", 11434)):
        report[f"port_{port}_{name.replace(' ', '_')}"] = port_in_use(port)

    if args.check:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["dependencies_ok"] else 1

    if not CORE_BINARY.is_file():
        report["error"] = "the Core binary is not built; run the cargo wrapper first"
        print(json.dumps(report, ensure_ascii=False))
        return 2

    args.db.parent.mkdir(parents=True, exist_ok=True)
    port = args.port or free_port()
    report["requested_port"] = port
    child, claim = spawn_core(args.db, port)
    try:
        ready = wait_ready(child)
        report["ready_port"] = ready
        report["claim_actor"] = "human (default launch claim)"
        if ready is None:
            report["error"] = "the Core did not report readiness"
            return 3
        report["ok"] = True
        print(json.dumps(report, ensure_ascii=False))
        if args.probe:
            return 0
        print(f"ArcheAxis Core listening on http://127.0.0.1:{ready} - press Ctrl+C to stop", file=sys.stderr)
        return child.wait()
    finally:
        child.kill()
        child.wait()


if __name__ == "__main__":
    raise SystemExit(main())
