"""Fail closed when the release workflow omits the formal desktop chain."""

from __future__ import annotations

import argparse
from pathlib import Path


REQUIRED_PATHS = (
    "apps/ArcheAxis.Desktop/ArcheAxis.Desktop.csproj",
    "crates/archeaxis-api",
    "services/python-workers",
)


def verify(root: Path, workflow: Path) -> list[str]:
    errors: list[str] = []
    for relative in REQUIRED_PATHS:
        if not (root / relative).exists():
            errors.append(f"formal release component missing: {relative}")
    text = workflow.read_text(encoding="utf-8")
    if "ArcheAxis.Desktop" not in text:
        errors.append("release workflow does not mention the formal Avalonia desktop")
    if "crates/archeaxis-api" not in text and "Rust Core" not in text:
        errors.append("release workflow does not identify the Rust Core")
    if "services/python-workers" not in text and "python worker" not in text.lower():
        errors.append("release workflow does not identify the Python workers")
    if "Tauri" in text and "recovery" not in text.lower():
        errors.append("legacy Tauri references are not labelled recovery")
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
    print("PASS: formal Avalonia -> Rust Core -> Python workers release chain is identified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
