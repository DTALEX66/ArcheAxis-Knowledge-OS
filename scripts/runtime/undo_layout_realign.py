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
# The archive was first written under `task-runtime/` and then relocated to the development root
# because it exceeded that class's budget. The recorded per-entry `scratch_path` still names the old
# place, so it cannot be trusted: the archive is located here, and each entry is derived from its
# own `source` relative to the archive's own layout.
SCRATCH_CANDIDATES = (
    REPO / ".project-local" / "legacy-scratch-20261006",
    REPO / ".project-local" / "task-runtime" / "legacy-scratch-20261006",
)


def archive_root() -> Path:
    """The archive that actually exists, or a named failure.

    Returning a path that does not exist is how the restore used to skip every entry and still
    report success; a preservation point that cannot be found must say so.
    """
    for candidate in SCRATCH_CANDIDATES:
        if (candidate / "manifest.json").is_file():
            return candidate
    raise SystemExit(
        "no layout archive found; looked in " + ", ".join(str(c) for c in SCRATCH_CANDIDATES))


def archived_copy(scratch: Path, entry: dict) -> Path:
    """Where an entry's bytes live inside the archive, from its own recorded source.

    `realign_dev_layout` keeps the two trees apart — `project-local/<name>` for entries that were
    under `.project-local/`, `repo-root/<relative>` for the rest — so the location is derivable from
    the source alone, which is what makes the archive relocatable at all.
    """
    source = entry["source"]
    if source.startswith(".project-local/"):
        return scratch / "project-local" / source.split("/", 1)[1]
    return scratch / "repo-root" / source

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
    scratch = archive_root()
    manifest = json.loads((scratch / "manifest.json").read_text(encoding="utf-8"))
    entries = manifest["moved"]
    restored, missing, refused = 0, [], []
    for entry in entries:
        source = REPO / entry["source"]
        scratch_path = archived_copy(scratch, entry)
        if not scratch_path.exists():
            # A previously recorded absolute path may still name the pre-relocation place; fall back
            # to it, but a genuinely absent copy is reported rather than skipped.
            recorded = REPO / entry.get("scratch_path", "")
            if recorded.exists():
                scratch_path = recorded
            else:
                missing.append(entry["source"])
                continue
        source.parent.mkdir(parents=True, exist_ok=True)
        if source.exists():
            refused.append(entry["source"])
            continue
        shutil.move(str(scratch_path), str(source))
        restored += 1
    print(f"archive: {scratch}")
    print(f"restored {restored} of {len(entries)} moved entries")
    for path in refused[:12]:
        print(f"  refused (already present): {path}")
    for path in missing[:12]:
        print(f"  MISSING archived copy: {path}")
    if missing or refused:
        # Exit 0 here would report a restore that did not happen. The point of keeping an archive is
        # that it can be relied on; a partial or refused restore has to be visible to a script.
        print(f"incomplete: {len(missing)} missing, {len(refused)} refused")
        return 1
    return 0


def main() -> int:
    if "--restore" in sys.argv:
        return restore()
    scratch = archive_root()
    manifest = json.loads((scratch / "manifest.json").read_text(encoding="utf-8"))
    kept = [entry["source"] for entry in manifest["moved"]
            if referenced(entry["source"].split("/", 1)[-1])]
    present = [entry["source"] for entry in manifest["moved"]
               if not archived_copy(scratch, entry).exists()]
    print(f"archive: {scratch}")
    print(f"entries: {len(manifest['moved'])}")
    print(f"referenced (must stay): {len(kept)}")
    for path in kept[:12]:
        print(f"  keep {path}")
    print(f"entries whose archived copy is missing: {len(present)}")
    for path in present[:12]:
        print(f"  MISSING {path}")
    return 1 if present else 0


if __name__ == "__main__":
    raise SystemExit(main())
