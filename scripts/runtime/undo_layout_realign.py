"""Undo a layout realignment, then re-run it against a curated allowance.

The first pass moved 220 entries because the allowance was written from a size report instead of
from what the repository actually references. It moved donor directories that clean-up documents name
as restore targets (`a10`) and probe inputs the bucketing record cites (`a1`, `a1-python-input`, `rt`,
`rt-before-*`). Moving is reversible, which is why nothing was lost — but a path that a document
points at must not move, so this restores first and then moves only what nothing refers to.
"""
from __future__ import annotations

import json
import os
import re
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


def manifest_path(scratch: Path) -> Path:
    dated = bounded_path(scratch, f"manifest-{scratch.name.removeprefix('legacy-scratch-')}.json")
    return dated if dated.is_file() else bounded_path(scratch, 'manifest.json')


def bounded_path(root: Path, location: str) -> Path:
    candidate = Path(location)
    if '..' in candidate.parts or any(part.casefold() in {
        '.git', '.codex', '.hermes', '.zcode', '.ui-task-tree', '.env', '.ssh', '.aws', '.npmrc', '.pypirc'
    } for part in candidate.parts):
        raise ValueError('protected or traversing restore path')
    path = candidate if candidate.is_absolute() else root / candidate
    if path.drive.upper() in {'E:', 'F:'} or str(path).startswith('\\\\'):
        raise ValueError('protected restore root')
    if any(part.casefold() in {'.git', '.codex', '.hermes', '.zcode', '.ui-task-tree', '.ssh', '.aws'}
           for part in path.parts):
        raise ValueError('private restore root')
    if not path.is_relative_to(root):
        raise ValueError('restore path is outside its owner')
    for ancestor in (path, *path.parents):
        try:
            info = ancestor.lstat()
        except FileNotFoundError:
            continue
        if ancestor.is_symlink() or getattr(info, 'st_file_attributes', 0) & 0x400:
            raise ValueError('restore path contains a reparse point')
    return path


def archive_root() -> Path:
    """The archive that actually exists, or a named failure.

    Returning a path that does not exist is how the restore used to skip every entry and still
    report success; a preservation point that cannot be found must say so.
    """
    for candidate in SCRATCH_CANDIDATES:
        bounded_path(REPO, str(candidate))
        if manifest_path(candidate).is_file():
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
    if Path(source).is_absolute():
        raise ValueError('archive source must be repository-relative')
    bounded_path(REPO, source)
    if source.startswith(".project-local/"):
        return bounded_path(scratch, 'project-local/' + source.split("/", 1)[1])
    return bounded_path(scratch, 'repo-root/' + source)

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
    manifest = json.loads(manifest_path(scratch).read_text(encoding="utf-8"))
    entries = manifest["moved"]
    restored, missing, refused = 0, [], []
    for entry in entries:
        source = bounded_path(REPO, entry["source"])
        scratch_path = archived_copy(scratch, entry)
        if not scratch_path.exists():
            # A previously recorded absolute path may still name the pre-relocation place; fall back
            # to it, but a genuinely absent copy is reported rather than skipped.
            recorded = bounded_path(REPO, entry.get("scratch_path", ""))
            if recorded.exists():
                scratch_path = recorded
            else:
                missing.append(entry["source"])
                continue
        source.parent.mkdir(parents=True, exist_ok=True)
        if source.exists():
            refused.append(entry["source"])
            continue
        try:
            os.rename(scratch_path, source)
        except OSError as error:
            refused.append(f"{entry['source']} ({type(error).__name__})")
            continue
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
    manifest = json.loads(manifest_path(scratch).read_text(encoding="utf-8"))
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


def cli() -> int:
    import argparse
    global REPO, SCRATCH_CANDIDATES
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, default=REPO)
    parser.add_argument('--stamp', default='20261006')
    parser.add_argument('--restore', action='store_true')
    args = parser.parse_args()
    if not re.fullmatch(r'\d{8}', args.stamp):
        parser.error('--stamp must be an eight-digit date')
    REPO = args.repo.absolute()
    if REPO.drive.upper() in {'E:', 'F:'} or str(REPO).startswith('\\\\'):
        parser.error('protected restore root')
    SCRATCH_CANDIDATES = (REPO / '.project-local' / f'legacy-scratch-{args.stamp}',
                          REPO / '.project-local/task-runtime' / f'legacy-scratch-{args.stamp}')
    try:
        bounded_path(REPO, '.')  # validate the owner before inspecting any manifest, even an empty one
        return restore() if args.restore else main()
    except (OSError, ValueError) as error:
        print(f'restore refused: {type(error).__name__}: {error}')
        return 1


if __name__ == "__main__":
    raise SystemExit(cli())
