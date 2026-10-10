"""Move every out-of-layout entry into a dated scratch area, with a manifest. Nothing is deleted.

The repository's ignored development root had accumulated 200+ loose one-off scripts, log files and
ad-hoc directories at its top level, which is how an agreed layout decays: each is harmless alone and
the set becomes unreadable. Moving them (not deleting them) restores the layout without destroying
anything a receipt might cite, and the manifest lists every source path so any single file can be put
back.

Root-level generated leftovers (`__pycache__`, `*.egg-info`, a stray `build/`) are moved the same way
for the same reason: they are regenerable, but "regenerable" is not a licence to delete silently.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import subprocess
from pathlib import Path


def _load_sibling(filename: str):
    """The sibling module, loaded by file path.

    `sys.path.insert` is refused by the architecture guard, and each of these scripts is launched
    directly rather than imported as a package, so the sibling is loaded from this file's own
    directory the same way the workers load their shared helpers.
    """
    path = Path(__file__).resolve().parent / filename
    spec = importlib.util.spec_from_file_location(path.stem, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"{filename} is missing beside this script")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


storage_report = _load_sibling("storage_report.py")

REPO = storage_report.REPO


def file_digest(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def worktree_roots(repo: Path, *, require_complete: bool = False) -> list[Path]:
    """Project-owned checkouts only; registered private clones are not project evidence."""
    import subprocess

    roots = [repo]
    common = subprocess.run(["git", "-C", str(repo), "rev-parse", "--path-format=absolute", "--git-common-dir"],
                            capture_output=True, text=True, encoding="utf-8", check=True)
    owner = Path(common.stdout.strip()).parent
    listing = subprocess.run(["git", "-C", str(repo), "worktree", "list", "--porcelain"],
                             capture_output=True, text=True, encoding="utf-8", errors="replace")
    if listing.returncode:
        raise RuntimeError('cannot enumerate checkout references')
    excluded = False
    for line in (listing.stdout or "").splitlines():
        if line.startswith("worktree "):
            path = Path(line[len("worktree "):].strip())
            # Filter lexically before is_dir() or any filesystem probe of a foreign/private tree.
            if any(part.casefold() in {'.ui-task-tree', '.codex', '.hermes', '.zcode'} for part in path.parts):
                excluded = True
                continue
            if path != owner and not path.is_relative_to(owner / '.project-local' / 'worktrees'):
                excluded = True
                continue
            try:
                present = path.is_dir()
            except OSError:
                present = False
            if not present:
                excluded = True
            elif path != repo:
                roots.append(path)
    if require_complete and excluded:
        raise RuntimeError('reference coverage includes protected or foreign checkouts; preserve assets')
    return roots


def referenced_exactly(relative: str, repo: Path) -> bool:
    """Whether any tracked document, receipt or test names this exact path.

    Substring matching is not enough and cost a full restore: `.project-local/a10` is a documented
    restore target and `.project-local/rt` is cited by hand-off notes, while a loose
    `.project-local/rust-ws-12.log` is named by nothing. The question is whether the path itself is
    pointed at, so the path itself is what gets searched. Every checkout is searched, not just this
    one: the handoff that cites a receipt lives on the delivery branch, and reading only the primary
    checkout's tracked text would call such a path unreferenced and move it out from under its own
    evidence trail.
    """
    needle = relative.replace("\\", "/")
    try:
        roots = worktree_roots(repo, require_complete=True)
    except (OSError, RuntimeError, subprocess.SubprocessError):
        return True
    for root in roots:
        try:
            found = subprocess.run(["git", "grep", "-l", "-F", needle],
                                   cwd=root, capture_output=True, text=True)
        except OSError:
            return True
        if found.returncode not in (0, 1):
            return True  # inability to read is not evidence that a path is unreferenced
        if found.returncode == 0 and found.stdout.strip():
            return True
    return False


def plan_moves(repo: Path, scratch: Path) -> tuple[list[tuple[Path, Path]], list[str]]:
    report = storage_report.measure(repo)
    if report.get("measurement_status") != "PASS":
        raise RuntimeError("incomplete ownership measurement; preserve assets, no realignment plan")
    moves: list[tuple[Path, Path]] = []
    skipped: list[str] = []
    def candidate(source: Path) -> None:
        storage_report.safe_path(source)
        if source.is_dir():
            measured = storage_report.directory_measurement(source)
            if measured['errors'] or measured['excluded_private'] or measured['links']:
                raise RuntimeError(f"incomplete or redirected candidate; preserve {source}")
        elif source.name.casefold().startswith('.env') or source.name.casefold() in {'.npmrc', '.pypirc', 'id_rsa', 'id_ed25519'}:
            raise RuntimeError(f"protected file is not a migration candidate: {source.name}")
    for name in report["dev_strays"]:
        source = repo / name
        candidate(source)
        if not source.exists():
            continue
        relative = name
        if referenced_exactly(relative, repo):
            skipped.append(f"{relative}: referenced or reference coverage unavailable")
            continue
        moves.append((source, scratch / "project-local" / name.split("/", 1)[1]))
    for name in [item for item in report["out_of_layout"] if item.startswith("root:")]:
        relative = name[len("root: "):].rstrip("/")
        source = repo / relative
        candidate(source)
        if not source.exists():
            continue
        if relative == "data":
            skipped.append("data/ is sanctioned local runtime state")
            continue
        if referenced_exactly(relative, repo):
            skipped.append(f"{relative}: referenced or reference coverage unavailable")
            continue
        moves.append((source, scratch / "repo-root" / relative))
    return moves, skipped


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=None,
                        help="checkout whose dev root to realign (default: this script's repository)")
    parser.add_argument("--stamp", default="20261006",
                        help="date suffix for the scratch area and its manifest")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if not re.fullmatch(r'\d{8}', args.stamp):
        parser.error('--stamp must be an eight-digit date')
    repo = Path(args.repo).absolute() if args.repo else REPO
    scratch = repo / ".project-local" / f"legacy-scratch-{args.stamp}"

    try:
        storage_report.safe_path(repo)
        storage_report.safe_path(scratch)
        moves, skipped = plan_moves(repo, scratch)
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        print(f"refused: {error}")
        return 1
    if args.dry_run:
        print(json.dumps({"repo": str(repo), "scratch": str(scratch),
                          "would_move": [str(s.relative_to(repo)).replace("\\", "/") for s, _ in moves],
                          "skipped": skipped}, ensure_ascii=False, indent=1))
        return 0
    manifest = {
        "schema": "archeaxis/layout-scratch/v1",
        "scratch": str(scratch),
        "moved": [],
        "skipped": skipped,
        "note": "restore by moving each source back to the repository root; nothing was deleted",
    }
    scratch.mkdir(parents=True, exist_ok=True)
    scratch_manifest = scratch / f"manifest-{args.stamp}.json"
    if scratch_manifest.exists():
        print(f"refused: manifest exists {scratch_manifest}")
        return 1

    def checkpoint() -> None:
        storage_report.safe_path(scratch_manifest)
        temporary = storage_report.safe_path(scratch_manifest.with_suffix('.json.tmp'))
        temporary.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        os.replace(temporary, scratch_manifest)

    checkpoint()
    for source, target in moves:
        storage_report.safe_path(source)
        storage_report.safe_path(target)
        target.absolute().relative_to(repo.absolute())
        digest = file_digest(source)
        size = source.stat().st_size if source.is_file() else storage_report.directory_size(source)
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            print(f"refused: target exists {target}")
            return 1
        try:
            os.rename(source, target)  # same-volume atomic move; never fall back to recursive copying
        except OSError as error:
            manifest['skipped'].append(f"{source.relative_to(repo)}: move refused ({type(error).__name__})")
            checkpoint()
            return 1
        manifest["moved"].append({
            "source": str(source.relative_to(repo)).replace("\\", "/"),
            "scratch_path": str(target.relative_to(repo)).replace("\\", "/"),
            "kind": "file" if digest else "dir",
            "bytes": size,
            "sha256": digest,
            "recover": f"move {target} back to {source}",
        })
        checkpoint()

    after = storage_report.measure(repo)
    print(f"moved {len(manifest['moved'])} entries to {scratch}")
    print(f"manifest: {scratch_manifest}")
    print(f"remaining drift: root={[x for x in after['out_of_layout'] if x.startswith('root')]} "
          f"dev={len(after['dev_strays'])} runs={len(after['runs_layout'])}")
    return 0 if not [x for x in after["out_of_layout"] if x.startswith("root")] else 1


if __name__ == "__main__":
    raise SystemExit(main())
