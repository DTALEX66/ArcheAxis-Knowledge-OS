"""Capture a source snapshot before builds for later Candidate provenance checks.

The receipt is project-local, append-only, and contains no source file contents or paths.
"""

from __future__ import annotations

import argparse
import datetime
import importlib.util
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"required project module is missing: {path.name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


candidate = _load_module("capture_candidate_source", Path(__file__).with_name("candidate.py"))
dev = _load_module("capture_candidate_dev", REPO / "scripts/runtime/dev.py")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="capture a pre-build Candidate source snapshot")
    parser.add_argument("--root", type=Path, default=REPO, help="exact Git worktree root")
    parser.add_argument("--out", type=Path, required=True, help="new receipt path under project .project-local/runs")
    args = parser.parse_args(argv)
    try:
        root = args.root.resolve()
        paths = dev.layout(root)
        output = dev.safe_path(args.out)
        relative = output.relative_to(paths["dev"])
        if not relative.parts or relative.parts[0] != "runs":
            raise ValueError("snapshot receipt must be under project .project-local/runs")
        if output.exists():
            raise ValueError("snapshot receipt already exists; choose a new path")
        snapshot = candidate.working_tree_snapshot(root)
        payload = {
            "schema": "aaos.source-snapshot-receipt/v1",
            "captured_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "snapshot": snapshot,
        }
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("x", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
    except (OSError, ValueError, RuntimeError) as error:
        print(f"source snapshot refused: {error}", file=sys.stderr)
        return 2
    print(f"source snapshot captured: {output}")
    print(f"  sha256 {snapshot['sha256']}")
    print(f"  files {snapshot['file_count']}; untracked build inputs {snapshot['untracked_build_input_count']}; "
          f"path-only exclusions {snapshot['excluded_path_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
