#!/usr/bin/env python3
"""Generate a SHA-256 checksum manifest for a release artifact.

Usage:
    python scripts/release_checksum.py --wheel dist/*.whl --installer *.exe --output .hermes/task-runtime/artifacts/release-checksums.txt

Output format (same as sha256sum):
    <sha256>  <basename>
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate release artifact checksum manifest")
    parser.add_argument("--wheel", type=str, help="Path to the .whl file")
    parser.add_argument("--installer", type=str, help="Path to the NSIS installer .exe")
    parser.add_argument("--output", type=str, required=True, help="Output checksum file path")
    args = parser.parse_args()

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)

    lines: list[str] = []
    artifacts: list[tuple[str, Path]] = []

    if args.wheel:
        wheel = Path(args.wheel)
        if not wheel.exists():
            print(f"ERROR: wheel not found: {wheel}", file=sys.stderr)
            return 1
        artifacts.append(("wheel", wheel))

    if args.installer:
        installer = Path(args.installer)
        if not installer.exists():
            print(f"ERROR: installer not found: {installer}", file=sys.stderr)
            return 1
        artifacts.append(("installer", installer))

    if not artifacts:
        print("ERROR: at least one of --wheel or --installer is required", file=sys.stderr)
        return 1

    for label, path in artifacts:
        digest = _sha256(path)
        lines.append(f"{digest}  {path.name}")
        print(f"  {label}: {path.name}  SHA-256: {digest}")

    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nChecksum manifest written: {output} ({len(lines)} artifact(s))")
    return 0


if __name__ == "__main__":
    sys.exit(main())
