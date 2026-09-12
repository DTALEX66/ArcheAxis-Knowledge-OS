#!/usr/bin/env python3
"""Format status matrix check (R15 / X12).

`docs/authority/taskpack-0910-r3/R15-FORMAT-STATUS.json` claims what each of the
sixteen carried-over format groups can actually do today. A claim like that is
worth nothing unless something refuses it when it drifts, so this checker verifies
every mechanical part of the matrix against the real tree:

  * all sixteen groups are still there, and `release_scope`, `formats` and
    `required_output` still match the 2026-09-07 record verbatim - the requirement
    cannot be quietly redefined to match what was built, and no group may be
    dropped from the matrix;
  * every status is one of complete/partial/custody_only, and the summary counts
    match the rows;
  * every route a row claims exists in the Core's `ROUTES` table
    (`crates/archeaxis-application/src/attempts.rs`) as the same
    kind/capability/media-type triple;
  * every worker route a row claims matches the transport's route table
    (`services/python-workers/transport/text_ndjson.py`), including the worker
    module path;
  * every evidence path exists, and `legacy_reference` paths are labelled as such
    rather than counting as implementation;
  * a `custody_only` row may not claim a route (that is what makes it custody
    only), and a `partial` or `complete` row must claim at least one Core route and
    at least one test path.

What this cannot check is whether the prose is *sufficient*; it checks that the
mechanical claims are not false. Semantic judgement stays with the independent
audit, which is told here exactly which row to look at.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MATRIX = ROOT / "docs/authority/taskpack-0910-r3/R15-FORMAT-STATUS.json"
CARRIED_FROM = ROOT / "docs/authority/taskpack-0907/FORMAT-COVERAGE.json"
CORE_ROUTES = ROOT / "crates/archeaxis-application/src/attempts.rs"
TRANSPORT_ROUTES = ROOT / "services/python-workers/transport/text_ndjson.py"

STATUSES = ("complete", "partial", "custody_only")
EXPECTED_IDS = [f"F{index:02d}" for index in range(1, 17)]
CORE_TRIPLE_RE = re.compile(r'\(\s*"([^"]+)"\s*,\s*"([^"]+)"\s*,\s*"([^"]+)"\s*,?\s*\)')


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig", errors="replace")


def core_route_triples() -> set[tuple[str, str, str]]:
    """Parse the Core ROUTES table: (kind, capability, media_type)."""
    source = _read(CORE_ROUTES)
    start = source.find("pub const ROUTES")
    if start < 0:
        return set()
    end = source.find("];", start)
    return {(kind, capability, media) for kind, capability, media in CORE_TRIPLE_RE.findall(source[start:end])}


def accepted_media_by_capability() -> dict[str, set[str]]:
    """Parse ROUTE_MEDIA_TYPES: the media types each capability's worker accepts.

    A kind maps to one capability and one default media type, while the capability
    accepts several (a .docx and a .xlsx both travel the office route). A matrix row
    therefore claims a (kind, capability, media type) triple, and that claim holds when
    the kind routes to that capability AND the capability accepts that media type.
    """
    source = _read(CORE_ROUTES)
    start = source.find("pub const ROUTE_MEDIA_TYPES")
    if start < 0:
        return {}
    end = source.find("\n];", start)
    block = source[start:end]
    accepted: dict[str, set[str]] = {}
    # each entry is ("capability", &[ "media/type", ... ]); the arrays span several
    # lines, so the body is taken by bracket counting rather than by a lazy regex
    for match in re.finditer(r'"([a-z][a-z.]*\.[a-z]+)"\s*,\s*&\[', block):
        body_start = match.end()
        depth = 1
        cursor = body_start
        while cursor < len(block) and depth:
            if block[cursor] == "[":
                depth += 1
            elif block[cursor] == "]":
                depth -= 1
            cursor += 1
        accepted[match.group(1)] = set(re.findall(r'"([^"]+)"', block[body_start : cursor - 1]))
    return accepted


def worker_route_map() -> dict[str, str]:
    """Parse the transport ROUTES table: capability -> worker module path."""
    source = _read(TRANSPORT_ROUTES)
    start = source.find("ROUTES = {")
    end = source.find("\n}", start)
    block = source[start:end] if start >= 0 else ""
    routes: dict[str, str] = {}
    for match in re.finditer(r'"([a-z][a-z.]*\.[a-z]+)"\s*:\s*\{(.*?)\n    \}', block, re.DOTALL):
        capability, body = match.group(1), match.group(2)
        worker = re.search(r'"worker"\s*:\s*"([^"]+)"', body)
        if worker:
            routes[capability] = worker.group(1)
    return routes


def check(matrix_path: Path = MATRIX, root: Path = ROOT) -> tuple[list[str], dict]:
    failures: list[str] = []
    try:
        matrix = json.loads(_read(matrix_path))
    except (OSError, json.JSONDecodeError) as error:
        return [f"{matrix_path}: cannot read the matrix: {error}"], {}

    carried = json.loads(_read(root / "docs/authority/taskpack-0907/FORMAT-COVERAGE.json"))
    required = {row["format_id"]: row for row in carried["formats"]}

    rows = matrix.get("formats", [])
    ids = [row.get("format_id") for row in rows]
    if ids != EXPECTED_IDS:
        failures.append(f"matrix ids are {ids}; the sixteen carried groups must all be present, in order")

    vocabulary = tuple(matrix.get("status_vocabulary", []))
    if vocabulary != STATUSES:
        failures.append(f"status vocabulary is {vocabulary}; expected {STATUSES}")

    routes = core_route_triples()
    accepted = accepted_media_by_capability()
    kind_to_capability = {kind: capability for kind, capability, _ in routes}
    workers = worker_route_map()
    if not routes:
        failures.append(f"{CORE_ROUTES}: could not parse the Core ROUTES table")
    if not accepted:
        failures.append(f"{CORE_ROUTES}: could not parse the ROUTE_MEDIA_TYPES table")
    if not workers:
        failures.append(f"{TRANSPORT_ROUTES}: could not parse the transport ROUTES table")

    counts = {status: 0 for status in STATUSES}
    for row in rows:
        row_id = row.get("format_id", "?")
        source = required.get(row_id)
        if source is None:
            failures.append(f"{row_id}: not present in the carried 2026-09-07 record")
            continue
        for field in ("release_scope", "formats", "required_output"):
            if row.get(field) != source.get(field):
                failures.append(
                    f"{row_id}: {field} was changed from the carried record "
                    f"({source.get(field)!r} -> {row.get(field)!r})"
                )

        status = row.get("status")
        if status not in STATUSES:
            failures.append(f"{row_id}: status {status!r} is not one of {STATUSES}")
            continue
        counts[status] += 1

        evidence = row.get("evidence") or {}
        for claimed in evidence.get("core_routes", []):
            triple = (claimed.get("kind"), claimed.get("capability"), claimed.get("media_type"))
            kind, capability, media = triple
            if triple in routes:
                continue
            # a row may claim a media type the route accepts even when it is not the
            # route's default: one kind, one capability, several accepted media types
            if kind_to_capability.get(kind) == capability and media in accepted.get(capability, set()):
                continue
            failures.append(f"{row_id}: claims Core route {triple} which is not in the ROUTES table")
        for claimed in evidence.get("worker_routes", []):
            capability, worker = claimed.get("capability"), claimed.get("worker")
            if workers.get(capability) != worker:
                failures.append(
                    f"{row_id}: claims capability {capability!r} is served by {worker!r}, "
                    f"but the transport serves it by {workers.get(capability)!r}"
                )
        for group in ("code", "tests", "legacy_reference"):
            for relative in evidence.get(group, []):
                if not (root / relative).exists():
                    failures.append(f"{row_id}: evidence path {relative} does not exist")

        has_route = bool(evidence.get("core_routes"))
        has_test = bool(evidence.get("tests"))
        if status == "custody_only" and has_route:
            failures.append(f"{row_id}: status is custody_only but it claims an extraction route")
        if status in ("partial", "complete") and not has_route:
            failures.append(f"{row_id}: status is {status} but no Core route is claimed")
        if status in ("partial", "complete") and not has_test:
            failures.append(f"{row_id}: status is {status} but no test path is given")
        if status in ("partial", "custody_only") and not (row.get("gap") or "").strip():
            failures.append(f"{row_id}: status is {status} so the gap must be stated, not left empty")
        if status == "complete" and (row.get("gap") or "").strip():
            failures.append(f"{row_id}: status is complete but a gap is still recorded")

    summary = matrix.get("coverage_summary") or {}
    expected_summary = {**counts, "total": len(rows)}
    for key, value in expected_summary.items():
        if summary.get(key) != value:
            failures.append(f"coverage_summary.{key} is {summary.get(key)} but the rows count {value}")

    detail = {
        "rows": len(rows),
        "counts": counts,
        "core_routes_parsed": len(routes),
        "worker_routes_parsed": len(workers),
        "matrix": str(matrix_path),
    }
    return failures, detail


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--matrix", type=Path, default=MATRIX)
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)

    failures, detail = check(args.matrix)
    if args.json:
        print(json.dumps({"passed": not failures, "failures": failures, **detail}, ensure_ascii=False, indent=2))
    elif failures:
        print("format status matrix check failed:")
        for item in failures:
            print(f"  - {item}")
    else:
        counts = detail["counts"]
        print(
            "format status matrix check passed: "
            f"{detail['rows']} groups carried, {counts['complete']} complete, "
            f"{counts['partial']} partial, {counts['custody_only']} custody only; "
            f"every claimed route exists in the Core and transport tables "
            f"({detail['core_routes_parsed']} core routes, {detail['worker_routes_parsed']} worker routes parsed)"
        )
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
