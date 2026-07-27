#!/usr/bin/env python3
"""Inject exact source/CI identity into a release artifact identity manifest.

Reads the current tree's Git commit, tree hash, and CI run info (from env
vars), then writes a separate artifact identity manifest next to the release
artifact. The tracked release-manifest.json always stays at
``source.commit=unavailable`` — only the release artifact gets real identity.

Usage:
    export GITHUB_RUN_ID=123456789  (optional: set in CI)
    python scripts/release_inject_identity.py \
        --commit $(git rev-parse HEAD) \
        --tree $(git write-tree) \
        --branch feat/absorption-roadmap-r0 \
        --output .hermes/task-runtime/artifacts/release-identity.json
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

_HEX_40 = re.compile(r"[0-9a-f]{40}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Inject release identity")
    parser.add_argument("--commit", required=True, help="Exact Git commit SHA (40 hex chars)")
    parser.add_argument("--tree", required=True, help="Exact Git tree hash (40 hex chars)")
    parser.add_argument("--branch", required=True, help="Git branch name")
    parser.add_argument("--output", required=True, help="Output identity manifest path")
    args = parser.parse_args()

    commit = args.commit.strip()
    tree = args.tree.strip()

    if not _HEX_40.fullmatch(commit):
        print(f"ERROR: invalid commit SHA: {commit}", file=sys.stderr)
        return 1
    if not _HEX_40.fullmatch(tree):
        print(f"ERROR: invalid tree hash: {tree}", file=sys.stderr)
        return 1

    ci_run = os.environ.get("GITHUB_RUN_ID")
    if ci_run:
        try:
            ci_run = int(ci_run)
        except ValueError:
            print(f"WARNING: GITHUB_RUN_ID is not a valid integer: {ci_run}", file=sys.stderr)
            ci_run = None

    identity = {
        "schema_version": "1.0.0",
        "source": {
            "commit": commit,
            "tree": tree,
            "branch": args.branch,
            "ci_run": ci_run,
        },
        "generated_at": "ISO-8601",  # placeholder — CI may not have tz
    }

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(identity, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"Identity manifest written: {output}")
    print(f"  commit: {commit}")
    print(f"  tree:   {tree}")
    print(f"  branch: {args.branch}")
    print(f"  ci_run: {ci_run}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
