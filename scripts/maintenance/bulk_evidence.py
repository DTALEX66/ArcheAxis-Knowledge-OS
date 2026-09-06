#!/usr/bin/env python3
"""Record and verify one project-local run as a machine-readable evidence receipt.

BULK-0907 P02: this is NOT a process launcher and NOT a shell proxy. It never
executes the ``argv`` it records. It consumes an existing ``scripts/runtime/dev.py``
run root (``artifacts/execution.json`` produced by the launcher) and validates file
hashes, exit-code honesty and output presence for exactly the inputs/outputs named
in a project-authored spec JSON. Receipts are written only under that run root's
``artifacts`` directory. A non-zero underlying exit is preserved and reported as
FAILED; a failed run cannot become PASS because a later aggregation command exited 0.

Structural problems (protected drive, UNC, parent-traversal escape, link/reparse,
invalid run root, malformed spec) fail with exit code 2 and perform ZERO writes.
Content problems (missing output, tampered hash, exit mismatch) write a FAILED
receipt and exit 1 so a real failure keeps a machine-readable record.

Usage:
    python bulk_evidence.py --run-root <dev-run-dir> --spec <spec.json> \
        [--receipt-name bulk-receipt]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _usage_error(message: str) -> int:
    print(f"bulk_evidence: {message}", file=sys.stderr)
    return 2


def _require_inside(path: Path, base: Path, label: str) -> Path:
    """Validate a path stays under ``base``; raise ValueError on drive/UNC/escape/link.

    A missing leaf is allowed (callers decide whether that is an error); missing or
    linked ancestors are rejected because resolution through them is not trustworthy.
    """
    raw = str(path)
    if re.match(r"^[A-Za-z]:", raw):
        if raw[:2].upper() == "E:":
            raise ValueError(f"{label} uses a protected E: drive")
    elif raw.replace("\\", "/").startswith(("//", "/")):
        raise ValueError(f"{label} uses a UNC or absolute root path")
    absolute = Path(os.path.abspath(raw))
    base_abs = Path(os.path.abspath(base))
    try:
        common = os.path.commonpath([str(base_abs), str(absolute)])
    except ValueError as exc:
        raise ValueError(f"{label} escapes its allowed base") from exc
    if common != str(base_abs):
        raise ValueError(f"{label} escapes its allowed base: {absolute}")
    ancestors = reversed(absolute.parents)
    for part in ancestors:
        try:
            info = part.lstat()
        except FileNotFoundError:
            raise ValueError(f"{label} has a missing ancestor: {part}") from None
        if stat.S_ISLNK(info.st_mode) or (
            getattr(info, "st_file_attributes", 0)
            & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
        ):
            raise ValueError(f"{label} ancestor is a link or reparse point: {part}")
    if absolute.exists():
        info = absolute.lstat()
        if stat.S_ISLNK(info.st_mode) or (
            getattr(info, "st_file_attributes", 0)
            & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
        ):
            raise ValueError(f"{label} is a link or reparse point: {absolute}")
    return absolute


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _check_hashes(refs: dict, base: Path, label: str) -> list[str]:
    """Return content problems (missing / tampered); structural paths raise ValueError."""
    problems: list[str] = []
    for rel, expected in refs.items():
        if not isinstance(rel, str) or not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected.lower()):
            problems.append(f"{label} entry has an invalid reference or expected hash: {rel!r}")
            continue
        resolved = _require_inside(base / rel, base, label)
        if not resolved.is_file():
            problems.append(f"{label} is missing: {rel}")
            continue
        actual = _sha256(resolved)
        if actual != expected.lower():
            problems.append(f"{label} hash mismatch (tampered): {rel} expected {expected} got {actual}")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-root", type=Path, required=True, help="existing dev.py run directory")
    parser.add_argument("--spec", type=Path, required=True, help="project-authored spec JSON")
    parser.add_argument("--receipt-name", default="bulk-receipt", help="receipt basename under run-root/artifacts")
    args = parser.parse_args()
    try:
        run_root = _require_inside(args.run_root, ROOT / ".project-local", "run root")
    except ValueError as exc:
        return _usage_error(str(exc))
    if not run_root.is_dir():
        return _usage_error("run root is not a directory; no writes performed")
    if not (run_root / "artifacts" / "execution.json").is_file():
        return _usage_error("run root has no artifacts/execution.json (not a dev.py run); no writes performed")
    try:
        execution = json.loads((run_root / "artifacts" / "execution.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return _usage_error(f"cannot read execution.json: {exc}")
    try:
        spec = json.loads(args.spec.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as exc:
        return _usage_error(f"cannot read spec: {exc}")
    if not isinstance(spec, dict):
        return _usage_error("spec must be a JSON object")
    argv = spec.get("argv")
    if not isinstance(argv, list) or not all(isinstance(item, str) for item in argv):
        return _usage_error("spec.argv must be a list of strings (documented only, never executed)")
    problems: list[str] = []
    repo_inputs = spec.get("repo_inputs") or {}
    run_outputs = spec.get("run_outputs") or {}
    if not isinstance(repo_inputs, dict) or not isinstance(run_outputs, dict):
        return _usage_error("spec.repo_inputs and spec.run_outputs must be objects")
    try:
        problems.extend(_check_hashes(repo_inputs, ROOT, "repo input"))
        problems.extend(_check_hashes(run_outputs, run_root, "run output"))
    except ValueError as exc:
        return _usage_error(str(exc))
    stdout_ref = None
    stdout_rel = spec.get("stdout_stderr")
    if stdout_rel is not None:
        if not isinstance(stdout_rel, str):
            return _usage_error("spec.stdout_stderr must be a run-relative string")
        try:
            log = _require_inside(run_root / stdout_rel, run_root, "stdout_stderr")
        except ValueError as exc:
            return _usage_error(str(exc))
        if not log.is_file():
            problems.append(f"stdout_stderr is missing: {stdout_rel}")
        else:
            stdout_ref = {"relpath": stdout_rel, "sha256": _sha256(log)}
    recorded_exit = execution.get("exit_code")
    if isinstance(recorded_exit, bool) or not isinstance(recorded_exit, int):
        problems.append(f"execution.json exit_code is not an integer: {recorded_exit!r}")
    expected_exit = spec.get("expected_exit_code")
    if expected_exit is not None:
        if not isinstance(expected_exit, int) or isinstance(expected_exit, bool):
            problems.append("spec.expected_exit_code must be an integer")
        elif recorded_exit != expected_exit:
            problems.append(f"exit mismatch: expected {expected_exit} got {recorded_exit}")
    if isinstance(recorded_exit, int) and recorded_exit != 0:
        problems.append(f"underlying run exited non-zero ({recorded_exit}); evidence must not be PASS")

    receipt = {
        "schema": "archeaxis.bulk-evidence-receipt/v1",
        "status": "PASS" if not problems else "FAILED",
        "reason": problems,
        "title": spec.get("title", ""),
        "argv": argv,
        "cwd": str(spec.get("cwd") or ROOT),
        "interpreter": spec.get("interpreter") or execution.get("python") or sys.executable,
        "engine_versions": spec.get("engine_versions") or {},
        "source_sha": execution.get("source_commit"),
        "source_tree": execution.get("source_tree"),
        "dirty": execution.get("dirty"),
        "started_at": execution.get("started_at"),
        "ended_at": execution.get("ended_at"),
        "exit_code": recorded_exit,
        "repo_input_sha256": dict(repo_inputs),
        "run_output_sha256": dict(run_outputs),
        "stdout_stderr": stdout_ref,
        "receipt_created_at": datetime.now(timezone.utc).isoformat(),
    }
    receipt_name = re.sub(r"[^A-Za-z0-9_.-]", "_", args.receipt_name)
    artifacts = run_root / "artifacts"
    if not artifacts.is_dir():
        return _usage_error("run root has no artifacts directory; no writes performed")
    destination = artifacts / f"{receipt_name}.json"
    destination.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"bulk_evidence receipt: {destination} status={receipt['status']}")
    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())
