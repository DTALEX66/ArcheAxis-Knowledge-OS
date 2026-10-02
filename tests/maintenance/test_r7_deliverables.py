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


# --- the master taskpack's section 42 first round ----------------------------------------------
# Section 42 names nine records the first round must produce and land before any code execution.
FIRST_ROUND = {
    "CURRENT_AUTHORITY_SNAPSHOT": "AAOS-CURRENT-AUTHORITY-SNAPSHOT-20261002.json",
    "HISTORY_COVERAGE_LEDGER": "AAOS-HISTORY-COVERAGE-LEDGER-20261002.json",
    "BRANCH_CONVERGENCE_LEDGER": "AAOS-BRANCH-CONVERGENCE-LEDGER-20261002.json",
    "LOCAL_CLOUD_RECONCILIATION": "AAOS-LOCAL-CLOUD-RECONCILIATION-20261002.json",
    "CORE_PLUGIN_BOUNDARY": "AAOS-CORE-PLUGIN-BOUNDARY-V1-20261002.json",
    "FAST_CLOSURE_GOLDEN_PATH": "AAOS-FAST-CLOSURE-GOLDEN-PATH-V1-20261002.json",
    "UI_IA_FREEZE": "AAOS-UI-IA-FREEZE-V1-20261002.json",
    "OPEN_BLOCKERS_AND_OWNER_GATES": "AAOS-OPEN-BLOCKERS-AND-OWNER-GATES-20261002.json",
}
EXECUTION_ORDER = "AAOS-EXECUTION-ORDER-AND-DOD-20261002.json"


@pytest.mark.parametrize("name", sorted(FIRST_ROUND))
def test_first_round_record_exists_and_parses(name: str):
    path = DOCS / FIRST_ROUND[name]
    assert path.is_file(), f"section 42 first-round record is missing: {name}"
    assert path.stat().st_size > 500, f"{name} looks like a stub"
    json.loads(path.read_text(encoding="utf-8"))


def test_the_execution_order_and_dod_record_exists():
    path = DOCS / EXECUTION_ORDER
    assert path.is_file(), "section 42's last first-round item is missing"
    document = json.loads(path.read_text(encoding="utf-8"))
    assert [round_["round"] for round_ in document["rounds"]] == ["first", "next"]
    assert len(document["rounds"][0]["items"]) == 9, "the first round is nine records"
    for item in document["rounds"][0]["items"]:
        assert item["status"] == "DONE" and item["dod"], item


def test_the_branch_ledger_records_the_fourteen_required_fields():
    ledger = json.loads(
        (DOCS / "AAOS-BRANCH-CONVERGENCE-LEDGER-20261002.json").read_text(encoding="utf-8"))
    required = ["branch", "base", "head", "ahead_of_main", "behind_main", "merged_into_main",
                "unique_content", "unique_contracts", "unique_docs", "unique_tests",
                "unique_runtime_evidence", "conflicts", "superseded_content", "decision",
                "rollback_sha"]
    for branch in ledger["branches"]:
        for field in required:
            assert field in branch, f"{branch['branch']} is missing the {field} field"


def test_unique_content_is_measured_against_each_branchs_own_base():
    """Measuring everything against main would credit #157 and #158 with #156's commits."""
    ledger = json.loads(
        (DOCS / "AAOS-BRANCH-CONVERGENCE-LEDGER-20261002.json").read_text(encoding="utf-8"))
    for branch in ledger["branches"]:
        if branch["branch"].endswith("dsh-aaos-real-multiformat-loop-20261001"):
            assert branch["base"] == "codex/Audit", branch["base"]
            # 92 files differ from codex/Audit; 151 differ from main, which would be wrong here
            assert branch["unique_content"]["unique_files"] == 92, branch["unique_content"]
        if branch["branch"].endswith("minimax-aaos-cosmic-ui-20261001"):
            assert branch["unique_content"]["unique_files"] == 14, branch["unique_content"]


def test_the_cross_pr_overlap_is_measured_not_assumed():
    ledger = json.loads(
        (DOCS / "AAOS-BRANCH-CONVERGENCE-LEDGER-20261002.json").read_text(encoding="utf-8"))
    overlap = ledger["ordering_hazard"]["cross_pr_overlap_measured"]
    assert overlap["files_in_common_count"] == 0, overlap
    assert "measured" in ledger["ordering_hazard"]["conflict_assessment"]


def test_the_ia_freeze_names_the_six_domains_the_taskpack_froze():
    ia = json.loads((DOCS / "AAOS-UI-IA-FREEZE-V1-20261002.json").read_text(encoding="utf-8"))
    assert ia["frozen_top_level_domains"] == ["Home", "Knowledge", "Learning", "AI Learning",
                                              "Blueprint / Explore", "System"]
    # and the earlier wrong reading must stay recorded rather than quietly dropped
    assert "correction_of_the_earlier_record" in ia


def test_the_golden_path_is_the_taskpacks_own_chain():
    golden = json.loads(
        (DOCS / "AAOS-FAST-CLOSURE-GOLDEN-PATH-V1-20261002.json").read_text(encoding="utf-8"))
    assert golden["stage_count"] == len(golden["chain"])
    joined = " | ".join(golden["chain"])
    for anchor in ("real Parser / OCR", "FTS search", "FSRS / learning event", "Retest",
                   "restart", "all read back"):
        assert anchor in joined, f"the golden path is missing {anchor}"


def test_the_authority_snapshot_keeps_r6_and_m0_live():
    authority = json.loads(
        (DOCS / "AAOS-CURRENT-AUTHORITY-SNAPSHOT-20261002.json").read_text(encoding="utf-8"))
    live = authority["active_execution_authority"]
    assert "AAK-LOCAL-GREEN-ABSORB-FIRST-20260919-R6" in live["R6_plan_id"]
    assert "M0-SHORTEST-COMPLETE-LOOP" in live["M0_overlay"]
    assert "label" in live["R7_status"], "R7 must not be recorded as Authority"
    assert "FROZEN" in authority["frozen_by_this_plan"]["release"]


def test_the_history_coverage_ledger_forbids_missing():
    ledger = json.loads(
        (DOCS / "AAOS-HISTORY-COVERAGE-LEDGER-20261002.json").read_text(encoding="utf-8"))
    assert "MISSING" in ledger["rule"], "section 34 forbids MISSING and the rule must say so"
    counts = ledger["counts"]
    assert counts == {"capability_atlas": 16, "requirement_trace": 17, "history_to_current": 15,
                      "capability_absorption": 11}, counts
    # every mapped row must land in the section 34 vocabulary
    vocabulary = {"IMPLEMENTED", "ACTIVE_NOW", "NEXT", "FUTURE", "DONOR", "MOVED_TO_WORK_LAB",
                  "SUPERSEDED_WITH_REPLACEMENT", "REJECTED_WITH_REASON"}
    for row in ledger["archived_registries"]["capability_atlas_16"]:
        assert row["coverage"] in vocabulary, row
    for row in ledger["archived_registries"]["requirement_trace_17"]:
        assert row["coverage"] in vocabulary, row


def test_the_archive_holds_the_complete_document_not_a_partial_copy():
    archive = REPO / "docs/history/plan-recovery-2026-10-02"
    manifest = json.loads((archive / "ARCHIVE_MANIFEST.json").read_text(encoding="utf-8"))
    copy = manifest["source_copies"][0]
    assert copy["byte_identical"] is True, copy
    assert manifest["provenance"]["sections"] == 45, manifest["provenance"]
    assert manifest["provenance"]["lines"] == 1019, manifest["provenance"]
    # the replaced partial copy stays recorded rather than being silently overwritten
    assert "superseded_partial_archive" in manifest
    assert "RESOLVED" in manifest["truncation"]["observed"]
