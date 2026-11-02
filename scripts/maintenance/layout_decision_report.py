"""Classify the out-of-layout entries from a storage report without changing anything.

The storage report flags entries that do not fit the documented layout, but it
deliberately refuses to delete them: each one needs a decision. This read-only tool
turns the latest report into a decision table - whether the entry is referenced by a
tracked file, whether it is protected or a generic name, whether it is a runs-layout
entry, whether it exists, and its size - so a later S01 pass can decide per item
instead of scanning the tree again.

It never deletes, moves or writes inside the measured tree. It only reads the report
and, optionally, writes the table to a named JSON file.

Usage:
  python -B scripts/maintenance/layout_decision_report.py \
      --report .project-local/runs/<run>/storage-observation.json \
      [--json-out <table.json>]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

# Names that are ambiguous, private, historical or otherwise not safe to decide with
# a name alone. The report keeps them as decisions for the Owner/S01 pass.
PROTECTED = {
    ".screenshots", "account-preferences", "appdata", "acceptance", "backups", "tools",
    "inputs", "staging", "dist", "c", "g", "n", "wt", "probe", "restored",
    "test-fallback-run", "proposals", "audits", "audit-tools", "ui-audit",
    "inspect", "consolidation-ci", "cargo-home-a04", "dotnet-home",
}
GENERIC = {".screenshots", ".tmp", "artifacts", "reports", "tmp", "temp", "cache", "logs"}


def classify(
    *,
    kind: str,
    name: str,
    exists: bool,
    files: int,
    referenced: bool,
    run_layout: bool,
) -> str:
    """Classify one entry. Pure so a decision table can be tested without disk."""
    bare = name.rstrip("/").rsplit("/", 1)[-1]
    if not exists:
        return "MISSING"
    if run_layout:
        return "RUNS_LAYOUT"
    if files == 0:
        return "EMPTY"
    if referenced:
        return "REFERENCED"
    if bare in PROTECTED or bare in GENERIC:
        return "PROTECTED_OR_GENERIC"
    if kind == "root":
        return "ROOT_STRAY"
    return "UNREFERENCED_CANDIDATE"


def referenced(name: str, repo: Path) -> bool:
    for token in (name, ".project-local/" + name):
        result = subprocess.run(
            ["git", "-C", str(repo), "grep", "-l", "--fixed-strings", token, "--", "."],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        if result.stdout:
            return True
    return False


def measure(path: Path) -> tuple[int, int]:
    if not path.exists():
        return 0, 0
    if path.is_file():
        return path.stat().st_size, 1
    size = files = 0
    for entry in path.rglob("*"):
        if entry.is_file():
            size += entry.stat().st_size
            files += 1
    return size, files


def _name_of(entry: str) -> tuple[str, str]:
    kind, _, rest = entry.partition(": ")
    name = rest.split(" ")[0].rstrip("/")
    return kind, name


def resolve_path(repo: Path, kind: str, name: str) -> Path:
    """Resolve a report entry to a disk path for the three kind prefixes it uses."""
    if kind == "root":
        return repo / name
    if kind == "runs":
        return repo / ".project-local" / "runs" / name
    return repo / ".project-local" / name


def build_table(report: dict, repo: Path = REPO) -> list[dict]:
    rows = []
    for entry in report.get("out_of_layout", []):
        kind, name = _name_of(entry)
        path = resolve_path(repo, kind, name)
        unreadable = ""
        try:
            size, files = measure(path)
        except OSError as error:
            size, files = 0, 0
            unreadable = type(error).__name__
        run_layout = kind == "runs"
        has_ref = referenced(name, repo)
        classification = (
            "UNREADABLE"
            if unreadable
            else classify(
                kind=kind,
                name=name,
                exists=path.exists(),
                files=files,
                referenced=has_ref,
                run_layout=run_layout,
            )
        )
        rows.append(
            {
                "entry": entry,
                "kind": kind,
                "name": name,
                "exists": path.exists(),
                "files": files,
                "bytes": size,
                "referenced": has_ref,
                "class": classification,
                "unreadable": unreadable,
            }
        )
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--json-out", type=Path, default=None)
    parser.add_argument("--repo", type=Path, default=REPO)
    args = parser.parse_args(argv)

    if not args.report.is_file():
        print(f"storage report not found: {args.report}", file=sys.stderr)
        return 2
    report = json.loads(args.report.read_text(encoding="utf-8"))
    rows = build_table(report, args.repo)
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["class"]] = counts.get(row["class"], 0) + 1
    payload = {
        "schema": "aaos.layout-decision-table/v1",
        "source_report": str(args.report),
        "entries": len(rows),
        "counts": dict(sorted(counts.items())),
        "bytes": sum(row["bytes"] for row in rows),
        "rows": rows,
    }
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
