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
import shutil
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


def worktree_roots(repo: Path) -> list[Path]:
    """Every checkout of this repository, because a citation may live on another branch."""
    import subprocess

    roots = [repo]
    listing = subprocess.run(["git", "-C", str(repo), "worktree", "list", "--porcelain"],
                             capture_output=True, text=True, encoding="utf-8", errors="replace")
    for line in (listing.stdout or "").splitlines():
        if line.startswith("worktree "):
            path = Path(line[len("worktree "):].strip())
            if path.is_dir() and path != repo:
                roots.append(path)
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
    for root in worktree_roots(repo):
        try:
            found = subprocess.run(["git", "grep", "-l", "-F", needle],
                                   cwd=root, capture_output=True, text=True)
        except OSError:
            return True
        if found.returncode == 0 and found.stdout.strip():
            return True
    return False


def plan_moves(repo: Path, scratch: Path) -> tuple[list[tuple[Path, Path]], list[str]]:
    report = storage_report.measure(repo)
    moves: list[tuple[Path, Path]] = []
    skipped: list[str] = []
    for name in report["dev_strays"]:
        source = repo / name
        if not source.exists():
            continue
        relative = name
        if referenced_exactly(relative, repo):
            skipped.append(f"{relative}: referenced by a tracked file")
            continue
        moves.append((source, scratch / "project-local" / name.split("/", 1)[1]))
    for name in [item for item in report["out_of_layout"] if item.startswith("root:")]:
        relative = name[len("root: "):].rstrip("/")
        source = repo / relative
        if not source.exists():
            continue
        if relative == "data":
            skipped.append("data/ is sanctioned local runtime state")
            continue
        if referenced_exactly(relative, repo):
            skipped.append(f"{relative}: referenced by a tracked file")
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
    repo = Path(args.repo).resolve() if args.repo else REPO
    scratch = repo / ".project-local" / f"legacy-scratch-{args.stamp}"

    moves, skipped = plan_moves(repo, scratch)
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
    for source, target in moves:
        digest = file_digest(source)
        size = source.stat().st_size if source.is_file() else storage_report.directory_size(source)
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            print(f"refused: target exists {target}")
            return 1
        shutil.move(str(source), str(target))
        manifest["moved"].append({
            "source": str(source.relative_to(repo)).replace("\\", "/"),
            "scratch_path": str(target.relative_to(repo)).replace("\\", "/"),
            "kind": "file" if digest else "dir",
            "bytes": size,
            "sha256": digest,
            "recover": f"move {target} back to {source}",
        })
    scratch_manifest = scratch / f"manifest-{args.stamp}.json"
    scratch_manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    after = storage_report.measure(repo)
    print(f"moved {len(manifest['moved'])} entries to {scratch}")
    print(f"manifest: {scratch_manifest}")
    print(f"remaining drift: root={[x for x in after['out_of_layout'] if x.startswith('root')]} "
          f"dev={len(after['dev_strays'])} runs={len(after['runs_layout'])}")
    return 0 if not [x for x in after["out_of_layout"] if x.startswith("root")] else 1


if __name__ == "__main__":
    raise SystemExit(main())
