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
import json
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import storage_report  # noqa: E402  (same directory, same contract)

REPO = storage_report.REPO
SCRATCH = REPO / ".project-local" / "legacy-scratch-20261006"


def file_digest(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def referenced_exactly(relative: str) -> bool:
    """Whether any tracked document, receipt or test names this exact path.

    Substring matching is not enough and cost a full restore: `.project-local/a10` is a documented
    restore target and `.project-local/rt` is cited by hand-off notes, while a loose
    `.project-local/rust-ws-12.log` is named by nothing. The question is whether the path itself is
    pointed at, so the path itself is what gets searched.
    """
    needle = relative.replace("\\", "/")
    try:
        found = subprocess.run(["git", "grep", "-l", "-F", needle],
                               cwd=REPO, capture_output=True, text=True)
    except OSError:
        return True
    return found.returncode == 0 and bool(found.stdout.strip())


def plan_moves() -> tuple[list[tuple[Path, Path]], list[str]]:
    report = storage_report.measure()
    moves: list[tuple[Path, Path]] = []
    skipped: list[str] = []
    for name in report["dev_strays"]:
        source = REPO / name
        if not source.exists():
            continue
        relative = name
        if referenced_exactly(relative):
            skipped.append(f"{relative}: referenced by a tracked file")
            continue
        moves.append((source, SCRATCH / "project-local" / name.split("/", 1)[1]))
    for name in [item for item in report["out_of_layout"] if item.startswith("root:")]:
        relative = name[len("root: "):].rstrip("/")
        source = REPO / relative
        if not source.exists():
            continue
        if relative == "data":
            skipped.append("data/ is sanctioned local runtime state")
            continue
        if referenced_exactly(relative):
            skipped.append(f"{relative}: referenced by a tracked file")
            continue
        moves.append((source, SCRATCH / "repo-root" / relative))
    return moves, skipped


def main() -> int:
    moves, skipped = plan_moves()
    manifest = {
        "schema": "archeaxis/layout-scratch/v1",
        "scratch": str(SCRATCH),
        "moved": [],
        "skipped": skipped,
        "note": "restore by moving each source back to the repository root; nothing was deleted",
    }
    SCRATCH.mkdir(parents=True, exist_ok=True)
    for source, target in moves:
        digest = file_digest(source)
        size = source.stat().st_size if source.is_file() else storage_report.directory_size(source)
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            print(f"refused: target exists {target}")
            return 1
        shutil.move(str(source), str(target))
        manifest["moved"].append({
            "source": str(source.relative_to(REPO)).replace("\\", "/"),
            "scratch_path": str(target.relative_to(REPO)).replace("\\", "/"),
            "kind": "file" if digest else "dir",
            "bytes": size,
            "sha256": digest,
            "recover": f"move {target} back to {source}",
        })
    scratch_manifest = SCRATCH / "manifest.json"
    scratch_manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    after = storage_report.measure()
    print(f"moved {len(manifest['moved'])} entries to {SCRATCH}")
    print(f"manifest: {scratch_manifest}")
    print(f"remaining drift: root={[x for x in after['out_of_layout'] if x.startswith('root')]} dev={len(after['dev_strays'])}")
    return 0 if not [x for x in after["out_of_layout"] if x.startswith("root")] else 1


if __name__ == "__main__":
    raise SystemExit(main())
