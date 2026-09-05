#!/usr/bin/env python3
"""vNext capability-worker smoke gate (workers-vnext).

Runs against the real worker entrypoints in services/python-workers:

- every worker module compiles;
- worker_extract returns the JSON envelope contract on a real file
  (engine/engine_version/text/loss_receipt; BOM stripped);
- a missing input exits non-zero with {"error": ...} — never a fake success.

The protocol envelope is defined in
packages/contracts/v1/worker-protocol.schema.json.
"""

from __future__ import annotations

import json
import py_compile
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKERS = ROOT / "services" / "python-workers"
WORKER_EXTRACT = WORKERS / "worker_extract.py"

ENVELOPE_KEYS = ("engine", "engine_version", "text", "loss_receipt")


def _run_worker(args: list[str], *, text: str | None = None) -> subprocess.CompletedProcess[str]:
    import os

    child_env = dict(os.environ)
    child_env.setdefault("PYTHONUTF8", "1")
    child_env.setdefault("PYTHONIOENCODING", "utf-8")
    return subprocess.run(
        [sys.executable, str(WORKER_EXTRACT), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=child_env,
        input=text,
        timeout=60,
    )


def main() -> int:
    failures: list[str] = []
    if not WORKER_EXTRACT.is_file():
        print(f"ERROR: worker entrypoint missing: {WORKER_EXTRACT}")
        return 1

    modules = sorted(WORKERS.glob("*.py"))
    for module in modules:
        try:
            py_compile.compile(str(module), doraise=True)
        except py_compile.PyCompileError as exc:
            failures.append(f"{module.name}: compile failed: {exc}")

    with tempfile.TemporaryDirectory() as tmp:
        sample = Path(tmp) / "sample.txt"
        sample.write_bytes("\ufeffBOM-marked 原件内容 hello\n".encode("utf-8"))
        ok = _run_worker([str(sample)])
        if ok.returncode != 0:
            failures.append(f"worker_extract exit {ok.returncode}: {ok.stderr.strip()[:300]}")
        else:
            try:
                envelope = json.loads(ok.stdout.strip().splitlines()[-1])
            except (json.JSONDecodeError, IndexError) as exc:
                failures.append(f"worker_extract stdout not a JSON envelope: {exc}")
                envelope = {}
            for key in ENVELOPE_KEYS:
                if key not in envelope:
                    failures.append(f"worker_extract envelope missing key: {key}")
            if envelope.get("text") != "BOM-marked 原件内容 hello\n":
                failures.append(
                    f"worker_extract text mismatch (BOM must be stripped): {envelope.get('text')!r}"
                )
            if not isinstance(envelope.get("loss_receipt"), dict):
                failures.append("worker_extract loss_receipt must be an object")

        missing = _run_worker([str(Path(tmp) / "does-not-exist.txt")])
        if missing.returncode == 0:
            failures.append("worker_extract succeeded on a missing file (must fail)")
        else:
            try:
                error_payload = json.loads(
                    (missing.stdout or missing.stderr).strip().splitlines()[-1]
                )
            except (json.JSONDecodeError, IndexError):
                error_payload = {}
            if "error" not in error_payload:
                failures.append(
                    "worker failure output must carry an error payload, "
                    f"got: {(missing.stdout or missing.stderr).strip()[:200]!r}"
                )

    if failures:
        print("workers-vnext check failed:")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("workers-vnext check passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
