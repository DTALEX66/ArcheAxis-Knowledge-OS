"""Check current authority SHA claims without rewriting evidence identity.

The M0 overlay's explicit ``current local and remote main`` claim is a live
authority pointer and must match Git.  R6 ``subject_sha`` is evidence identity;
it is checked as a resolvable commit and is reported separately from the
record file's own latest commit.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Sequence


GitRunner = Callable[..., str]
SHA_RE = re.compile(r"^[0-9a-fA-F]{40}$")
CURRENT_MAIN_RE = re.compile(
    r"当前本地与远端\s+`main`\s*：\s*`([0-9a-fA-F]{40})`"
)


class DuplicateJsonMemberError(ValueError):
    """Raised when a JSON object contains the same member name more than once."""


def _reject_duplicate_json_members(pairs: list[tuple[str, object]]) -> dict[str, object]:
    payload: dict[str, object] = {}
    for key, value in pairs:
        if key in payload:
            raise DuplicateJsonMemberError(f"duplicate JSON object member: {key!r}")
        payload[key] = value
    return payload


@dataclass
class AuthorityShaReport:
    errors: list[str] = field(default_factory=list)
    current_head: str | None = None
    origin_main: str | None = None
    claimed_current_main: str | None = None
    evidence_subject_sha: str | None = None
    record_commit: str | None = None
    record_first_parent: str | None = None


def _git_from_subprocess(*args: str) -> str:
    return subprocess.check_output(["git", *args], text=True, encoding="utf-8").strip()


def _read_current_claim(path: Path, report: AuthorityShaReport) -> None:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        report.errors.append(f"cannot read authority overlay {path}: {exc}")
        return
    match = CURRENT_MAIN_RE.search(text)
    if match is None:
        report.errors.append(
            "authority overlay has no valid current main claim; "
            "historical subject SHA entries are not accepted as a replacement"
        )
        return
    report.claimed_current_main = match.group(1).lower()


def _read_state(path: Path, report: AuthorityShaReport) -> dict:
    try:
        payload = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_reject_duplicate_json_members,
        )
    except (OSError, json.JSONDecodeError, DuplicateJsonMemberError) as exc:
        report.errors.append(f"cannot read R6 state {path}: {exc}")
        return {}
    if not isinstance(payload, dict):
        report.errors.append("R6 state must be a JSON object")
        return {}
    subject = payload.get("subject_sha")
    if not isinstance(subject, str) or not SHA_RE.fullmatch(subject):
        report.errors.append("R6 state subject_sha must be a full 40-character commit SHA")
    else:
        report.evidence_subject_sha = subject.lower()
    return payload


def _run(git: GitRunner, report: AuthorityShaReport, *args: str) -> str | None:
    try:
        return git(*args).strip()
    except (OSError, subprocess.CalledProcessError, KeyError) as exc:
        report.errors.append(f"git {' '.join(args)} failed: {exc}")
        return None


def check_authority_sha_consistency(
    overlay_path: Path,
    state_path: Path,
    *,
    git: GitRunner = _git_from_subprocess,
) -> AuthorityShaReport:
    """Return a read-only consistency report for current authority records."""

    report = AuthorityShaReport()
    _read_current_claim(overlay_path, report)
    _read_state(state_path, report)

    report.current_head = _run(git, report, "rev-parse", "HEAD")
    report.origin_main = _run(git, report, "rev-parse", "origin/main")
    if report.current_head and not SHA_RE.fullmatch(report.current_head):
        report.errors.append("git HEAD is not a full commit SHA")
    if report.origin_main and not SHA_RE.fullmatch(report.origin_main):
        report.errors.append("git origin/main is not a full commit SHA")

    if report.current_head and report.origin_main:
        if report.current_head.lower() != report.origin_main.lower():
            report.errors.append(
                f"git HEAD differs from origin/main ({report.current_head} != {report.origin_main})"
            )

    if report.evidence_subject_sha:
        _run(git, report, "cat-file", "-e", f"{report.evidence_subject_sha}^{{commit}}")
    report.record_commit = _run(git, report, "log", "-1", "--format=%H", "--", str(overlay_path))
    if report.record_commit and not SHA_RE.fullmatch(report.record_commit):
        report.errors.append("authority record commit is not a full commit SHA")
    if report.record_commit and report.current_head:
        if report.record_commit.lower() != report.current_head.lower():
            report.errors.append(
                "authority record commit does not match git HEAD "
                f"({report.record_commit} != {report.current_head})"
            )
    if report.record_commit:
        parents = _run(git, report, "rev-list", "--parents", "-n", "1", report.record_commit)
        if parents:
            fields = parents.split()
            if fields[0].lower() != report.record_commit.lower():
                report.errors.append("git record parent query returned a different commit")
            elif len(fields) > 1:
                report.record_first_parent = fields[1].lower()

    if report.claimed_current_main:
        allowed = {value.lower() for value in (report.current_head, report.record_first_parent) if value}
        if report.claimed_current_main not in allowed:
            report.errors.append(
                "current main claim must match git HEAD or the authority record's first parent "
                f"({report.claimed_current_main} not in {sorted(allowed)})"
            )

    return report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--overlay",
        type=Path,
        default=Path("docs/current/M0-DIRECTION-OVERRIDE-20260920.md"),
    )
    parser.add_argument(
        "--state",
        type=Path,
        default=Path("docs/current/R6-STATE.json"),
    )
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args(argv)
    report = check_authority_sha_consistency(args.overlay, args.state)
    payload = {
        "ok": not report.errors,
        "errors": report.errors,
        "current_head": report.current_head,
        "origin_main": report.origin_main,
        "claimed_current_main": report.claimed_current_main,
        "evidence_subject_sha": report.evidence_subject_sha,
        "record_commit": report.record_commit,
        "record_first_parent": report.record_first_parent,
    }
    if args.as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print("PASS" if payload["ok"] else "FAIL")
        for error in report.errors:
            print(f"- {error}")
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
