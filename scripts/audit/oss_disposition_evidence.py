#!/usr/bin/env python3
"""Check the open-source donor dispositions against what this repository actually carries.

`AAOS-OSS-DONOR-DISPOSITION-V2-20261002.json` records a verdict per donor, and its own
`not_done_here` says the verdict frame is not an installation. A verdict like `CURRENT` or `ADOPT`
therefore has to be checked, not believed: the question this answers is *which declared dependency,
lock entry, vendored tree or source import actually backs each row*, and which rows have none.

Read-only. It reports what it found and where; a row with no evidence is reported ABSENT rather
than assumed present, and a row whose declaration is present but whose capability is not wired is
reported as such rather than as an absorption.

Three evidence classes, kept apart because they answer different questions:

* `DECLARED` / `DECLARED_AND_VENDORED` / `VENDORED_ONLY` — a manifest, a lock entry, a pipeline
  invocation, or a real vendored directory.
* `IMPLEMENTED_IN_SOURCE` — first-party code names the capability in an identifier and the file
  carrying it does *not* mark itself unavailable.
* `STUB_IN_SOURCE` — first-party code names it, but only in files that register it as
  unavailable-honest (a `MissingDependency` stub). "Something names this" is not "this works".
* `MENTIONED_IN_SOURCE` — the name appears only in prose, docstrings or string literals. A domain
  list entry (`developer.mozilla.org`) is a reference, not an implementation.
"""

from __future__ import annotations

import argparse
import ast
import io
import json
import re
import tokenize
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
# `shared/` used to be listed here, which made any first-party module whose *filename* contained a
# A vendor root holds copies, not this repository's own code.
# `shared/models` is a vendor root because it holds the vendored upstream model copy itself
# (shared/models/magika/{model.onnx,config.min.json,LICENSE}); it contains no first-party module,
# so crediting a directory name there cannot turn this repository's own code into a "copy".
VENDOR_ROOTS = ["Inspiration-Research", "vendor", "third_party", "packages", "shared/models"]
SKIP_DIRS = {"__pycache__", "node_modules", ".git", "target", "dist", "build", ".project-local",
             "generated"}
TEXT_SUFFIXES = {".py", ".rs", ".ts", ".tsx", ".js", ".jsx", ".toml", ".yaml", ".yml", ".json",
                 ".md", ".txt", ".cfg", ".ini"}
# Only a programming language names a capability in an identifier. A word in a README or a JSON
# fixture is a mention, and treating those as code made prose read as implementation.
CODE_SUFFIXES = {".py", ".rs", ".ts", ".tsx", ".js", ".jsx"}
# Floors and ceilings are deliberately wide: an unavailable-honest registry states the limitation in
# its module docstring and its classes a few lines later.
STUB_WINDOW = 20

# A file that registers a capability as unavailable-honest names it without providing it. The four
# real REST clients carry none of these markers; the OCR/ASR/VAD registries carry several.
STUB_MARKER = re.compile(r"unavailable|MissingDependency|not installed|placeholder", re.IGNORECASE)

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
    # Two name corrections, in opposite directions, both found by reading the repository rather
    # than the row. `apache` is a licence word that appears in a frontend lockfile and in several
    # docstrings, which credited a Tika sidecar that exists nowhere here; the donor's own name is
    # Tika. And Readability's identifier is `readabilipy`, which IS declared and used, while the
    # term `mozilla` only ever matched documentation URLs - so that row understated the truth.
    "A010": ["tika"],
    "A011": ["readabilipy"],
}

# The document's `rule` names this vocabulary and `verdict_definitions` defines exactly it. The
# rows below use a *different* set (`CURRENT`, `ADOPT`, `EVALUATE`, ...), which the document never
# defines. That is reported as a fact rather than resolved by guessing what the author meant: a
# disposition whose verdict is undefined cannot be checked against anything.
DEFINED_VERDICTS = {"REFERENCE", "ADAPTER", "ABSORB", "PROVIDER", "SIDECAR", "BENCHMARK", "REJECT"}

_WORD_SPLIT = re.compile(r"[^A-Za-z0-9]+")
_CAMEL_SPLIT = re.compile(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")
_IDENTIFIER = re.compile(r"[A-Za-z_$][A-Za-z0-9_$]*")


def _components(name: str) -> set[str]:
    """`CrossrefClient` -> {'crossrefclient', 'crossref', 'client'}.

    Whole-word matching is why the earlier version could not see the four REST clients it was
    supposed to find: the term is `crossref`, the identifier is `CrossrefClient`, and no word
    boundary separates them.
    """
    parts = {name}
    for piece in _WORD_SPLIT.split(name):
        if piece:
            parts.add(piece)
            parts.update(_CAMEL_SPLIT.split(piece))
    return {part.casefold() for part in parts if part}


def _manifest_paths() -> list[Path]:
    paths = [REPO / relative for relative in MANIFESTS if (REPO / relative).is_file()]
    for glob in PIPELINE_GLOBS:
        paths.extend(sorted(REPO.glob(glob)))
    return [path for path in paths if path.is_file()]


def search_files(terms: list[str]) -> dict[str, list[str]]:
    """Lines naming each term, matched on whole words or on `-`/`_` boundaries."""
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


def _source_files():
    for root_name in SOURCE_ROOTS:
        root = REPO / root_name
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            # Only parts *below* the repository root may disqualify a file: this checkout can sit
            # under a `.project-local/` path, so an absolute-path check would skip everything.
            if any(part in SKIP_DIRS for part in path.relative_to(REPO).parts):
                continue
            if path.suffix.casefold() not in TEXT_SUFFIXES:
                continue
            yield path


def _scan(path: Path) -> tuple[dict[str, int], set[int], list[int], list[str]]:
    """(identifier -> first line, prose lines, unavailability-marker lines, file lines)."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return {}, set(), [], []
    lines = text.splitlines()
    stub_lines = [number for number, line in enumerate(lines, start=1) if STUB_MARKER.search(line)]
    identifiers: dict[str, int] = {}
    prose: set[int] = set()
    if path.suffix.casefold() not in CODE_SUFFIXES:
        return {}, set(range(1, len(lines) + 1)), stub_lines, lines
    if path.suffix == ".py":
        try:
            tree = ast.parse(text)
        except SyntaxError:
            return {}, set(), stub_lines, lines
        for node in ast.walk(tree):
            if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                body = getattr(node, "body", [])
                if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
                        and isinstance(body[0].value.value, str):
                    first = body[0].value
                    prose.update(range(first.lineno, (first.end_lineno or first.lineno) + 1))
        try:
            for token in tokenize.generate_tokens(io.StringIO(text).readline):
                if token.type == tokenize.NAME and token.start[0] not in prose:
                    identifiers.setdefault(token.string.casefold(), token.start[0])
                elif token.type == tokenize.COMMENT:
                    prose.add(token.start[0])
        except (tokenize.TokenError, IndentationError):
            pass
        return identifiers, prose, stub_lines, lines
    for number, line in enumerate(lines, start=1):
        stripped = line.strip()
        if stripped.startswith(("#", "//", "/*", "*", "<!--")):
            prose.add(number)
            continue
        for match in _IDENTIFIER.finditer(line):
            identifiers.setdefault(match.group(0).casefold(), number)
    return identifiers, prose, stub_lines, lines


def _names_term(term: str, identifier: str) -> bool:
    """Does `identifier` name `term`?

    Component matching alone is not enough: `DataCiteClient` splits into `Data`/`Cite`/`Client`, so
    the donor written as one word (`datacite`) never appears as a component. A name that begins with
    the term does count — which is how `CrossrefClient`, `OpenAlexClient`, `WikidataClient` and
    `DataCiteClient` are all found.
    """
    wanted = re.sub(r"[^A-Za-z0-9]", "", term).casefold()
    if not wanted:
        return False
    if identifier.casefold().startswith(wanted):
        return True
    return wanted in _components(identifier)


_SCANNED: list[tuple[Path, dict[str, int], set[int], bool]] | None = None


def _scanned():
    global _SCANNED
    if _SCANNED is None:
        _SCANNED = [(path, *(_scan(path))) for path in _source_files()]
    return _SCANNED


def source_hits(terms: list[str]) -> tuple[dict[str, list[str]], dict[str, list[str]],
                                          dict[str, list[str]]]:
    """(code hits, stub-marked code hits, mentions) each with a `path:line` locator.

    An identifier says the repository names the capability in code; a line that only *contains* the
    term — a docstring, a comment, a string literal such as a domain list — is a mention.
    """
    code: dict[str, list[str]] = {}
    stub: dict[str, list[str]] = {}
    mention: dict[str, list[str]] = {}
    patterns = {term: re.compile(rf"(?<![A-Za-z0-9]){re.escape(term)}(?![A-Za-z0-9])", re.IGNORECASE)
                for term in terms}
    for path, identifiers, prose, stub_lines, lines in _scanned():
        relative = path.relative_to(REPO).as_posix()
        for term in terms:
            line = next((identifiers[name] for name in identifiers if _names_term(term, name)), None)
            if line is not None:
                near = any(abs(marker - line) <= STUB_WINDOW for marker in stub_lines)
                (stub if near else code).setdefault(term, []).append(f"{relative}:{line}")
                continue
            for number, raw in enumerate(lines, start=1):
                if patterns[term].search(raw):
                    mention.setdefault(term, []).append(f"{relative}:{number}")
                    break
    return ({t: hits[:3] for t, hits in code.items()},
            {t: hits[:3] for t, hits in stub.items()},
            {t: hits[:3] for t, hits in mention.items()})


def vendor_hits(terms: list[str]) -> dict[str, list[str]]:
    """A vendored copy is a directory that exists under a vendor root."""
    found: dict[str, list[str]] = {}
    for term in terms:
        pattern = re.compile(re.escape(term), re.IGNORECASE)
        hits: list[str] = []
        for root_name in VENDOR_ROOTS:
            root = REPO / root_name
            if not root.is_dir():
                continue
            for entry in sorted(root.iterdir()):
                if entry.is_dir() and pattern.search(entry.name) and any(entry.rglob("*")):
                    hits.append(entry.relative_to(REPO).as_posix())
        found[term] = hits[:5]
    return found


def evidence_state(terms: dict[str, list[str]], vendored: dict[str, list[str]],
                   code: dict[str, list[str]], stub: dict[str, list[str]],
                   mention: dict[str, list[str]]) -> str:
    """What the repository actually carries, independent of what the row's verdict claims."""
    declared = any(terms[t] for t in terms)
    copied = any(vendored[t] for t in vendored)
    written = any(code[t] for t in code)
    stubbed = any(stub[t] for t in stub)
    referenced = any(mention[t] for t in mention)
    if declared and copied:
        return "DECLARED_AND_VENDORED"
    if declared:
        return "DECLARED"
    if copied:
        return "VENDORED_ONLY"
    if written:
        return "IMPLEMENTED_IN_SOURCE"
    if stubbed:
        return "STUB_IN_SOURCE"
    if referenced:
        return "MENTIONED_IN_SOURCE"
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
        code, stub, mention = source_hits(terms)
        rows.append(
            {
                "id": row_id,
                "name": item["name"],
                "disposition": item["disposition"],
                "terms": terms,
                "evidence": {term: hits for term, hits in terms_found.items() if hits},
                "vendored": {term: hits for term, hits in vendored.items() if hits},
                "source": {term: hits for term, hits in code.items() if hits},
                "stub_source": {term: hits for term, hits in stub.items() if hits},
                "mentions": {term: hits for term, hits in mention.items() if hits},
                "verdict_defined": item["disposition"] in DEFINED_VERDICTS,
                "evidence_state": evidence_state(terms_found, vendored, code, stub, mention),
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
        if not row["evidence"] and row["source"]:
            where = "; ".join(f"{term} -> {', '.join(hits)}" for term, hits in row["source"].items())
        if not row["evidence"] and not row["source"] and row["stub_source"]:
            where = "stub: " + "; ".join(f"{term} -> {', '.join(hits)}"
                                         for term, hits in row["stub_source"].items())
        if not row["evidence"] and not row["source"] and not row["stub_source"] and row["mentions"]:
            where = "mention: " + "; ".join(f"{term} -> {', '.join(hits)}"
                                            for term, hits in row["mentions"].items())
        print(f"  {row['id']:5} {row['disposition']:13} {row['evidence_state']:22} "
              f"{row['name'][:32]:34} {where[:100]}")
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
