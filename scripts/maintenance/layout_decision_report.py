"""Classify the out-of-layout entries from a storage report without changing anything.

The storage report flags entries that do not fit the documented layout, but it
deliberately refuses to delete them: each one needs a decision. This read-only tool
turns the latest report into a decision table - whether the entry is referenced by a
tracked file, whether it is protected or a generic name, whether it is a runs-layout
entry, whether it exists, and its size - so a later S01 pass can decide per item
instead of scanning the tree again.

Reference evidence is reported at two strengths. A path-qualified citation
(`.project-local/<name>` or `.project-local/runs/<name>`) is evidence on its own. A
bare name is only evidence when it is distinctive - at least ten characters and a
digit or a separator - because a short or generic token (for example `c`, `p`,
`dist`, `state`) matches ordinary text thousands of times and would otherwise mark an
unreferenced candidate as referenced. Both signals stay in the row so a decision can
see which one applied.

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


def shell_name(name: str) -> str:
    """The last path segment of a report entry name."""
    return name.rstrip("/").rsplit("/", 1)[-1]


def distinctive(name: str) -> bool:
    """Whether a bare token cannot plausibly be ordinary prose.

    Matches the rule the archive rounds already use for candidate names: long
    enough to be specific, and carrying a digit or a separator. A name such as
    `c`, `p`, `dist` or `state` is never counted from a bare token alone.
    """
    bare = shell_name(name)
    return len(bare) >= 10 and (
        any(character.isdigit() for character in bare)
        or "-" in bare
        or "_" in bare
    )


def path_token(kind: str, name: str) -> str:
    """The path-qualified spelling a tracked file would use to cite this entry."""
    if kind == "runs":
        return ".project-local/runs/" + shell_name(name)
    if kind == "root":
        return shell_name(name)
    return ".project-local/" + shell_name(name)


ERE_SPECIAL = frozenset("\\.^$|?*+()[]{}")


def ere_escape(text: str) -> str:
    """Escape only what a POSIX extended regular expression treats as special.

    `git grep -E` uses POSIX ERE, so a PCRE lookahead would quietly fail to match.
    A trailing character class is the portable boundary; escaping only the ERE
    metacharacters keeps separators such as `-` literal instead of relying on a
    GNU-extension escaped hyphen.
    """
    return "".join(("\\" + character) if character in ERE_SPECIAL else character for character in text)


def path_pattern(kind: str, name: str) -> str:
    """An ERE spelling of the path token that ends at the path segment.

    A fixed-string match on `.project-local/p` also hits `.project-local/proposals`,
    so the citation has to end at the segment: `/`, a quote, a backtick or the end
    of the line are all valid boundaries, a longer name is not.
    """
    token = ere_escape(path_token(kind, name))
    if kind == "root":
        return r"(^|[^A-Za-z0-9_.-])" + token + r"([^A-Za-z0-9_.-]|$)"
    return token + r"([^A-Za-z0-9_.-]|$)"


def strong_reference(*, path_hit: bool, bare_hit: bool, name: str) -> bool:
    """A path-qualified hit always counts; a bare hit only for a distinctive name."""
    return path_hit or (bare_hit and distinctive(name))



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


def grep_hit(arguments: list[str], token: str, repo: Path) -> bool:
    result = subprocess.run(
        ["git", "-C", str(repo), "grep", "-l", *arguments, token, "--", "."],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return bool(result.stdout)


def reference_evidence(kind: str, name: str, repo: Path) -> dict:
    """Both reference strengths for one entry, without collapsing them."""
    path_hit = grep_hit(["-E"], path_pattern(kind, name), repo)
    bare_hit = grep_hit(["--fixed-strings"], shell_name(name), repo)
    strong = strong_reference(path_hit=path_hit, bare_hit=bare_hit, name=name)
    if path_hit:
        note = "cited by path"
    elif strong:
        note = "cited by a distinctive bare name only"
    elif bare_hit:
        note = "bare token matches only as ordinary text; not evidence"
    else:
        note = "no tracked citation"
    return {
        "referenced": strong,
        "reference_path": path_hit,
        "reference_bare_name": bare_hit,
        "reference_note": note,
    }


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
        evidence = reference_evidence(kind, name, repo)
        has_ref = evidence["referenced"]
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
                "reference_path": evidence["reference_path"],
                "reference_bare_name": evidence["reference_bare_name"],
                "reference_note": evidence["reference_note"],
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
