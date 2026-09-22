"""Prepare a deterministic handoff report when account quota is nearly exhausted.

The Codex account quota is intentionally supplied by the caller; this project
script cannot read account state or credentials.  At or below the threshold it
records the exact Git refs, delivery gap, and safe tracked handoff documents.
It never stages, commits, pushes, reads private agent state, or includes
untracked user material.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_THRESHOLD = 2.0
HANDOFF_PATHS = (
    "docs/current/R6-EXECUTION.md",
    "docs/current/R6-STATE.json",
    "docs/current/M0-DIRECTION-OVERRIDE-20260920.md",
    "docs/current/REPOSITORY-CLEANUP-HANDOFF-20260921.md",
    "docs/current/LOW-QUOTA-HANDOFF-POLICY.md",
    "docs/CONFIGURATION_AUTHORITY_INDEX.md",
    "docs/DOCUMENTATION_AUTHORITY_INDEX.md",
    "docs/SHARED_RESOURCE_PATH_INDEX.md",
)


def classify_quota(remaining_percent: float, threshold: float = DEFAULT_THRESHOLD) -> str:
    if remaining_percent < 0 or remaining_percent > 100:
        raise ValueError("remaining_percent must be between 0 and 100")
    if threshold < 0 or threshold > 100:
        raise ValueError("threshold must be between 0 and 100")
    return "UPLOAD_REQUIRED" if remaining_percent <= threshold else "MONITORING"


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(["git", *args], cwd=root, text=True, capture_output=True, check=True)
    return result.stdout.strip()


def build_report(root: Path, remaining_percent: float, threshold: float = DEFAULT_THRESHOLD) -> dict:
    root = Path(os.path.abspath(root))
    state = classify_quota(remaining_percent, threshold)
    branch = _git(root, "branch", "--show-current")
    head = _git(root, "rev-parse", "HEAD")
    upstream = _git(root, "for-each-ref", "--format=%(upstream:short)", f"refs/heads/{branch}")
    ahead = None
    commit_range = None
    if upstream:
        ahead = int(_git(root, "rev-list", "--count", f"{upstream}..HEAD"))
        commit_range = f"{upstream}..HEAD"
    # Never enumerate untracked names into a report that may be uploaded. The
    # handoff only needs tracked modifications; private/history paths remain
    # excluded by construction.
    status = _git(root, "status", "--short", "--untracked-files=no")
    tracked_handoff = [path for path in HANDOFF_PATHS if (root / path).is_file()]
    report = {
        "schema": "archeaxis.low-quota-handoff/v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "remaining_percent": remaining_percent,
        "threshold_percent": threshold,
        "state": state,
        "git": {"branch": branch, "head": head, "upstream": upstream or None,
                "ahead_of_upstream": ahead, "upload_commit_range": commit_range},
        "working_tree_status": status.splitlines() if status else [],
        "safe_tracked_handoff_paths": tracked_handoff,
        "private_or_untracked_excluded": [".codex/", ".zcode/", ".hermes/", "untracked user/history assets"],
        "upload": {
            "required": state == "UPLOAD_REQUIRED",
            "action": "stage exact listed paths, commit, push, then read back both refs" if state == "UPLOAD_REQUIRED" else "continue monitoring",
            "automatic_push": False,
        },
    }
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--remaining-percent", required=True, type=float)
    parser.add_argument("project_root", nargs="?", type=Path, default=Path("."))
    parser.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD)
    parser.add_argument("--output", type=Path, required=True, help="must be under project .project-local")
    args = parser.parse_args()
    try:
        root = Path(os.path.abspath(args.project_root))
        report = build_report(root, args.remaining_percent, args.threshold)
        output = Path(os.path.abspath(args.output))
        output.relative_to(root / ".project-local")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        print(f"low-quota handoff failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
