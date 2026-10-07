"""Measure the repository's footprint per ownership class and flag anything outside the layout.

Why this exists: the ignored development root grew to tens of gigabytes and acquired directories
nobody had agreed to (`rt-before-*` snapshots, duplicate candidate trees, per-build tool dirs). Size
alone is not the problem — unbounded *unclassified* size is, because it hides which paths are
expendable cache and which are cited evidence.

The layout this asserts is the one the repository already documents:

* tracked source        crates/ services/ frontend/ src-tauri/ apps/ scripts/ config/ docs/ tests/ packages/
* ignored dev outputs   .project-local/{build,runs,task-runtime,candidates,recovery,mig,cache}
* local runtime data    data/ (git-ignored, a convenience copy, never a source of truth)
* deployment surface    a Green tree outside this repository (written only by an audited deploy)

Anything else at the repository root, or any unexpected top-level entry inside `.project-local`, is
reported as OUT-OF-LAYOUT rather than silently measured. Run with `--json <path>` to write the
report; the exit code is non-zero when something is out of layout.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

# Which ignored top-level entries are sanctioned. Everything else at the root is drift.
ALLOWED_IGNORED = {".git", ".github", ".worklab", ".project-local", ".project", ".codex.example",
                   ".cargo", ".ruff_cache", ".pytest_cache", ".venv", ".hermes", ".codex", ".dsh",
                   # documented local runtime state: a convenience copy, never a source of truth
                   "data"}
DEV_ALLOWED = {"build", "runs", "task-runtime", "candidates", "recovery", "mig", "cache",
               "a3-python-input", "worktrees", "legacy-scratch",
               # named by a tracked document, so it stays; sanctioned rather than re-flagged forever
               "tmp"}
# Budgets are ceilings for review, not delete triggers: exceeding one means the class needs a
# decision, and a class is only ever pruned with an audited path list and a preservation ref.
DEV_BUDGET_GB = {"build": 22.0, "task-runtime": 12.0, "candidates": 4.0, "runs": 2.0, "recovery": 4.0}
# Donor/probe trees are named by number in the clean-up records (a3 = donor, a10 = restore target),
# and `rt`/`rt-before-*` are cited by hand-off notes. They are a class, not drift.
DEV_ALLOWED_PATTERN = __import__("re").compile(r"^(a\d+(-.*)?|rt(-.*)?|legacy-scratch.*)$")


def dev_allowed(name: str) -> bool:
    return name in DEV_ALLOWED or bool(DEV_ALLOWED_PATTERN.match(name))


def directory_size(path: Path) -> int:
    total = 0
    stack = [path]
    while stack:
        current = stack.pop()
        try:
            with __import__("os").scandir(current) as entries:
                for entry in entries:
                    if entry.is_file(follow_symlinks=False):
                        total += entry.stat(follow_symlinks=False).st_size
                    elif entry.is_dir(follow_symlinks=False):
                        stack.append(Path(entry.path))
        except OSError:
            continue
    return total


def protected_bytes(directory: Path) -> int:
    """Bytes inside *directory* that a documented rule puts out of reach of this report.

    The compile caches are that case: `dev.py` is explicit that no historical cache is moved or
    removed, so counting them against a budget would only ever produce a permanent false alarm.
    They are still measured and shown - the point is to see them, not to schedule their deletion.
    """
    total = 0
    try:
        children = sorted(directory.iterdir())
    except OSError:
        return 0
    for child in children:
        if not child.is_dir():
            continue
        name = child.name
        if name.startswith("cargo"):  # <root>/cargo, <root>/cargo-gnu
            total += directory_size(child)
        elif name not in {".git"} and (child / "cargo").is_dir():  # <identity>/cargo
            total += directory_size(child / "cargo")
    return total


def _git_root_names() -> set[str]:
    """Top-level names Git itself tracks — the authoritative expectation for the repository root.

    A hand-written allowlist flagged `.gitignore`, `.editorconfig` and every other tracked
    configuration file as drift, which is worse than useless: a checker that cries wolf gets ignored.
    Git already knows what belongs here, so the contract is asked of Git and only the *ignored* side
    needs a declared set.
    """
    import subprocess

    names: set[str] = set()
    try:
        # Paths are decoded as UTF-8: this repository tracks non-ASCII names, and the platform
        # default codec raises on their bytes, which turned the whole report into a crash instead
        # of a measurement. `surrogateescape` keeps an undecodable name visible rather than fatal.
        listing = subprocess.run(
            ["git", "ls-files", "-z"],
            cwd=REPO,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="surrogateescape",
            check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return names
    if listing.stdout is None:
        return names
    for entry in listing.stdout.split("\0"):
        if entry:
            names.add(entry.split("/", 1)[0])
    return names


def measure() -> dict:
    out_of_layout: list[str] = []
    tracked = _git_root_names()
    root_entries = []
    for entry in sorted(REPO.iterdir()):
        name = entry.name
        if name in tracked:
            if entry.is_dir():
                root_entries.append({"name": name + "/", "bytes": directory_size(entry), "tracked": True})
            continue
        if name in ALLOWED_IGNORED:
            continue
        out_of_layout.append(f"root: {name}/" if entry.is_dir() else f"root: {name}")

    dev = REPO / ".project-local"
    dev_classes, dev_strays = [], []
    if dev.is_dir():
        for entry in sorted(dev.iterdir()):
            name = entry.name
            if not dev_allowed(name):
                dev_strays.append(entry)
                out_of_layout.append(f".project-local: {name}/" if entry.is_dir() else f".project-local: {name}")
                continue
            size = directory_size(entry)
            # Compile caches are exempt from the budget rather than silently over it. `dev.py`
            # states the rule - "Do not move or remove any historical cache" - so a class that is
            # mostly that cache cannot be brought under a ceiling by deleting it, and a ceiling that
            # is knowingly exceeded is noise. Only the rest of the class is budgeted.
            protected = protected_bytes(entry) if entry.is_dir() else 0
            budget = DEV_BUDGET_GB.get(name) or DEV_BUDGET_GB.get(name.split("-")[0])
            dev_classes.append({
                "name": name + "/" if entry.is_dir() else name,
                "bytes": size,
                "gb": round(size / 1024 ** 3, 2),
                "protected_bytes": protected,
                "budgeted_bytes": size - protected,
                "budget_gb": budget,
                "over_budget": bool(budget and size - protected > budget * 1024 ** 3),
            })
    return {
        "repository": str(REPO),
        "root": root_entries,
        "ignored_root": sorted(ALLOWED_IGNORED),
        "dev_root": dev_classes,
        "dev_strays": [str(path.relative_to(REPO)).replace("\\", "/") for path in dev_strays],
        "out_of_layout": out_of_layout,
    }


def print_report(report: dict) -> None:
    print(f"repository {report['repository']}")
    print("root classes:")
    for entry in sorted(report["root"], key=lambda item: -item["bytes"]):
        print(f"  {entry['bytes'] / 1024 ** 3:8.2f} GB  {entry['name']}")
    print(".project-local classes (budget in GB; compile caches shown but not budgeted):")
    for entry in sorted(report["dev_root"], key=lambda item: -item["bytes"]):
        flag = f"  OVER budget {entry['budget_gb']}" if entry["over_budget"] else ""
        budget = f"{entry['budget_gb']}" if entry["budget_gb"] else "-"
        protected = entry.get("protected_bytes") or 0
        held = f"  ({protected / 1024 ** 3:.2f} GB of it is a cache dev.py forbids removing)" if protected else ""
        print(f"  {entry['gb']:8.2f} GB  {entry['name']:<24} budget {budget}{flag}{held}")
    if report["out_of_layout"]:
        print("OUT-OF-LAYOUT (needs a decision, not a silent delete):")
        for item in report["out_of_layout"]:
            print(f"  - {item}")
    else:
        print("layout: every entry is inside the documented set")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", default=None)
    args = parser.parse_args()
    report = measure()
    print_report(report)
    if args.json:
        Path(args.json).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 1 if report["out_of_layout"] else 0


if __name__ == "__main__":
    sys.exit(main())
