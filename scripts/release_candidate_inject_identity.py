#!/usr/bin/env python3
"""Write the non-public identity embedded in a CI-qualified installer.

The candidate identity records only facts available during CI qualification.
The tag's public Release identity remains a separate artifact generated after
the exact candidate is promoted and read back from GitHub.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

_HEX_40 = re.compile(r"[0-9a-f]{40}")
_REPOSITORY_URL = "https://github.com/DTALEX66/ArcheAxis-Knowledge-OS"


def _positive_run(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be a positive integer") from exc
    if parsed < 1:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return parsed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--tree", required=True)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--verification-ci-run-id", required=True, type=_positive_run)
    parser.add_argument("--verification-ci-url", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    commit = args.commit.strip()
    tree = args.tree.strip()
    if _HEX_40.fullmatch(commit) is None or _HEX_40.fullmatch(tree) is None:
        print("ERROR: commit and tree must be 40-character lowercase SHA-1 values", file=sys.stderr)
        return 1
    if args.tag != f"v{args.version}" or not args.version:
        print("ERROR: tag must be v<version>", file=sys.stderr)
        return 1
    expected_url = f"{_REPOSITORY_URL}/actions/runs/{args.verification_ci_run_id}"
    if args.verification_ci_url != expected_url:
        print("ERROR: verification CI URL must be the canonical repository run URL", file=sys.stderr)
        return 1

    identity = {
        "schema_version": "candidate-1.0.0",
        "candidate": {
            "tag": args.tag,
            "version": args.version,
            "channel": "stable",
            "public": False,
        },
        "source": {
            "commit": commit,
            "tree": tree,
            "verification_ci_run_id": args.verification_ci_run_id,
            "verification_ci_url": args.verification_ci_url,
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(identity, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
