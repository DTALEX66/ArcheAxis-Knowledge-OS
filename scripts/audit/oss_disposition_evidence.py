#!/usr/bin/env python3
"""Check the open-source donor dispositions against what this repository actually carries.

`AAOS-OSS-DONOR-DISPOSITION-V2-20261002.json` records a verdict per donor, and its own
`not_done_here` says the verdict frame is not an installation. A verdict like `CURRENT` or `ADOPT`
therefore has to be checked, not believed: the question this answers is *which declared dependency,
lock entry, vendored tree or source import actually backs each row*, and which rows have none.

Read-only. It reports what it found and where; a row with no evidence is reported ABSENT rather
than assumed present, and a row whose declaration is present but whose capability is not wired is
reported as such rather than as an absorption.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DISPOSITION = REPO / "docs" / "current" / "AAOS-OSS-DONOR-DISPOSITION-V2-20261002.json"

# Where a dependency can be declared or a donor vendored. Lockfiles are evidence of resolution,
# manifests of declaration, and the vendored roots of a real copy.
MANIFESTS = [
    "pyproject.toml",
    "uv.lock",
    "requirements.txt",
    "frontend/package.json",
    "frontend/package-lock.json",
]
# A tool invoked by a pipeline is absorbed without appearing in any manifest: pip-audit and
# gitleaks are run by the CI workflow, not installed as project dependencies. Searching only
# manifests reported those two as unabsorbed while they were running in CI.
PIPELINE_GLOBS = [".github/workflows/*.yml", ".github/workflows/*.yaml", "scripts/ci/*"]
# A REST service is absorbed by writing a client, not by adding a package: the Crossref, DataCite,
# OpenAlex and Wikidata rows are first-party `urllib` clients. Without this scope they read as
# unabsorbed, which is the opposite of the truth.
SOURCE_ROOTS = ["shared", "services", "app", "crates", "frontend/src"]
VENDOR_ROOTS = ["Inspiration-Research", "vendor", "third_party", "packages", "shared"]

# Rows whose donor is a Rust crate, an OS tool or a REST service rather than a Python package: the
# name to look for differs from the row's display name, and the evidence lives somewhere else.
EVIDENCE_TERMS = {
    "C001": ["pdfjs-dist"],
    "C002": ["markitdown"],
    "C003": ["trafilatura"],
    "C004": ["pytesseract", "tesseract"],
    "C005": ["crawl4ai"],
    "C006": ["litellm"],
    "C007": ["langfuse"],
    "C008": ["sqlite-vec", "sqlite_vec", "vec0"],
    "C009": ["networkx"],
    "C010": ["loguru"],
    "C011": ["structlog"],
    "C012": ["apscheduler"],
    "C013": ["deeptutor"],
    "A005": ["faster-whisper", "faster_whisper"],
    "A008": ["silero", "vad"],
    "A013": ["jiwer"],
    "A014": ["rapidfuzz"],
    "A015": ["fsrs"],
    "A016": ["canvas"],
    "A018": ["crossref"],
    "A019": ["datacite"],
    "A020": ["openalex"],
    "A021": ["wikidata"],
    "A022": ["syft"],
    "A023": ["pip-audit", "pip_audit"],
    "A024": ["gitleaks"],
}

# The document's `rule` names this vocabulary and `verdict_definitions` defines exactly it. The
# rows below use a *different* set (`CURRENT`, `ADOPT`, `EVALUATE`, ...), which the document never
# defines. That is reported as a fact rather than resolved by guessing what the author meant: a
# disposition whose verdict is undefined cannot be checked against anything.
DEFINED_VERDICTS = {"REFERENCE", "ADAPTER", "ABSORB", "PROVIDER", "SIDECAR", "BENCHMARK", "REJECT"}


def _manifest_paths() -> list[Path]:
    paths = [REPO / relative for relative in MANIFESTS if (REPO / relative).is_file()]
    for glob in PIPELINE_GLOBS:
        paths.extend(sorted(REPO.glob(glob)))
    return [path for path in paths if path.is_file()]


def search_files(terms: list[str]) -> dict[str, list[str]]:
    """Lines naming each term, matched on whole words.

    A bare substring match is what made the first version of this check useless: `vad` matched
    inside unrelated package names, so donors with no declaration at all were reported as present.
    """
    paths = _manifest_paths()
    found: dict[str, list[str]] = {}
    for term in terms:
        pattern = re.compile(rf"(?<![A-Za-z0-9]){re.escape(term)}(?![A-Za-z0-9])", re.IGNORECASE)
        hits: list[str] = []
        for path in paths:
            try:
                text = path.read_text(encoding="utf-8", errors="surrogateescape")
            except OSError:
                continue
            for number, line in enumerate(text.splitlines(), start=1):
                if pattern.search(line):
                    hits.append(f"{path.relative_to(REPO).as_posix()}:{number}")
                    break
        found[term] = hits
    return found


def source_hits(terms: list[str]) -> dict[str, list[str]]:
    """Source files naming each term, so an absorption written by hand is still visible."""
    found: dict[str, list[str]] = {}
    for term in terms:
        pattern = re.compile(rf"(?<![A-Za-z0-9]){re.escape(term)}(?![A-Za-z0-9])", re.IGNORECASE)
        hits: list[str] = []
        for root_name in SOURCE_ROOTS:
            root = REPO / root_name
            if not root.is_dir():
                continue
            for path in sorted(root.rglob("*")):
                if not path.is_file() or path.suffix.lower() in {".png", ".jpg", ".ico", ".woff", ".woff2"}:
                    continue
                try:
                    text = path.read_text(encoding="utf-8", errors="surrogateescape")
                except OSError:
                    continue
                for number, line in enumerate(text.splitlines(), start=1):
                    if pattern.search(line):
                        hits.append(f"{path.relative_to(REPO).as_posix()}:{number}")
                        break
                if len(hits) >= 3:
                    break
            if len(hits) >= 3:
                break
        found[term] = hits
    return found


def vendor_hits(terms: list[str]) -> dict[str, list[str]]:
    found: dict[str, list[str]] = {}
    for term in terms:
        pattern = re.compile(re.escape(term), re.IGNORECASE)
        hits: list[str] = []
        for root_name in VENDOR_ROOTS:
            root = REPO / root_name
            if not root.is_dir():
                continue
            for entry in sorted(root.iterdir()):
                if pattern.search(entry.name):
                    hits.append(str(entry.relative_to(REPO)).replace("\\", "/"))
        found[term] = hits[:5]
    return found


def evidence_state(terms: dict[str, list[str]], vendored: dict[str, list[str]],
                   source: dict[str, list[str]]) -> str:
    """What the repository actually carries, independent of what the row's verdict claims."""
    declared = any(terms[t] for t in terms)
    copied = any(vendored[t] for t in vendored)
    written = any(source[t] for t in source)
    if declared and copied:
        return "DECLARED_AND_VENDORED"
    if declared:
        return "DECLARED"
    if copied:
        return "VENDORED_ONLY"
    if written:
        return "IMPLEMENTED_IN_SOURCE"
    return "NONE"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", type=Path, default=None, help="also write the per-row evidence here")
    args = parser.parse_args()

    document = json.loads(DISPOSITION.read_text(encoding="utf-8"))
    rows = []
    for item in document["supply_chain_47_as_archived"]:
        row_id = item["id"]
        terms = EVIDENCE_TERMS.get(row_id) or [item["name"].split("(")[0].split(" ")[0].lower()]
        terms = [term for term in terms if term]
        terms_found = search_files(terms)
        vendored = vendor_hits(terms)
        written = source_hits(terms)
        rows.append(
            {
                "id": row_id,
                "name": item["name"],
                "disposition": item["disposition"],
                "terms": terms,
                "evidence": {term: hits for term, hits in terms_found.items() if hits},
                "vendored": {term: hits for term, hits in vendored.items() if hits},
                "source": {term: hits for term, hits in written.items() if hits},
                "verdict_defined": item["disposition"] in DEFINED_VERDICTS,
                "evidence_state": evidence_state(terms_found, vendored, written),
            }
        )

    used = sorted({row["disposition"] for row in rows})
    undefined = [verdict for verdict in used if verdict not in DEFINED_VERDICTS]
    totals: dict[str, int] = {}
    for row in rows:
        totals[row["evidence_state"]] = totals.get(row["evidence_state"], 0) + 1
    print(f"donor rows: {len(rows)}   evidence: {json.dumps(totals, ensure_ascii=False)}")
    print(f"verdicts used by the rows ({len(used)}): {', '.join(used)}")
    print(f"verdicts the document defines ({len(DEFINED_VERDICTS)}): {', '.join(sorted(DEFINED_VERDICTS))}")
    print(f"used but undefined by the document ({len(undefined)}): {', '.join(undefined)}")
    for row in rows:
        if row["evidence_state"] in {"NONE", "VENDORED_ONLY"}:
            continue
        where = "; ".join(f"{term} -> {', '.join(hits)}" for term, hits in row["evidence"].items()) or "-"
        print(f"  {row['id']:5} {row['disposition']:13} {row['evidence_state']:22} {row['name'][:32]:34} {where[:100]}")
    print("\nrows with no installed or written artifact found:")
    for row in rows:
        if row["evidence_state"] == "NONE":
            note = "" if row["verdict_defined"] else "  (verdict also undefined by the document)"
            print(f"  {row['id']:5} {row['disposition']:13} {row['name']}  (looked for {row['terms']}){note}")
    if args.json:
        args.json.write_text(json.dumps({"rows": rows, "totals": totals}, ensure_ascii=False, indent=2),
                             encoding="utf-8")
        print(f"\nwrote {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
