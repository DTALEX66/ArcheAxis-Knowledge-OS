"""Strict reference validation for audit records.

Why this module exists (FINDING 5): the audit tool this replaces took the last path
segment of a cited reference and ran ``rglob(tail)`` over a whole tree, so *any*
same-named file anywhere counted as resolved and an empty "missing" list printed as
"all references resolved". A basename match is not reference integrity: it can be
satisfied by an unrelated file that happens to share a name.

The rules implemented here:

1. a citation is resolved **exactly**, relative to the root it names -- no basename walk;
2. the target must exist and be a file;
3. when the record carries a hash or a commit, the target's identity is verified against
   it, from the bytes on disk;
4. a same-named file at a *different* path is never a substitute: it is reported as
   AMBIGUOUS and refused, with every candidate listed, rather than silently picked;
5. a historical citation stays resolvable-but-marked (HISTORICAL). It is never
   auto-satisfied, and a same-named substitute is still AMBIGUOUS;
6. the verdict classes stay distinct (PASS / UNRESOLVED / AMBIGUOUS / HASH_MISMATCH /
   HISTORICAL). Collapsing them is how the old tool turned "found nothing" into green.

Hash convention: ``sha256_raw`` is the SHA-256 of the file's bytes exactly as stored;
``sha256_lf_normalized`` is the SHA-256 of the text decoded as UTF-8 with CRLF collapsed
to LF, re-encoded as UTF-8. They are different values on purpose (Windows writers can
translate newlines) and are always named separately here.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Iterable, Mapping, Sequence

PASS = "PASS"
UNRESOLVED = "UNRESOLVED"
AMBIGUOUS = "AMBIGUOUS"
HASH_MISMATCH = "HASH_MISMATCH"
HISTORICAL = "HISTORICAL"

#: Distinct classes. ``SATISFIED`` is the only pair that lets a run go green.
VERDICT_CLASSES: tuple[str, ...] = (PASS, UNRESOLVED, AMBIGUOUS, HASH_MISMATCH, HISTORICAL)
SATISFIED: frozenset[str] = frozenset({PASS, HISTORICAL})

#: Directories never walked when looking for same-named candidates (diagnostics only).
SKIP_DIRS = frozenset({
    ".git", "node_modules", "__pycache__", ".pytest_cache", ".mypy_cache",
    "target", "dist", "build", ".venv", "venv", ".cargo", "registry", ".turbo",
})

_TRAILING_PUNCT = "，。、（）()〔〕[]{}<>`'\".;:;!！？? \t"


def sha256_raw(path: Path) -> str:
    """SHA-256 of the stored bytes, nothing else."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sha256_lf_normalized(path: Path) -> str:
    """SHA-256 of the decoded text with CRLF collapsed to LF, re-encoded as UTF-8."""
    text = path.read_bytes().decode("utf-8", errors="strict")
    return hashlib.sha256(text.replace("\r\n", "\n").encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class Root:
    """A named directory a citation may be resolved against."""

    name: str
    directory: Path
    marker: str = ""
    """The prefix citations use for this root ('' for the repository itself)."""

    def as_dict(self) -> dict:
        return {"name": self.name, "directory": str(self.directory), "marker": self.marker}


@dataclass(frozen=True)
class Reference:
    """One citation, parsed into an exact path under a stated root.

    ``relative`` is None when the citation is a bare basename or an absolute path:
    neither names a location inside a declared root, so neither is ever exactly
    resolvable (that is the defect this module exists to stop).
    """

    citation: str
    root: str
    relative: str | None
    expected_sha256: str | None = None
    commit: str | None = None
    historical: bool = False
    label: str = ""
    absolute: bool = False

    def exact(self, roots: Mapping[str, Path]) -> Path | None:
        if self.relative is None or self.absolute:
            return None
        base = roots.get(self.root)
        if base is None:
            return None
        candidate = base / PurePosixPath(self.relative)
        # A '..' traversal or an embedded drive letter must not be able to walk the
        # resolution out of the stated root -- that is how an absolute citation used to
        # read as "resolved" while bypassing every root check.
        try:
            resolved = candidate.resolve()
            resolved_root = Path(base).resolve()
        except OSError:
            return None
        if not resolved.is_relative_to(resolved_root):
            return None
        return resolved if resolved.is_file() else None


@dataclass(frozen=True)
class Verdict:
    """The outcome for one citation, with everything a reader needs to re-check it."""

    citation: str
    root: str
    relative: str | None
    verdict: str
    reason: str
    resolved_path: str | None = None
    candidates: tuple[str, ...] = ()
    recorded_sha256: str | None = None
    measured_sha256: str | None = None
    measured_sha256_lf: str | None = None
    commit: str | None = None
    historical: bool = False
    label: str = ""

    @property
    def satisfied(self) -> bool:
        return self.verdict in SATISFIED

    def as_dict(self) -> dict:
        out = {"citation": self.citation, "root": self.root, "relative": self.relative,
               "verdict": self.verdict, "reason": self.reason}
        for key in ("resolved_path", "candidates", "recorded_sha256", "measured_sha256",
                    "measured_sha256_lf", "commit", "historical", "label"):
            value = getattr(self, key)
            if value not in (None, (), False, ""):
                out[key] = list(value) if isinstance(value, tuple) else value
        return out


def _normalize(token: str) -> str:
    text = token.strip().strip("`").strip()
    text = text.rstrip(_TRAILING_PUNCT)
    text = text.replace("\\", "/")
    while text.startswith("./"):
        text = text[2:]
    return text


_ABSOLUTE_TOKEN = re.compile(r"^(?:[A-Za-z]:[\\/]|[\\/]{2}|[\\/])")


def parse_reference(token: str, roots: Sequence[Root], *, default_root: str | None = None,
                    expected_sha256: str | None = None, commit: str | None = None,
                    historical: bool = False, label: str = "") -> Reference:
    """Bind a citation to one root and an exact relative path *as written*.

    The root is chosen by the longest declared marker the citation starts with. A
    citation that matches no root and contains a separator is resolved against the
    default root exactly. A bare basename, or an absolute path, gets ``relative=None``.
    """
    text = _normalize(token)
    if not text:
        raise ValueError(f"empty citation: {token!r}")
    if _ABSOLUTE_TOKEN.match(text):
        fallback = default_root or (roots[0].name if roots else "")
        return Reference(text, fallback, None, expected_sha256, commit, historical, label,
                         absolute=True)
    best: Root | None = None
    for root in roots:
        marker = _normalize(root.marker) if root.marker else ""
        if not marker:
            continue
        if text == marker or text.startswith(marker + "/"):
            if best is None or len(marker) > len(_normalize(best.marker)):
                best = root
    if best is not None and best.marker:
        relative = text[len(_normalize(best.marker)):].lstrip("/")
        if not relative:
            raise ValueError(f"citation {token!r} names the root only")
        return Reference(text, best.name, relative, expected_sha256, commit, historical, label)
    if "/" in text:
        fallback = default_root or (roots[0].name if roots else "")
        return Reference(text, fallback, text, expected_sha256, commit, historical, label)
    fallback = default_root or (roots[0].name if roots else "")
    return Reference(text, fallback, None, expected_sha256, commit, historical, label)


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)


def _git_blob_id(path: Path) -> str | None:
    result = _git(path.parent if path.parent.exists() else Path("."),
                  "hash-object", "--", str(path))
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def _identity_check(ref: Reference, target: Path, repo: Path | None) -> tuple[str, str] | None:
    """Return (verdict, reason) when identity is claimed *and* fails; None when it holds."""
    if ref.expected_sha256:
        actual = sha256_raw(target)
        if actual != ref.expected_sha256.strip().lower():
            return (HASH_MISMATCH,
                    f"recorded sha256 {ref.expected_sha256} != raw-bytes sha256 {actual}")
    if ref.commit:
        if repo is None:
            return (UNRESOLVED, "commit identity cannot be checked: no repository was given")
        if _git(repo, "cat-file", "-e", f"{ref.commit}^{{commit}}").returncode != 0:
            return (UNRESOLVED, f"cited commit {ref.commit} does not resolve in this repository")
        try:
            tracked = target.relative_to(repo).as_posix()
        except ValueError:
            return (UNRESOLVED,
                    "commit identity cannot be checked: the target lies outside the repository")
        if _git(repo, "cat-file", "-e", f"{ref.commit}:{tracked}").returncode != 0:
            # The artifact is not tracked at that commit (e.g. it lives under the ignored
            # project-local root). Saying "mismatch" here would be a lie; so is calling it
            # resolved. Identity from the commit is simply not available.
            return (UNRESOLVED,
                    f"identity not verifiable: commit {ref.commit} tracks no path at {tracked}, "
                    "so the citation carries no commit-bound evidence for this artifact")
        want = _git(repo, "rev-parse", f"{ref.commit}:{tracked}")
        blob = _git_blob_id(target)
        if want.returncode != 0 or not blob:
            return (UNRESOLVED, "git could not hash either side of the identity check")
        if want.stdout.strip() != blob:
            return (HASH_MISMATCH,
                    f"git blob id at {ref.commit} is {want.stdout.strip()}, on-disk bytes "
                    f"hash to {blob}")
    return None


def _same_named_candidates(name: str, roots: Mapping[str, Path], limit: int = 20) -> list[str]:
    """Same-named files under the declared roots -- diagnostics only, never a match."""
    found: list[str] = []
    for root_name, base in roots.items():
        if not base.is_dir():
            continue
        for directory, dirnames, filenames in os.walk(base):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            if name in filenames:
                found.append(f"{root_name}:{Path(directory) / name}")
                if len(found) >= limit:
                    return found
    return found


def validate_reference(ref: Reference, roots: Mapping[str, Path], *,
                       repo: Path | None = None) -> Verdict:
    """Apply the strict rules to one citation. See the module docstring."""
    base = {
        "citation": ref.citation, "root": ref.root, "relative": ref.relative,
        "recorded_sha256": ref.expected_sha256, "commit": ref.commit,
        "historical": ref.historical, "label": ref.label,
    }
    target = ref.exact(roots)
    if target is not None:
        identity = _identity_check(ref, target, repo)
        measured = sha256_raw(target)
        try:
            measured_lf = sha256_lf_normalized(target)
        except Exception:  # not UTF-8 text: raw hash is all that exists
            measured_lf = None
        if identity is not None:
            verdict, reason = identity
            return Verdict(**base, verdict=verdict, reason=reason,
                           resolved_path=str(target), measured_sha256=measured,
                           measured_sha256_lf=measured_lf)
        if ref.historical:
            return Verdict(**base, verdict=HISTORICAL,
                           reason="resolved exactly and marked historical by the record; "
                                  "not counted as current evidence",
                           resolved_path=str(target), measured_sha256=measured,
                           measured_sha256_lf=measured_lf)
        return Verdict(**base, verdict=PASS, reason="exact path resolved and identity holds",
                       resolved_path=str(target), measured_sha256=measured,
                       measured_sha256_lf=measured_lf)

    name = PurePosixPath(ref.citation).name
    if ref.absolute:
        # A stat only: the record already names this path. The point is not to read it but
        # to say plainly that it sits outside every root this tool is allowed to vouch for.
        outside = Path(ref.citation)
        where = ("the bytes are on this host, but outside every declared root, so this tool "
                 "cannot vouch for the reference" if outside.exists() else
                 "and the path does not exist on this host either")
        return Verdict(**base, verdict=UNRESOLVED,
                       reason=f"citation is absolute, so it names no location inside a "
                              f"declared root; {where}",
                       candidates=tuple(_same_named_candidates(name, roots, limit=5)))
    candidates = tuple(_same_named_candidates(name, roots))
    if not candidates:
        return Verdict(**base, verdict=UNRESOLVED,
                       reason=("cited path does not exist and no same-named file exists under "
                               "the declared roots" if ref.relative is not None else
                               "citation is a bare basename with no directory, and nothing of "
                               "that name exists under the declared roots"))
    if ref.relative is None:
        return Verdict(**base, verdict=AMBIGUOUS,
                       reason=("citation names only a basename, so it asserts no location; "
                               f"{len(candidates)} same-named candidate(s) exist"),
                       candidates=candidates)
    return Verdict(**base, verdict=AMBIGUOUS,
                   reason=("cited path does not exist; same-named file(s) found only at other "
                           "paths, which are not the cited reference"),
                   candidates=candidates)


def validate_all(refs: Iterable[Reference], roots: Mapping[str, Path], *,
                 repo: Path | None = None) -> list[Verdict]:
    return [validate_reference(ref, roots, repo=repo) for ref in refs]


def summarise(verdicts: Sequence[Verdict]) -> dict[str, int]:
    """Per-class counts. Every class is reported even when empty, so a collapsed
    verdict cannot hide behind a missing row."""
    counts = {name: 0 for name in VERDICT_CLASSES}
    for verdict in verdicts:
        counts[verdict.verdict] = counts.get(verdict.verdict, 0) + 1
    counts["TOTAL"] = len(verdicts)
    return counts


def exit_code(verdicts: Sequence[Verdict]) -> int:
    """0 only when nothing is UNRESOLVED / AMBIGUOUS / HASH_MISMATCH."""
    return 0 if all(v.satisfied for v in verdicts) else 1


# --------------------------------------------------------------------------- records


@dataclass
class RecordFinding:
    """One hash field inside one record, checked against the bytes it names."""

    record: str
    field: str
    recorded: str
    verdict: str
    reason: str
    target: str | None = None
    measured_sha256: str | None = None
    measured_sha256_lf: str | None = None
    directory_files: tuple[str, ...] = ()
    recomputed: dict[str, str] = field(default_factory=dict)

    def as_dict(self) -> dict:
        out = {"record": self.record, "field": self.field, "recorded": self.recorded,
               "verdict": self.verdict, "reason": self.reason}
        for key, value in (("target", self.target), ("measured_sha256", self.measured_sha256),
                           ("measured_sha256_lf", self.measured_sha256_lf)):
            if value:
                out[key] = value
        if self.directory_files:
            out["directory_files"] = list(self.directory_files)
        if self.recomputed:
            out["recomputed_raw_bytes_sha256"] = self.recomputed
        return out


_HASH_FIELD = re.compile(r"^(?P<stem>.+_)?(sha256|sha_256)$")
_TARGET_FIELD = re.compile(r"^(?P<stem>.+_)?(file|path|target|artifact|log)$")


def _target_named_by_record(data: Mapping, stem: str, field: str) -> str | None:
    """The file a hash field is about, only if the record itself names it.

    Deliberately stem-matched: an earlier tool paired any ``*_sha256`` with any nearby
    filename, which is the basename mistake again. No stem, no target.
    """
    if _TARGET_FIELD.match(field):
        return None
    guesses = [f"{stem}_file", f"{stem}_path", f"{stem}_target", f"{stem}_log",
               f"{stem}_artifact"] if stem else []
    guesses += ["hashed_file", "hashed_path", "target_file"]
    for key in guesses:
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def audit_hash_fields(directory: Path, *, sibling_only: bool = True) -> list[RecordFinding]:
    """Check every ``*_sha256`` field in every JSON record of a directory.

    A hash field is satisfied only when the record names the file it hashes, that named
    file exists, and recomputing its raw bytes reproduces the recorded value. If the
    record names no file, the finding is UNRESOLVED with the directory's real contents
    listed -- the recorded value is then provably about nothing in hand, and no basename
    guess is allowed to promote it to PASS.
    """
    findings: list[RecordFinding] = []
    for record in sorted(directory.glob("*.json")):
        try:
            data = json.loads(record.read_bytes().decode("utf-8"))
        except Exception as error:  # a record that cannot be parsed cannot be trusted
            findings.append(RecordFinding(record.name, "<record>", "", UNRESOLVED,
                                          f"record does not parse as JSON: {error}"))
            continue
        if not isinstance(data, dict):
            continue
        siblings = tuple(sorted(p.name for p in directory.iterdir() if p.is_file()))
        files = {p.name: p for p in directory.iterdir() if p.is_file()}
        for field, value in sorted(data.items()):
            match = _HASH_FIELD.match(field)
            if not match or not isinstance(value, str) or not value.strip():
                continue
            recorded = value.strip().lower()
            stem = (match.group("stem") or "").rstrip("_")
            named = _target_named_by_record(data, stem, field)
            if named is None:
                recomputed = {name: sha256_raw(path) for name, path in sorted(files.items())}
                resolving = [name for name, digest in recomputed.items() if digest == recorded]
                findings.append(RecordFinding(
                    record.name, field, recorded,
                    HASH_MISMATCH if resolving else UNRESOLVED,
                    ("hash field names no file; recomputation resolves it to "
                     + ", ".join(resolving)) if resolving else
                    ("hash field names no file, so the value is tied to no named artifact; "
                     "recomputing every file in the directory reproduces it for none"),
                    target=None, directory_files=siblings,
                    recomputed=recomputed))
                continue
            target = (directory / named) if sibling_only else Path(named)
            if not target.is_file():
                findings.append(RecordFinding(
                    record.name, field, recorded, UNRESOLVED,
                    f"record names {named}, which does not exist next to the record",
                    directory_files=siblings))
                continue
            measured_raw = sha256_raw(target)
            try:
                measured_lf = sha256_lf_normalized(target)
            except Exception:
                measured_lf = None
            if measured_raw != recorded:
                findings.append(RecordFinding(
                    record.name, field, recorded, HASH_MISMATCH,
                    f"raw-bytes sha256 of {named} is {measured_raw}", target=named,
                    measured_sha256=measured_raw, measured_sha256_lf=measured_lf,
                    directory_files=siblings))
                continue
            findings.append(RecordFinding(
                record.name, field, recorded, PASS, f"{named} recomputes to the recorded value",
                target=named, measured_sha256=measured_raw, measured_sha256_lf=measured_lf,
                directory_files=siblings))
    return findings


# ------------------------------------------------------------------------- citation scan

_CITATION_TOKEN = re.compile(
    r"`([^`\n]{4,400}?)`"
)
_PATHISH = re.compile(r"([A-Za-z0-9_.\-]+/)+[A-Za-z0-9_.\-\u4e00-\u9fff]+|\b[\w.\-\u4e00-\u9fff]+\.(py|ts|tsx|json|md|rs|log|yaml|yml|txt|md)\b")


_NON_PATH_TOKEN = re.compile(
    r"^(?:codex|origin|upstream|refs|heads?|tags?|feature|hotfix|main|master|HEAD)\b"
    r"|^[A-Za-z0-9._-]+/[A-Za-z0-9._-]*$"
)
"""A backticked token that is a branch/ref name, not a path citation. Treating a branch
as a missing file would make the gate red for the wrong reason."""


def extract_citations(text: str) -> list[str]:
    """Backticked, path-like tokens in a record. Basenames are kept -- they must now fail."""
    out: list[str] = []
    for raw in _CITATION_TOKEN.findall(text):
        token = _normalize(raw)
        if not token:
            continue
        if token.startswith(("http://", "https://", "git@", "<")):
            continue
        if any(ch in token for ch in ("{", "}", "<", ">", "→", "|")):
            continue
        # A branch/ref name is not a path citation; checking it would turn the gate red
        # for the wrong reason. Paths that merely *look* like one are still checked when
        # they carry a file extension.
        if _NON_PATH_TOKEN.match(token) and not token.endswith(
                (".py", ".ts", ".tsx", ".json", ".md", ".rs", ".yaml", ".yml", ".txt", ".log")):
            continue
        if _PATHISH.fullmatch(token) or ("/" in token and "." in token):
            if token not in out:
                out.append(token)
    return out


def default_roots(repo: Path) -> list[Root]:
    """The two roots the audit tool has ever had: the repository and its project-local
    working root. Both are derived from the repository location, never hard-coded.

    A worktree run reaches the shared project-local evidence root with
    ``ARCHEAXIS_PROJECT_LOCAL`` instead of a machine path baked into the source.
    """
    configured = os.environ.get("ARCHEAXIS_PROJECT_LOCAL", "").strip()
    project_local = Path(configured) if configured else repo / ".project-local"
    return [Root("repo", repo, ""), Root("project_local", project_local, ".project-local")]


def root_map(roots: Sequence[Root]) -> dict[str, Path]:
    return {root.name: Path(root.directory) for root in roots}


def main(argv: Sequence[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--record", action="append", default=[],
                        help="record file whose backticked citations are validated")
    parser.add_argument("--scan-evidence", metavar="DIR",
                        action="append", default=[],
                        help="directory of JSON records whose *_sha256 fields are checked")
    parser.add_argument("--root", action="append", default=[], metavar="NAME=PATH",
                        help="declare a root; may repeat (default repo plus project_local)")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args(argv)

    repo = Path(__file__).resolve().parents[2]
    if args.root:
        roots = []
        for item in args.root:
            name, _, path = item.partition("=")
            roots.append(Root(name.strip(), Path(path.strip()), ""))
    else:
        roots = default_roots(repo)
    roots_map = root_map(roots)

    verdicts: list[Verdict] = []
    for record_path in args.record:
        path = Path(record_path)
        text = path.read_text(encoding="utf-8")
        for token in extract_citations(text):
            ref = parse_reference(token, roots, default_root=roots[0].name)
            verdicts.append(validate_reference(ref, roots_map, repo=repo))

    findings: list[RecordFinding] = []
    for directory in args.scan_evidence:
        findings.extend(audit_hash_fields(Path(directory)))

    payload = {
        "roots": [root.as_dict() for root in roots],
        "summary": summarise(verdicts),
        "verdicts": [v.as_dict() for v in verdicts],
        "record_findings": [f.as_dict() for f in findings],
        "record_summary": {c: sum(1 for f in findings if f.verdict == c) for c in VERDICT_CLASSES},
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        for verdict in verdicts:
            print(f"{verdict.verdict:13s} {verdict.citation} :: {verdict.reason}")
            for candidate in verdict.candidates[:5]:
                print(f"{'':13s}   candidate {candidate}")
        for finding in findings:
            print(f"{finding.verdict:13s} {finding.record}:{finding.field} :: {finding.reason}")
        print(json.dumps(payload["summary"], ensure_ascii=False))
        print(json.dumps(payload["record_summary"], ensure_ascii=False))
    bad = [v for v in verdicts if not v.satisfied]
    bad_findings = [f for f in findings if f.verdict not in SATISFIED]
    return 0 if not bad and not bad_findings else 1


if __name__ == "__main__":
    sys.exit(main())
