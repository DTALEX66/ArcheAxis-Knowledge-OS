#!/usr/bin/env python3
"""R14/R16 evidence index: what an independent auditor can re-check, per slice.

`EXECUTION.md` and `STATE.json` remain the live record; this index adds no authority.
Its job is to be *checkable*, so `scripts/check_evidence_index.py` refuses it when:

  * a slice is missing, or its status disagrees with `STATE.json` (two files cannot
    contradict each other about what is done);
  * a claim rests only on a receipt under the ignored `.project-local/runs/` tree - a
    fresh checkout could not verify it, so every slice must cite at least one tracked
    artifact (a test, a source file or a document);
  * a cited tracked path does not exist, or a cited command names a script that is not
    tracked;
  * a slice records no limitation, because a slice without a stated limit is a slice
    whose boundary nobody wrote down;
  * either independent gate (R14, R16) is recorded as passed. Those gates are decided
    by an independent audit, never by this repository, so the index may only say TODO
    or BLOCKED_EXTERNAL for them.

Receipts are still cited, because an audit wants the logs; they are marked
`receipt` so their absence from a fresh clone is expected rather than a failure.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "docs/authority/taskpack-0910-r3/R14-EVIDENCE-INDEX.json"
STATE = ROOT / "docs/authority/taskpack-0910-r3/STATE.json"
SLICES = [f"R{index:02d}" for index in range(17)]
INDEPENDENT_GATES = ("R14", "R16")
PASS_WORDS = ("PASS", "COMPLETE", "DONE", "SIGNED", "APPROVED")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig", errors="replace")


def check(index_path: Path = INDEX, state_path: Path = STATE, root: Path = ROOT) -> tuple[list[str], dict]:
    failures: list[str] = []
    try:
        index = json.loads(_read(index_path))
    except (OSError, json.JSONDecodeError) as error:
        return [f"{index_path}: cannot read the index: {error}"], {}
    try:
        state = json.loads(_read(state_path))
    except (OSError, json.JSONDecodeError) as error:
        return [f"{state_path}: cannot read the state: {error}"], {}

    rows = {row.get("slice"): row for row in index.get("slices", [])}
    missing = [name for name in SLICES if name not in rows]
    if missing:
        failures.append(f"the index is missing slices: {', '.join(missing)}")

    for name in SLICES:
        row = rows.get(name)
        if row is None:
            continue
        expected = state.get(name, {}).get("status")
        if row.get("status") != expected:
            failures.append(
                f"{name}: the index says {row.get('status')!r} while STATE.json says {expected!r}"
            )
        if name in INDEPENDENT_GATES:
            status = str(row.get("status", "")).upper()
            if any(word in status for word in PASS_WORDS) or row.get("independent_audit_passed"):
                failures.append(
                    f"{name}: an independent gate may not be recorded as passed by this repository"
                )
            if not row.get("independent_auditor"):
                failures.append(f"{name}: the gate must name who is to decide it (independent_auditor)")

        evidence = row.get("evidence") or []
        if not evidence:
            failures.append(f"{name}: no evidence is cited")
        tracked = [item for item in evidence if item.get("kind") != "receipt"]
        if not tracked:
            failures.append(
                f"{name}: every cited artifact is an ignored local receipt, so a fresh checkout cannot verify it"
            )
        for item in evidence:
            path = str(item.get("path", ""))
            kind = item.get("kind")
            if kind not in ("tracked", "receipt"):
                failures.append(f"{name}: {path!r} must say kind tracked or receipt")
                continue
            target = root / path
            if kind == "tracked" and not target.exists():
                failures.append(f"{name}: cited tracked path {path} does not exist")
            if kind == "receipt" and not path.startswith(".project-local/"):
                failures.append(f"{name}: {path} is marked a receipt but is not under .project-local/")

        command = str(row.get("command", "")).strip()
        if not command:
            failures.append(f"{name}: no command is recorded, so nothing can be re-run")
        else:
            mentions = [token for token in command.replace("||", " ").split() if token.endswith((".py", ".bat", ".ps1", ".sh", ".rs"))]
            if not mentions:
                failures.append(f"{name}: the command names no script a reader could run: {command!r}")
            for token in mentions:
                candidate = token.strip('"').replace("\\", "/")
                if not (root / candidate).exists():
                    failures.append(f"{name}: the command names {candidate}, which does not exist")

        limitations = row.get("limitations") or []
        if not limitations or not any(str(item).strip() for item in limitations):
            failures.append(f"{name}: no limitation is recorded")

    if not index.get("not_claimed"):
        failures.append("the index must carry a not_claimed list: what this evidence does not show")

    detail = {
        "slices": len(rows),
        "tracked_evidence": sum(
            1 for row in rows.values() for item in (row.get("evidence") or []) if item.get("kind") == "tracked"
        ),
        "receipt_evidence": sum(
            1 for row in rows.values() for item in (row.get("evidence") or []) if item.get("kind") == "receipt"
        ),
    }
    return failures, detail


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--index", type=Path, default=INDEX)
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)

    failures, detail = check(args.index)
    if args.json:
        print(json.dumps({"passed": not failures, "failures": failures, **detail}, ensure_ascii=False, indent=2))
    elif failures:
        print("evidence index check failed:")
        for item in failures:
            print(f"  - {item}")
    else:
        print(
            "evidence index check passed: "
            f"{detail['slices']} slices, {detail['tracked_evidence']} tracked evidence pointers, "
            f"{detail['receipt_evidence']} receipts, every status agrees with STATE.json, "
            "no independent gate is self-signed and every slice states its limits"
        )
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
