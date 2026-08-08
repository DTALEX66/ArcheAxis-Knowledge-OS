#!/usr/bin/env python3
"""Inject exact source/CI identity into a release artifact identity manifest.

Reads the current tree's Git commit, tree hash, and CI run info (from env
vars), then writes a separate artifact identity manifest next to the release
artifact. The tracked release-manifest.json always stays at
``source.*=unavailable`` — only the release artifact gets real identity.

Schema v2 separates the verification (full-qualification) CI run from the
release workflow run so a selective/main-bind run can never be mistaken for
full release qualification.

Usage:
    export GITHUB_RUN_ID=123456789  (the release workflow run)
    python scripts/release_inject_identity.py \
        --commit $(git rev-parse HEAD) \
        --tree $(git write-tree) \
        --tag v0.5.0 --version 0.5.0 \
        --url https://github.com/DTALEX66/Cognitive-Loop-OS/releases/tag/v0.5.0 \
        --verification-ci-run-id 987654 \
        --verification-ci-url https://github.com/DTALEX66/Cognitive-Loop-OS/actions/runs/987654 \
        --output .hermes/desktop-runtime-v1/runtime/release-identity.json
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

_HEX_40 = re.compile(r"[0-9a-f]{40}")
_REPO_URL = "https://github.com/DTALEX66/Cognitive-Loop-OS"


def _valid_run(value: str, label: str) -> int:
    try:
        parsed = int(value or "")
    except ValueError:
        print(f"ERROR: {label} must be a positive integer", file=sys.stderr)
        sys.exit(1)
    if parsed < 1:
        print(f"ERROR: {label} must be a positive integer", file=sys.stderr)
        sys.exit(1)
    return parsed


def main() -> int:
    parser = argparse.ArgumentParser(description="Inject release identity")
    parser.add_argument("--commit", required=True, help="Exact Git commit SHA (40 hex chars)")
    parser.add_argument("--tree", required=True, help="Exact Git tree hash (40 hex chars)")
    parser.add_argument("--tag", required=True, help="Release tag")
    parser.add_argument("--version", required=True, help="Product version")
    parser.add_argument("--url", required=True, help="Canonical GitHub Release URL")
    parser.add_argument(
        "--schema-version", choices=("1.0.0", "2.0.0"), default="2.0.0",
        help="Identity schema to write (default 2.0.0)",
    )
    # v2 fields
    parser.add_argument(
        "--verification-ci-run-id", type=int,
        help="Exact successful full-qualification CI run ID (v2)",
    )
    parser.add_argument(
        "--verification-ci-url",
        help="Canonical verification CI run URL (v2)",
    )
    # legacy v1 field
    parser.add_argument(
        "--ci-url",
        help="Deprecated v1: Canonical GitHub Actions run URL",
    )
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

    release_run_id = _valid_run(os.environ.get("GITHUB_RUN_ID", ""), "GITHUB_RUN_ID")
    if args.tag != f"v{args.version}" or not args.url.startswith("https://"):
        print("ERROR: invalid release identity arguments", file=sys.stderr)
        return 1

    release = {
        "tag": args.tag,
        "version": args.version,
        "channel": "stable",
        "public": True,
        "url": args.url,
    }

    if args.schema_version == "2.0.0":
        if args.verification_ci_run_id is None or not args.verification_ci_url:
            print(
                "ERROR: --verification-ci-run-id and --verification-ci-url are required for schema 2.0.0",
                file=sys.stderr,
            )
            return 1
        if args.verification_ci_run_id < 1 or not args.verification_ci_url.startswith("https://"):
            print("ERROR: invalid verification CI identity", file=sys.stderr)
            return 1
        source = {
            "commit": commit,
            "tree": tree,
            "verification_ci_run_id": args.verification_ci_run_id,
            "verification_ci_url": args.verification_ci_url,
            "release_run_id": release_run_id,
            "release_run_url": f"{_REPO_URL}/actions/runs/{release_run_id}",
        }
    else:
        if not args.ci_url:
            print("ERROR: --ci-url is required for schema 1.0.0", file=sys.stderr)
            return 1
        if not args.ci_url.startswith("https://"):
            print("ERROR: invalid v1 ci_url", file=sys.stderr)
            return 1
        source = {
            "commit": commit,
            "tree": tree,
            "ci_run": release_run_id,
            "ci_url": args.ci_url,
        }

    identity = {
        "schema_version": args.schema_version,
        "release": release,
        "source": source,
    }

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(identity, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"Identity manifest written: {output}")
    print(f"  schema_version: {args.schema_version}")
    print(f"  commit: {commit}")
    print(f"  tree:   {tree}")
    print(f"  release_run_id: {release_run_id}")
    if args.schema_version == "2.0.0":
        print(f"  verification_ci_run_id: {args.verification_ci_run_id}")
    else:
        print(f"  ci_run: {release_run_id}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
