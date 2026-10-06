"""Undo a layout realignment, then re-run it against a curated allowance.

The first pass moved 220 entries because the allowance was written from a size report instead of
from what the repository actually references. It moved donor directories that clean-up documents name
as restore targets (`a10`) and probe inputs the bucketing record cites (`a1`, `a1-python-input`, `rt`,
`rt-before-*`). Moving is reversible, which is why nothing was lost — but a path that a document
points at must not move, so this restores first and then moves only what nothing refers to.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRATCH = REPO / ".project-local" / "task-runtime" / "legacy-scratch-20261006"
MANIFEST = SCRATCH / "manifest.json"

REFERENCE_DIRS = ("docs", ".project-local/task-runtime/aaos01-tools", "tests", "scripts", ".github")


def referenced(name: str) -> bool:
    """Whether any tracked document, receipt or test names this path."""
    needle = f".project-local/{name}"
    for directory in REFERENCE_DIRS:
        target = REPO / directory
        if not target.is_dir():
            continue
        try:
            listing = subprocess.run(
                ["git", "grep", "-l", "-F", needle, "--", directory],
                cwd=REPO, capture_output=True, text=True)
        except OSError:
            return True
        if listing.returncode == 0 and listing.stdout.strip():
            return True
    return False


def restore() -> int:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    restored = 0
    for entry in manifest["moved"]:
        source = REPO / entry["source"]
        scratch_path = REPO / entry["scratch_path"]
        if not scratch_path.exists():
            continue
        source.parent.mkdir(parents=True, exist_ok=True)
        if source.exists():
            print(f"refused: {source} already exists")
            return 1
        shutil.move(str(scratch_path), str(source))
        restored += 1
    print(f"restored {restored} of {len(manifest['moved'])} moved entries")
    return 0


def main() -> int:
    if "--restore" in sys.argv:
        return restore()
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    kept, moved = [], []
    for entry in manifest["moved"]:
        name = entry["source"].split("/", 1)[-1]
        if referenced(name):
            kept.append(entry["source"])
    print(f"referenced (must stay): {len(kept)}")
    for path in kept[:12]:
        print(f"  keep {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
