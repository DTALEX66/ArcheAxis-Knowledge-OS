"""The numbers the documents state must match what the tree contains.

The contract, the runbook and the ledger all quote counts, and a count that has drifted is worse
than no count: a reader uses it to decide whether they are looking at the whole picture. This
compares each quoted figure with the thing it describes, read from the source.

It also checks the two internal consistencies that are easy to break by hand: the ledger's counts
must agree with the disposition document it points at, and that document's stated evidence counts
must agree with the entries it lists. A key that is not in the source CSV, or that belongs to a
lane this task does not own, is reported too - the disposition is only meaningful for the keys it
was written for.

The audit that produced this found no drift.
"""

from __future__ import annotations

import csv
import importlib.util
import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CONTRACT = REPO / "docs/current/AAOS-PRODUCTION-HTTP-CONTRACT-20261001.md"
RUNBOOK = REPO / "docs/current/AAOS-BACKEND-ACCEPTANCE-RUNBOOK-20261001.md"
LEDGER = REPO / "docs/current/R6-STATE.json"
DISPOSITION = REPO / "docs/current/AAOS-BACKEND-KEY-DISPOSITION-20261001.json"
CSV = REPO / "docs/current/AAOS-ALL-TASKS-DISPOSITION-20261001.csv"
OWNED_LANES = {"BACKEND_FRONTEND_LOOP", "OWNER_GATE"}


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def tree_facts() -> dict[str, int]:
    matrix = load("matrix_for_consistency", REPO / "scripts/probes/staged_format_matrix_smoke.py")
    stager = load("stager_for_consistency", REPO / "scripts/release/stage_backend_runtime.py")
    contract = CONTRACT.read_text(encoding="utf-8")
    return {
        "golden_cases": len(matrix.GOLDEN_MATRIX),
        "real_cases": len(matrix.MATERIAL_ROUTES),
        # §6 says "30 routes (projection + the 4 runtime routes)"; route tables are the source.
        "declared_routes": len(stager.ROUTE_SCRIPTS),
        "inventory_pairs": len(re.findall(r"^\|\s*(?:\d+|R\d+)\s*\|", contract, re.M)),
    }


def router_mounts() -> tuple[int, int, int]:
    """Count unconditional projection, optional manual receipt and runtime mounts.

    A mount with GET and POST is one mount and two production method/path pairs.
    The conditional manual receipt is counted separately and excluded in production.
    """
    lib = (REPO / "crates/archeaxis-api/src/lib.rs").read_text(encoding="utf-8")
    runtime = (REPO / "crates/archeaxis-api/src/runtime/mod.rs").read_text(encoding="utf-8")
    marker = "let routes = if manual_receipts"
    projections = lib[lib.index("pub fn projections(") : lib.index(marker)]
    conditional = lib[lib.index(marker) : lib.index(marker) + 600]
    return (
        len(re.findall(r"\.route\s*\(", projections)),
        len(re.findall(r"\.route\s*\(", conditional)),
        len(re.findall(r"\.route\s*\(", runtime)),
    )


def test_the_contracts_route_counts_match_the_source():
    facts = tree_facts()
    contract = CONTRACT.read_text(encoding="utf-8")
    pairs = re.search(r"## 3\. Route inventory \((\d+) pairs", contract)
    routes = re.search(r"\| \*\*with\*\* `text_worker` \| (\d+) addresses", contract)
    assert pairs, "§3's heading no longer states a pair count; the claim cannot be checked"
    assert routes, "§6's table no longer states a route count"
    assert int(pairs.group(1)) == facts["inventory_pairs"], (
        f"§3 states {pairs.group(1)} pairs, the inventory table has {facts['inventory_pairs']}")
    assert int(routes.group(1)) == facts["inventory_pairs"], (
        f"§6 states {routes.group(1)} routes, the inventory table has {facts['inventory_pairs']}")


def test_the_launch_shape_split_adds_up():
    """Production method/path pairs differ from route mounts and omit manual receipts."""
    projections, conditional, runtime = router_mounts()
    inventory = tree_facts()["inventory_pairs"]
    assert projections == 38, f"unconditional projection mounts changed: {projections}"
    assert conditional == 1, f"conditional manual receipt mounts changed: {conditional}"
    assert runtime == 20, f"runtime mounts changed: {runtime}"
    lib = (REPO / "crates/archeaxis-api/src/lib.rs").read_text(encoding="utf-8")
    projection_builder = lib[lib.index("pub fn projections("):lib.index("let routes = if manual_receipts")]
    runtime_source = (REPO / "crates/archeaxis-api/src/runtime/mod.rs").read_text(encoding="utf-8")
    runtime_builder = runtime_source[runtime_source.index("pub fn router("):runtime_source.index(".merge(projections)")]
    parser = load("route_parser_for_shapes", REPO / "tests/maintenance/test_contract_route_inventory.py")

    def pairs(builder):
        entries = []
        for match in re.finditer(r"\.route\s*\(", builder):
            args = parser.balanced_call(builder, match.end() - 1)
            path = re.search(r'"([^"]+)"', args)
            assert path, "route path must be a literal"
            entries.extend((method.upper(), parser.normalise(path.group(1)))
                           for method in re.findall(r"\b(get|post|put|patch|delete)\s*\(", args))
        assert len(entries) == len(set(entries)), "duplicate mount in one builder"
        return set(entries)

    wrapper_end = lib.index("pub(crate) fn projections_base(")
    wrapper = pairs(lib[lib.index("pub fn projections("):wrapper_end])
    base = pairs(lib[wrapper_end:lib.index("let routes = if manual_receipts")])
    runtime_set = pairs(runtime_builder)
    execute = {("POST", "/api/v1/documents/:p/checks/execute")}
    assert wrapper == execute, "projection-only execution must retain its unconfigured handler"
    assert wrapper & base == set(), "projection-only duplicate mount"
    assert base & runtime_set == set(), "runtime duplicate mount"
    assert runtime_set & wrapper == execute, "only the execution handler is replaced"
    assert "crate::projections_base(executor.store().clone(), false)" in runtime_source
    assert len(wrapper | base) == 43
    assert len(base) == 42
    assert len(runtime_set) == 20
    assert len(base | runtime_set) == inventory
    contract = CONTRACT.read_text(encoding="utf-8")
    assert "43 projection method/path pairs" in contract
    assert "38 unconditional mounts" in contract
    assert "manual legacy `/jobs/{id}/receipts` remains absent" in contract


def test_the_runbooks_case_counts_match_the_matrix():
    facts = tree_facts()
    runbook = RUNBOOK.read_text(encoding="utf-8")
    golden = re.search(r"golden corpus covers (\d+) cases", runbook)
    real = re.search(r"real-material mode (\d+)", runbook)
    assert golden, "the runbook no longer states the golden-corpus case count"
    assert real, "the runbook no longer states the real-material case count"
    assert int(golden.group(1)) == facts["golden_cases"], (
        f"the runbook states {golden.group(1)} golden cases, the matrix has {facts['golden_cases']}")
    assert int(real.group(1)) == facts["real_cases"], (
        f"the runbook states {real.group(1)} real-material cases, the matrix has {facts['real_cases']}")


def test_the_contracts_readiness_counts_match_the_declared_routes():
    """§7 reports readiness on the staged runtime, one entry per declared route."""
    facts = tree_facts()
    contract = CONTRACT.read_text(encoding="utf-8")
    declared = re.search(r"\*\*(\d+)\*\* capabilities declared", contract)
    readiness = re.search(r"readiness `total (\d+) / ready", contract)
    assert declared, "§7 no longer states a declared-capability count"
    assert readiness, "§7 no longer states a readiness total"
    assert int(declared.group(1)) == facts["declared_routes"], (
        f"§7 states {declared.group(1)} declared capabilities, ROUTE_SCRIPTS has "
        f"{facts['declared_routes']}")
    # Keep the historical measured 13-route receipt distinct from current declarations.
    assert "historical measured 13-route runtime" in contract
    assert int(readiness.group(1)) == 13



def test_the_ledger_agrees_with_the_disposition_it_points_at():
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    disposition = json.loads(DISPOSITION.read_text(encoding="utf-8"))
    recorded = ledger.get("backend_key_disposition_20261001")
    assert recorded, "the ledger no longer records the per-key disposition"
    assert recorded["keys_recorded"] == len(disposition["keys"]), (
        f"the ledger says {recorded['keys_recorded']} keys, the document lists "
        f"{len(disposition['keys'])}")
    assert recorded["evidence_counts"] == disposition["counts"], (
        f"the ledger's evidence counts {recorded['evidence_counts']} disagree with the "
        f"document's {disposition['counts']}")
    assert recorded["status_counts"] == disposition["status_counts"]


def test_the_dispositions_stated_counts_match_its_own_entries():
    disposition = json.loads(DISPOSITION.read_text(encoding="utf-8"))
    entries = disposition["keys"]
    evidence: dict[str, int] = {}
    status: dict[str, int] = {}
    for entry in entries:
        evidence[entry["evidence_level"]] = evidence.get(entry["evidence_level"], 0) + 1
        status[entry["status"]] = status.get(entry["status"], 0) + 1
    assert evidence == disposition["counts"], (
        f"the document states {disposition['counts']} but its entries are {evidence}")
    assert status == disposition["status_counts"], (
        f"the document states {disposition['status_counts']} but its entries are {status}")


def test_every_disposition_key_is_one_of_the_keys_this_task_owns():
    disposition = json.loads(DISPOSITION.read_text(encoding="utf-8"))
    rows = list(csv.DictReader(CSV.open(encoding="utf-8")))
    lane_of = {row["key"]: row["lane"] for row in rows}
    unknown = [entry["key"] for entry in disposition["keys"] if entry["key"] not in lane_of]
    assert not unknown, f"disposition keys that are not in the source CSV: {unknown[:5]}"
    wrong_lane = [entry["key"] for entry in disposition["keys"]
                  if lane_of[entry["key"]] not in OWNED_LANES]
    assert not wrong_lane, (
        f"disposition keys outside the lanes this task owns: {wrong_lane[:5]}")


def test_the_disposition_covers_every_key_in_the_two_owned_lanes():
    """A key in an owned lane with no disposition is a claim nobody has re-examined."""
    disposition = json.loads(DISPOSITION.read_text(encoding="utf-8"))
    recorded = {entry["key"] for entry in disposition["keys"]}
    rows = list(csv.DictReader(CSV.open(encoding="utf-8")))
    owned = {row["key"] for row in rows if row["lane"] in OWNED_LANES}
    missing = sorted(owned - recorded)
    assert not missing, f"owned keys with no disposition: {missing}"
