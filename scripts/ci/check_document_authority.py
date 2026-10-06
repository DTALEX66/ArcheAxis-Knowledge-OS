#!/usr/bin/env python3
"""Repository documentation/authority drift gate.

Four faults this fails on, each of which either happened in this repository or would silently
corrupt an audit:

1. **More than one file claiming to be the current ledger or pack.** The repository twice carried
   two documents that each said "only current"; a reader cannot resolve that, and the earlier round
   found `README`/`AGENTS`/index pointing at one entry while two other files claimed different ones.
2. **A root authority entry whose references do not resolve.** The root entry exists to be followed,
   so every path it names must exist.
3. **An input record whose recorded byte hash disagrees with the file on this host.** Provenance that
   cannot be recomputed is not provenance.
4. **A coverage matrix that silently drops an ID.** Every CAP/Q/F/I identifier the input scope names
   must appear, so a matrix cannot look complete by omission.

Non-zero on any fault, each named with its file and line. Missing inputs are printed as such rather
than skipped silently. This gate proves document structure, never product qualification.

Reused rather than duplicated: generated-file drift is already covered by
`scripts/contracts/generate_vocabulary.py --check`, `check_media_window_policy.py --check` and
`generate_capability_catalog.py --check`; link and supersession structure by
`tests/test_documentation_authority_index.py` and `tests/test_truth_authority_supersession.py`.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
AUTHORITY = REPO / "AUTHORITY.md"
INPUTS = REPO / "docs" / "current" / "AAOS-INPUT-SOURCES-20261006.json"
MATRIX = REPO / "docs" / "current" / "AAOS-COVERAGE-MATRIX-20261006.md"

# Documents that route a reader to the current record. A file repository history is *not* scanned:
# dated records and frozen copies legitimately describe their own era's pack, and flagging preserved
# history is how a guard becomes noise. The defect this catches is two live pointers disagreeing.
LIVE_ENTRY_DOCS = (
    "README.md",
    "AUTHORITY.md",
    "AGENTS.md",
    "docs/DOCUMENTATION_AUTHORITY_INDEX.md",
    "docs/truth/README.md",
    "docs/taskpacks/README.md",
)
CURRENTNESS = re.compile(r"(当前|现行|current|live)", re.IGNORECASE)
LEDGER_PATH = re.compile(r"(docs/current/[A-Za-z0-9._-]*LEDGER[A-Za-z0-9._-]*\.md)")
PACK_NAME = re.compile(r"(taskpack-[0-9a-z.\-]+)")
LIVE_LEDGER = "docs/current/AAOS01-Q00-Q15-LEDGER-FINAL-20261005.md"
# Taken from the current AGENTS.md, the top-ranked repository authority: the current user-approved
# execution pack is taskpack-1004-aaos01, and R6 is the *preceding* pack whose constraints and
# receipts are inherited. An earlier version of this gate assumed R6 was current, which is exactly
# the stale reading this check exists to prevent.
LIVE_PACK = "taskpack-1004-aaos01"
PRECEDING_PACKS = ("taskpack-0919-r6", "taskpack-0912-r5", "taskpack-0910-r3", "taskpack-0907", "taskpack-0906")
# A line that mentions a target while withdrawing it, or marking it preceding/historical, is a
# record of succession rather than a competing claim.
WITHDRAWN = re.compile(
    r"(不再|并非|不主张|作废|取代|superseded|no longer|not the only|preceding|previous|历史|继承|inherited|historical)")
# The two stale pointers repaired in this round; they must not regrow a conflicting target.
MUST_NOT_CLAIM = (
    "docs/taskpacks/README.md",
    "docs/truth/README.md",
)


def check_single_current() -> list[str]:
    """Every live entry document must point at one ledger and one active pack.

    Each claim is collected as (file, line, target) from lines that both name a target and speak of
    currentness, so a historical mention inside a live document is not mistaken for a claim.
    """
    problems: list[str] = []
    ledger_claims: list[tuple[str, int, str]] = []
    pack_claims: list[tuple[str, int, str]] = []
    for relative in LIVE_ENTRY_DOCS:
        path = REPO / relative
        if not path.is_file():
            problems.append(f"{relative}: live entry document is missing")
            continue
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if not CURRENTNESS.search(line):
                continue
            ledger_claims += [(relative, number, match) for match in LEDGER_PATH.findall(line)]
            pack_claims += [(relative, number, match) for match in PACK_NAME.findall(line)]

    for file, line, target in ledger_claims:
        if target != LIVE_LEDGER:
            problems.append(
                f"{file}:{line}: points at {target} as the current progress record, while the "
                f"agreed one is {LIVE_LEDGER}")
    found_ledgers = {target for _, _, target in ledger_claims}
    if len(found_ledgers) > 1:
        problems.append(
            "live entry documents name more than one current ledger: "
            + ", ".join(sorted(found_ledgers)))
    if not ledger_claims:
        problems.append(
            "no live entry document names the current progress record, so a reader cannot find it")

    for file, line, target in pack_claims:
        if target == LIVE_PACK or target in PRECEDING_PACKS:
            continue
        problems.append(
            f"{file}:{line}: points at {target} as the current pack, while the agreed one is "
            f"{LIVE_PACK}")
    named_packs = {target for _, _, target in pack_claims}
    if LIVE_PACK not in named_packs:
        problems.append(
            f"no live entry document names {LIVE_PACK} as the current pack, so a reader may follow "
            "a pack that AGENTS.md no longer approves")

    # The two files repaired this round must not route a reader back to a competing target.
    for relative in MUST_NOT_CLAIM:
        path = REPO / relative
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        for number, line in enumerate(text.splitlines(), start=1):
            if not CURRENTNESS.search(line) or WITHDRAWN.search(line):
                continue
            for target in LEDGER_PATH.findall(line) + PACK_NAME.findall(line):
                if target not in (LIVE_LEDGER, LIVE_PACK):
                    problems.append(
                        f"{relative}:{number}: routes to {target}, which conflicts with the agreed "
                        "current record")
    return problems

LINK = re.compile(r"\]\(([^)]+)\)")
CODE_PATH = re.compile(r"`((?:docs|scripts|tests|config|services|crates|frontend|apps)/[^`]+)`")


def python_files(root: Path, suffixes: tuple[str, ...] = (".md",)) -> list[Path]:
    """Markdown files in the repository that may carry a currentness claim.

    The ignored development root is skipped by *relative* position. Matching on absolute path parts
    would have excluded the entire repository on a host where the checkout itself sits under a
    `.project-local` directory, which is exactly the layout this worktree uses — the scan then found
    nothing and every entry looked as though it made no claim.
    """
    found: list[Path] = []
    for base in ("docs", "."):
        directory = REPO / base if base != "." else REPO
        if not directory.is_dir():
            continue
        for path in directory.rglob("*"):
            if not path.is_file() or path.suffix not in suffixes:
                continue
            relative = path.relative_to(REPO)
            if relative.parts and relative.parts[0] == ".project-local":
                continue
            found.append(path)
    return sorted(set(found))


def check_authority_references() -> list[str]:
    if not AUTHORITY.is_file():
        return [f"{AUTHORITY.relative_to(REPO)}: missing; the root entry is what everything else "
                "is navigated from"]
    text = AUTHORITY.read_text(encoding="utf-8")
    problems: list[str] = []
    targets = set(LINK.findall(text)) | set(CODE_PATH.findall(text))
    for target in sorted(targets):
        if target.startswith(("http://", "https://", "#", "mailto:")):
            continue
        cleaned = target.split("#", 1)[0].strip()
        if not cleaned or "<" in cleaned:
            continue
        if not (REPO / cleaned).exists():
            problems.append(f"AUTHORITY.md: references {cleaned}, which does not exist")
    return problems


def check_input_hashes() -> list[str]:
    if not INPUTS.is_file():
        return [f"{INPUTS.relative_to(REPO)}: missing"]
    document = json.loads(INPUTS.read_text(encoding="utf-8"))
    problems: list[str] = []
    checked = skipped_outside = missing = 0
    entries = list(document.get("inputs_read_this_round") or []) + list(
        document.get("appendix_sources") or [])
    for entry in entries:
        recorded = entry.get("byte_sha256")
        locator = str(entry.get("path_or_locator") or "")
        if not recorded or not locator:
            continue
        candidate = Path(locator)
        if not candidate.is_absolute():
            candidate = REPO / locator
        if not candidate.is_file():
            if candidate.is_absolute():
                skipped_outside += 1  # outside the repository: not this gate's evidence
            else:
                missing += 1
            continue
        actual = hashlib.sha256(candidate.read_bytes()).hexdigest()
        checked += 1
        if actual != recorded:
            problems.append(
                f"{locator}: recorded {recorded[:16]}… but this host has {actual[:16]}…")
    # A run that verified nothing must not read as a clean result.
    if checked == 0 and missing == 0:
        problems.append(
            f"{INPUTS.relative_to(REPO)}: no in-repository input hash was verifiable "
            f"({skipped_outside} locator(s) are outside the repository)")
    if missing:
        problems.append(f"{INPUTS.relative_to(REPO)}: {missing} recorded path(s) are not in the "
                        "repository and are not absolute, so they cannot be a locator")
    print(f"input hashes: verified {checked}, outside-repository {skipped_outside}")
    return problems


def check_coverage_matrix() -> list[str]:
    if not MATRIX.is_file():
        return [f"{MATRIX.relative_to(REPO)}: missing"]
    text = MATRIX.read_text(encoding="utf-8")
    problems: list[str] = []
    required = (
        [f"CAP-{n:04d}" for n in range(10, 170, 10)]
        + [f"Q{n:02d}" for n in range(16)]
        + [f"F{n:02d}" for n in range(15)]
        + [f"I{n}" for n in range(1, 7)]
    )
    for identifier in required:
        if not re.search(rf"(?<![A-Za-z0-9-]){re.escape(identifier)}(?![0-9])(?!0)", text):
            problems.append(f"{MATRIX.relative_to(REPO)}: {identifier} is not covered")
    return problems


def main() -> int:
    problems: list[str] = []
    problems += check_single_current()
    problems += check_authority_references()
    problems += check_input_hashes()
    problems += check_coverage_matrix()
    if problems:
        print("document authority drift:")
        for problem in problems:
            print(f"  {problem}")
        return 1
    print("document authority: single current record, root references resolve, "
          "input hashes match, coverage complete")
    return 0


if __name__ == "__main__":
    sys.exit(main())
