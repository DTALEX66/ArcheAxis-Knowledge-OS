"""The 2026-10-02 plan names ten deliverables; this checks all ten exist and are not stubs.

The plan is explicit that its output is a document set rather than new code, so the risk is a
deliverable being quietly dropped. Each is asserted to exist, to parse, and to carry the section
that makes it useful rather than being an empty placeholder.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
DOCS = REPO / "docs/current"

# Deliverable number -> (file, a key that must be present so an empty file cannot pass)
DELIVERABLES = {
    1: ("AAOS-FULL-HISTORY-RECOVERY-20261002.json", "all_recorded_hashes_match"),
    2: ("AAOS-CLOUD-BRANCH-RECONCILIATION-20261002.md", None),
    3: ("AAOS-LOCAL-VS-CLOUD-GAP-20261002.json", "gaps"),
    4: ("AAOS-CAPABILITY-MASTER-ATLAS-V3-20261002.json", "r7_active_surface"),
    5: ("AAOS-CORE-PLUGIN-BOUNDARY-V1-20261002.json", "trusted_microkernel_never_plugin"),
    6: ("AAOS-OSS-DONOR-DISPOSITION-V2-20261002.json", "verdict_definitions"),
    7: ("AAOS-R7-FAST-CLOSURE-TASKPACK-20261002.json", "gates"),
    8: ("AAOS-R7-ACCEPTANCE-MATRIX-20261002.json", "ladder"),
    9: ("AAOS-OWNER-DECISIONS-REQUIRED-20261002.json", "decisions"),
    10: ("AAOS-NEXT-EXECUTION-QUEUE-20261002.json", "now"),
}

GATES = ["G0", "G1", "G2", "G3", "G4", "G5"]


@pytest.mark.parametrize("number", sorted(DELIVERABLES))
def test_deliverable_exists_and_is_not_empty(number: int):
    name, required_key = DELIVERABLES[number]
    path = DOCS / name
    assert path.is_file(), f"deliverable {number} is missing: {name}"
    assert path.stat().st_size > 400, f"deliverable {number} looks like a stub: {name}"
    if required_key:
        document = json.loads(path.read_text(encoding="utf-8"))
        assert required_key in document, (
            f"deliverable {number} lacks `{required_key}`: {name}")


def test_the_taskpack_compresses_into_exactly_the_six_gates():
    taskpack = json.loads(
        (DOCS / "AAOS-R7-FAST-CLOSURE-TASKPACK-20261002.json").read_text(encoding="utf-8"))
    assert [gate["gate"] for gate in taskpack["gates"]] == GATES, (
        "the taskpack must be exactly G0..G5; a third parallel route is what the plan forbids")
    assert taskpack["parallel_routes"] == 1


def test_the_acceptance_matrix_uses_the_plan_ladder():
    matrix = json.loads(
        (DOCS / "AAOS-R7-ACCEPTANCE-MATRIX-20261002.json").read_text(encoding="utf-8"))
    assert matrix["ladder"] == ["PLANNED", "CONTRACT_ONLY", "IMPLEMENTED", "TESTED_LOCAL",
                                "INTEGRATED", "REAL_INPUT_VERIFIED", "GREEN_VERIFIED", "RELEASED"]
    # and it must not round a gate up beyond what exists
    for gate in matrix["gates"]:
        assert gate["level_now"] in matrix["ladder"], gate


def test_no_gate_is_claimed_above_what_the_project_has_reached():
    matrix = json.loads(
        (DOCS / "AAOS-R7-ACCEPTANCE-MATRIX-20261002.json").read_text(encoding="utf-8"))
    ceiling = matrix["ladder"].index("INTEGRATED")
    for gate in matrix["gates"]:
        level = matrix["ladder"].index(gate["level_now"])
        assert level <= ceiling, (
            f"{gate['gate']} claims {gate['level_now']}, above anything this project has measured")


def test_the_plan_supersession_record_exists():
    path = DOCS / "AAOS-PLAN-SUPERSESSION-20261002.md"
    assert path.is_file(), "the superseded plan must be archived rather than dropped"
    text = path.read_text(encoding="utf-8")
    for anchor in ("R6", "M0", "R7", "Rollback"):
        assert anchor in text, f"the supersession record does not mention {anchor}"


def test_the_history_recovery_names_the_archived_registries():
    recovery = json.loads(
        (DOCS / "AAOS-FULL-HISTORY-RECOVERY-20261002.json").read_text(encoding="utf-8"))
    registries = recovery["registries"]
    expected = {"source_baseline_97": 97, "oss_research_pool_369": 369, "supply_chain_47": 47,
                "capability_absorption_11": 11, "capability_atlas_mapping": 16,
                "requirement_trace": 17}
    for name, count in expected.items():
        assert registries[name]["present"], f"{name} is not archived"
        assert registries[name]["data_rows"] == count, (
            f"{name} holds {registries[name]['data_rows']} rows, the plan names {count}")
