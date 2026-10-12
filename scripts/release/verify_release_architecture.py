"""Fail closed when the release workflow omits the formal desktop chain."""

from __future__ import annotations

import argparse
from pathlib import Path


REQUIRED_PATHS = (
    "src-tauri/tauri.conf.json",
    "frontend/package.json",
    "crates/archeaxis-api",
    "services/python-workers",
)


def verify(root: Path, workflow: Path) -> list[str]:
    errors: list[str] = []
    for relative in REQUIRED_PATHS:
        if not (root / relative).exists():
            errors.append(f"formal release component missing: {relative}")
    text = workflow.read_text(encoding="utf-8")
    if "if: ${{ false }} # R6 release freeze" not in text:
        errors.append("release publish job is not disabled by the current R6 freeze")
    if "src-tauri/frontend" not in text:
        errors.append("release workflow does not identify the formal Tauri/React desktop")
    if "crates/archeaxis-api" not in text and "Rust Core" not in text:
        errors.append("release workflow does not identify the Rust Core")
    if "services/python-workers" not in text and "python worker" not in text.lower():
        errors.append("release workflow does not identify the Python workers")
    for marker in ("release-candidate.json", "candidate.commit", "GITHUB_SHA", "candidate.installer.sha256", "candidate.executable.sha256", "candidate.frontend.sha256", "verify_nsis_install.ps1"):
        if marker not in text:
            errors.append(f"release workflow missing exact-SHA Tauri candidate validation: {marker}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--workflow", type=Path, default=Path(".github/workflows/release.yml"))
    args = parser.parse_args()
    errors = verify(args.root.resolve(), args.workflow.resolve())
    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        return 1
    print("PASS: formal Tauri/React -> Rust Core -> Python workers are identified; release remains frozen")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
