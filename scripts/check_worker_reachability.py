#!/usr/bin/env python3
"""Worker reachability: every capability worker is routed, or exempted with a reason.

Twice in this session a worker turned out to exist in the repository with **no route
pointing at it** - an Office worker and, separately, a canvas/subtitle/HTML family - so
a capability the format matrix recorded as missing was in fact present but unreachable
through the job contract. Nothing in the tree could have noticed. This checker is that
notice.

Rules:

  * every `services/python-workers/**/*.py` that looks like a capability worker (it
    declares an ENGINE and an `extract` entry point) must be named by the transport's
    route table (`services/python-workers/transport/text_ndjson.py`);
  * a worker that genuinely is not a routed capability (it takes a URL, a model path, an
    output directory, or is an internal helper) must be listed in the reachability
    record with a reason, so the exemption is a decision rather than an oversight;
  * the record may not list a worker that no longer exists, and may not list one that is
    in fact routed - a stale exemption is how a gate quietly stops meaning anything;
  * transport helpers and package markers are ignored by name.

Exit code 1 with the unclassified workers named.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKERS_ROOT = ROOT / "services/python-workers"
TRANSPORT = WORKERS_ROOT / "transport/text_ndjson.py"
RECORD = ROOT / "docs/authority/taskpack-0910-r3/WORKER-REACHABILITY.json"
IGNORED_NAMES = {"__init__.py", "vocabulary.py"}
ENGINE_RE = re.compile(r'^ENGINE\s*=\s*"([^"]+)"', re.MULTILINE)
EXTRACT_RE = re.compile(r"^def extract\(", re.MULTILINE)
ROUTE_WORKER_RE = re.compile(r'"worker"\s*:\s*"([^"]+)"')


def capability_workers(root: Path = ROOT) -> dict[str, str]:
    """Worker module path -> engine id, for every file that looks like a capability."""
    base = root / "services/python-workers"
    found: dict[str, str] = {}
    for path in sorted(base.rglob("*.py")):
        if path.name in IGNORED_NAMES or "transport" in path.parts or "contracts" in path.parts:
            continue
        text = path.read_text(encoding="utf-8-sig", errors="replace")
        engine = ENGINE_RE.search(text)
        if engine and EXTRACT_RE.search(text):
            found[str(path.relative_to(root)).replace("\\", "/")] = engine.group(1)
    return found


def routed_workers(root: Path = ROOT) -> set[str]:
    transport = root / "services/python-workers/transport/text_ndjson.py"
    text = transport.read_text(encoding="utf-8-sig", errors="replace")
    return {worker for worker in ROUTE_WORKER_RE.findall(text)}


def check(root: Path = ROOT, record_path: Path = RECORD) -> tuple[list[str], dict]:
    failures: list[str] = []
    workers = capability_workers(root)
    routed = routed_workers(root)
    if not workers:
        failures.append("no capability workers were discovered; the discovery rule is wrong")
    try:
        record = json.loads((record_path if record_path.is_absolute() else root / record_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return [f"{record_path}: cannot read the reachability record: {error}"], {}

    exemptions = {entry.get("worker"): entry for entry in record.get("unrouted") or []}
    for worker, engine in sorted(workers.items()):
        if worker in routed:
            if worker in exemptions:
                failures.append(f"{worker} is routed and also exempted; a stale exemption hides a real gap")
            continue
        entry = exemptions.get(worker)
        if entry is None:
            failures.append(
                f"{worker} (engine {engine}) is not named by any transport route and has no recorded reason: "
                "an unreachable capability looks identical to a missing one"
            )
            continue
        if not str(entry.get("reason", "")).strip():
            failures.append(f"{worker} is exempted with no reason")
    for worker in sorted(exemptions):
        if worker not in workers:
            failures.append(f"{worker} is exempted but does not exist (stale record)")

    detail = {
        "workers": len(workers),
        "routed": len([worker for worker in workers if worker in routed]),
        "exempted": len(exemptions),
        "engines": sorted(workers.values()),
    }
    return failures, detail


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--record", type=Path, default=RECORD)
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)

    failures, detail = check(ROOT, args.record)
    if args.json:
        print(json.dumps({"passed": not failures, "failures": failures, **detail}, ensure_ascii=False, indent=2))
    elif failures:
        print("worker reachability check failed:")
        for item in failures:
            print(f"  - {item}")
    else:
        print(
            "worker reachability check passed: "
            f"{detail['workers']} capability workers, {detail['routed']} routed, "
            f"{detail['exempted']} exempted with a recorded reason"
        )
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
