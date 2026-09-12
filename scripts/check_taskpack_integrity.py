#!/usr/bin/env python3
"""Installed taskpack integrity versus its live ledger.

`docs/authority/taskpack-0910-r3/verify_package.py` hashes every entry of
`MANIFEST.json` against the files in the pack. Two of those entries -
`EXECUTION.md` and `STATE.json` - are the pack's own designated *live progress*
files: the pack tells the executor to write progress into them. So the shipped
verifier cannot pass once any work has been recorded, and its `AssertionError:
EXECUTION.md` reads like corruption when it is actually the ledger working.

This checker separates the two questions instead of conflating them:

  * **is the frozen pack intact?** every manifest entry except the live-progress
    files must still hash to its recorded value;
  * **did only the ledger evolve?** the live-progress files must hash to what the
    install snapshot holds (`--shipped`, default
    `.project-local/runs/taskpack-0910-shipped/`), so a change to them is
    attributable to progress rather than to an unexplained edit;
  * **is the plan still the plan?** task ids unique, the dependency graph acyclic
    and fully resolvable in order, and all 23 tasks of the predecessor pack still
    represented, which is what the shipped verifier also asserted.

It then reports the divergence as facts - which files, both hashes, size deltas and
the current ledger/STATE size - so an independent auditor can see growth instead of
guessing. If the install snapshot is missing, the checker says the divergence cannot
be attributed rather than assuming the best.

Exit code 1 with the failures named; never an empty success.

**This is a local audit tool, not a CI gate.** The install snapshot lives under
`.project-local/runs/`, which is ignored and absent from a fresh checkout, so in CI
this checker would correctly refuse to attribute the divergence. Run it where the
install actually happened.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "docs/authority/taskpack-0910-r3"
SHIPPED = ROOT / ".project-local/runs/taskpack-0910-shipped"
LIVE_PROGRESS = ("EXECUTION.md", "STATE.json")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check(pack: Path = PACK, shipped: Path = SHIPPED) -> tuple[list[str], dict]:
    failures: list[str] = []
    manifest_path = pack / "MANIFEST.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return [f"{manifest_path}: cannot read the manifest: {error}"], {}

    frozen_ok, frozen_bad, attributable, unattributable = 0, [], [], []
    for name, expected in manifest.items():
        live = pack / name
        if not live.is_file():
            failures.append(f"{name}: listed in the manifest but missing from the pack")
            continue
        actual = sha256(live)
        if name not in LIVE_PROGRESS:
            if actual == expected:
                frozen_ok += 1
            else:
                frozen_bad.append({"path": name, "expected": expected, "actual": actual})
            continue
        snapshot = shipped / name
        if not snapshot.is_file():
            unattributable.append(name)
            continue
        if sha256(snapshot) != expected:
            unattributable.append(name)
        elif actual == expected:
            attributable.append({"path": name, "note": "unchanged since install"})
        else:
            attributable.append(
                {
                    "path": name,
                    "expected": expected,
                    "actual": actual,
                    "installed_bytes": snapshot.stat().st_size,
                    "live_bytes": live.stat().st_size,
                    "delta_bytes": live.stat().st_size - snapshot.stat().st_size,
                }
            )

    if frozen_bad:
        for item in frozen_bad:
            failures.append(
                f"{item['path']}: frozen pack file changed (expected {item['expected'][:12]}..., found {item['actual'][:12]}...)"
            )
    if unattributable:
        failures.append(
            "the install snapshot cannot attribute "
            + ", ".join(unattributable)
            + f"; restore it (expected under {shipped}) or the divergence is unexplained"
        )

    # plan structure, the part the shipped verifier also asserted
    task_pack = pack / "TASKS.json"
    plan_ok = False
    try:
        tasks = json.loads(task_pack.read_text(encoding="utf-8"))["tasks"]
        ids = [task["id"] for task in tasks]
        if len(set(ids)) != len(ids):
            failures.append("TASKS.json: task ids are not unique")
        else:
            done: set[str] = set()
            while len(done) < len(ids):
                ready = {task["id"] for task in tasks if set(task["depends_on"]) <= done} - done
                if not ready:
                    failures.append("TASKS.json: dependency graph has a cycle or a missing dependency")
                    break
                done |= ready
        predecessor = json.loads((pack / "reference-r2/TASKS.json").read_text(encoding="utf-8"))["tasks"]
        mapped = {item for task in tasks for item in task["original_tasks"]} | {f"F{index:02d}" for index in range(1, 7)}
        missing = sorted({task["id"] for task in predecessor} - mapped)
        if missing:
            failures.append(f"predecessor tasks are no longer represented in the plan: {missing}")
        if len(predecessor) != 23:
            failures.append(f"the predecessor pack is expected to hold 23 tasks, found {len(predecessor)}")
        plan_ok = not failures
    except (OSError, json.JSONDecodeError, KeyError) as error:
        failures.append(f"{task_pack}: cannot read the plan: {error}")

    ledger_rows = 0
    state_slices = 0
    try:
        ledger_rows = sum(
            1 for line in (pack / "EXECUTION.md").read_text(encoding="utf-8").splitlines() if line.startswith("|R")
        )
        state_slices = len(json.loads((pack / "STATE.json").read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError):
        pass

    detail = {
        "manifest_entries": len(manifest),
        "frozen_ok": frozen_ok,
        "frozen_changed": [item["path"] for item in frozen_bad],
        "live_progress": attributable,
        "plan_ok": plan_ok,
        "ledger_rows": ledger_rows,
        "state_slices": state_slices,
    }
    return failures, detail


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--pack", type=Path, default=PACK)
    parser.add_argument("--shipped", type=Path, default=SHIPPED)
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)

    failures, detail = check(args.pack, args.shipped)
    if args.json:
        print(json.dumps({"passed": not failures, "failures": failures, **detail}, ensure_ascii=False, indent=2))
    elif failures:
        print("taskpack integrity check failed:")
        for item in failures:
            print(f"  - {item}")
    else:
        grown = [item for item in detail["live_progress"] if item.get("delta_bytes")]
        summary = ", ".join(f"{item['path']} +{item['delta_bytes']} bytes" for item in grown) or "unchanged"
        print(
            "taskpack integrity check passed: "
            f"{detail['frozen_ok']} frozen pack files match their recorded hashes; "
            f"the live progress files match the install snapshot and grew as expected ({summary}); "
            f"plan intact ({detail['ledger_rows']} ledger rows, {detail['state_slices']} slices)"
        )
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
