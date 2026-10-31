#!/usr/bin/env python3
"""Local preflight for the byte-pinned contract chain.

A dependency or ledger change has to rebind every derived artifact it feeds.  The CI
lint/test jobs catch a missed rebind, but only after a push.  This script runs the same
checks locally and exits non-zero on the first broken link:

    uv.lock / pyproject.toml -> release-manifest -> resource-qualification
    -> resource-catalog.ts
    SUPPLY_CHAIN_LEDGER.json -> OSS reuse manifest/payload
    capability-requirements.yaml -> external-resources-index.json
    pyproject.toml -> requirements.txt

Run it before committing any dependency, lockfile, ledger or generated-contract change:

    .venv/Scripts/python.exe scripts/ci/preflight_contracts.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CHECKS = [
    ("resource catalog", [sys.executable, "-B", "scripts/contracts/generate_resource_catalog.py", "--check"]),
    ("release manifest", [sys.executable, "-m", "pytest", "tests/test_release_manifest.py", "-q"]),
    ("requirements sync", [
        sys.executable,
        "-m",
        "pytest",
        "tests/test_runtime_operations.py::test_requirements_txt_matches_pyproject_runtime_dependencies",
        "-q",
    ]),
    ("external resource index", [
        sys.executable,
        "-m",
        "pytest",
        "tests/workflow/test_external_resources_index.py",
        "-q",
    ]),
    ("OSS reuse manifest", [
        sys.executable,
        "-m",
        "pytest",
        "tests/workflow/test_oss_reuse_artifact_manifest.py",
        "-q",
    ]),
    ("document authority", [sys.executable, "-B", "scripts/ci/check_document_authority.py"]),
]


def main() -> int:
    failures: list[str] = []
    for name, command in CHECKS:
        print(f"[preflight] {name}: {' '.join(command)}", flush=True)
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if result.returncode != 0:
            failures.append(name)
            print(f"[fail] {name}", flush=True)
            output = (result.stdout + result.stderr).strip().splitlines()
            for line in output[-20:]:
                print(f"  {line}", flush=True)
        else:
            print(f"[ok] {name}", flush=True)
    if failures:
        print(f"[preflight] FAILED: {', '.join(failures)}", flush=True)
        return 1
    print("[preflight] all contract links agree", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
