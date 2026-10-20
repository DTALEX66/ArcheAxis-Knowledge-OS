"""Every section of the published contract must name the artifact that checks it.

The contract tells the UI branch what it may rely on. Each of its sections is checked by a
specific test, and the value of that arrangement depends entirely on the links staying real: a
renamed or deleted test file would leave a section looking verified when nothing checks it, and
nobody would notice, because a missing test does not fail - it simply does not run.

This test is the index. It does not re-check the claims; it checks that every claim still has a
checker, and it fails when the contract grows a section that no artifact covers.

It deliberately asserts that each artifact *contains assertions* rather than only existing: an
empty file would otherwise satisfy the map.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
CONTRACT = REPO / "docs/current/AAOS-PRODUCTION-HTTP-CONTRACT-20261021.md"
RUNBOOK = REPO / "docs/history/repository-consolidation-20261019/current/AAOS-BACKEND-ACCEPTANCE-RUNBOOK-20261001.md"

# Contract section number -> (artifact, what the artifact establishes). Keyed by number rather
# than title, because the titles carry suffixes that change as the document is edited.
COVERAGE: dict[str, tuple[str, str]] = {
    "20": ("crates/archeaxis-api/tests/session_shutdown_process.rs", "complete shutdown ACK, owned process exit0, accepted background conversion and saved object reopen"),
    "19": ("crates/archeaxis-api/tests/ingest_relations.rs",
           "single retained Source identity readback and missing-source refusal before relation consumption"),
    "18": ("crates/archeaxis-api/tests/material_question_api.rs",
           "bounded async admission, disconnected submitter, terminal replay, cancellation and orphan/restore guards; controlled worker is not real model qualification"),
    "17": ("crates/archeaxis-api/tests/ingest_relations.rs",
           "explicit original-CAS batch relations reach the canonical graph with version and restore scope guards"),
    "16": ("crates/archeaxis-api/tests/project_handoff_snapshot_queue.rs",
           "human-only fixed snapshot, expiry and queue/transaction guards; no knowledge acceptance or execution grant"),
    "15": ("crates/archeaxis-api/tests/file_format_qualification.rs",
           "source/job binding, real text and DOCX workers, persisted qualification and corrupt or missing evidence downgrade"),
    "14": ("tests/maintenance/test_contract_route_inventory.py",
           "2026-10-14 finite-host inventory reconciliation: every documented method/path matches the router; runtime qualification remains separate"),
    "12": ("crates/archeaxis-api/tests/document_package_api.rs", "human-only bounded package import, source preservation and idempotency"),
    "13": ("crates/archeaxis-api/tests/contract_machine_answer.rs", "attempt-bound cancellation and durable terminal readback after owned cleanup"),
    "1": ("crates/archeaxis-api/tests/contract_process_model.rs",
          "readiness line, IPv4-only binding, port precedence, exit code 2 for every launch-input "
          "failure"),
    "2": ("crates/archeaxis-api/tests/contract_auth_boundaries.rs",
          "one credential header, both principals in it, the actor derived from which token "
          "matched, 401 and 403 shapes"),
    "3": ("tests/maintenance/test_contract_route_inventory.py",
          "all current documented method+path pairs are served and none is undocumented, plus the one "
          "conditional mount; the outputs route's own boundaries are in contract_job_outputs.rs"),
    "4": ("crates/archeaxis-api/tests/contract_constant_fields.rs",
          "machine.status stays not_recorded with receipts present, the mastery projection is open, "
          "the streak is derived, the fixed notes are present"),
    "5": ("crates/archeaxis-api/tests/contract_conflict_rules.rs",
          "replay is 202 with replayed:true, a different payload under one key is 409, a settled "
          "job is 409 AAK-CON-003, no conflict leaves a second attempt"),
    "6": ("crates/archeaxis-api/tests/contract_launch_shape.rs",
          "the four runtime routes are absent without a text_worker and mounted with one, told "
          "apart by the 405 that a mounted path answers"),
    "10": ("tests/maintenance/test_contract_route_inventory.py",
           "2026-10-10 current-source expansion: every documented method/path is actually registered; no runtime qualification inferred"),
    "11": ("tests/maintenance/test_contract_route_inventory.py",
           "2026-10-12 machine inventory expansion: documented routes match registration; no runtime qualification inferred"),
}

# A section can have more than one checker; each is listed so none can be dropped silently.
ALSO_CHECKS: dict[str, list[str]] = {
    "16": ["crates/archeaxis-api/tests/project_handoff_preview_process.rs",
           "crates/archeaxis-api/tests/project_handoff_process.rs",
           "tests/maintenance/test_contract_route_inventory.py"],
    "14": ["tests/maintenance/test_contract_number_consistency.py"],
    "10": ["tests/maintenance/test_contract_number_consistency.py"],
    "11": ["tests/maintenance/test_contract_number_consistency.py"],
    "3": ["crates/archeaxis-api/tests/contract_job_outputs.rs",
          "crates/archeaxis-api/tests/contract_schedule_authority.rs",
          "crates/archeaxis-api/tests/ingest_batches_api.rs",
          "crates/archeaxis-api/tests/public_research_api.rs"],
    "5": ["crates/archeaxis-api/tests/contract_absent_surfaces.rs",
          "crates/archeaxis-api/tests/contract_review_cost.rs"],
    "7": ["tests/maintenance/test_m0_chain_claims.py",
          "tests/maintenance/test_build_toolchain_routing.py"],
    "8": ["crates/archeaxis-api/tests/contract_absent_surfaces.rs"],
    "4": ["tests/maintenance/test_request_body_fields.py"],
}

# The frozen acceptance runbook keeps its original bytes. Successor checks are
# reachable through the maintained contract's exact commands, never a rewritten
# historical qualification receipt.
CURRENT_CHECK_COMMANDS = {
    "crates/archeaxis-api/tests/session_shutdown_process.rs":
        "cargo test -p archeaxis-api --test session_shutdown_process --offline",
    "crates/archeaxis-api/tests/ingest_relations.rs":
        "cargo test -p archeaxis-api --test ingest_relations --offline",
    "crates/archeaxis-api/tests/material_question_api.rs":
        "cargo test -p archeaxis-api --test material_question_api --offline",
    "crates/archeaxis-api/tests/ingest_batches_api.rs":
        "cargo test -p archeaxis-api --test ingest_batches_api --offline",
    "crates/archeaxis-api/tests/public_research_api.rs":
        "cargo test -p archeaxis-api --test public_research_api --offline",
}

# Sections whose evidence is not a single test file, with where it actually lives.
EVIDENCE_ELSEWHERE: dict[str, str] = {
    "0": "the consumer boundaries, paraphrased from docs/LANGUAGE_BOUNDARY_AUTHORITY_INDEX.md and "
         "checked against that authority and its guard by "
         "tests/maintenance/test_consumer_boundaries.py",
    "7": "the probes and the readiness checker referenced by the section itself, recorded in "
         "docs/history/repository-consolidation-20261019/current/AAOS-BACKEND-LOOP-EVIDENCE-20261001.md",
    "8": "§8 is a list of things deliberately absent; each entry names the artifact that "
         "establishes the absence where one exists, and the rest are boundary statements the "
         "route inventory already checks",
    "9": "each item is marked resolved with the artifact that closed it, or left as an Owner "
         "decision; the archive and transform items name their own tests",
}


def section_number(heading: str) -> str:
    match = re.match(r"(\d+)\.", heading)
    return match.group(1) if match else heading


def contract_sections() -> list[tuple[str, str]]:
    headings = re.findall(r"^## (.+)$", CONTRACT.read_text(encoding="utf-8"), re.M)
    return [(section_number(heading.strip()), heading.strip()) for heading in headings]


def assertions_in(path: Path) -> int:
    text = path.read_text(encoding="utf-8")
    return len(re.findall(r"\b(assert|assert_eq|assert_ne)!|pytest\.raises|assert ", text))


def test_every_contract_section_has_a_recorded_check():
    sections = contract_sections()
    assert sections, "the contract has no sections; the heading format changed"
    uncovered = [
        heading for number, heading in sections
        if number not in COVERAGE and number not in EVIDENCE_ELSEWHERE
    ]
    assert not uncovered, (
        "these contract sections have no checker recorded, so a reader cannot tell whether "
        f"anything verifies them: {uncovered}")


def test_every_recorded_checker_exists_and_asserts():
    missing = []
    empty = []
    recorded = [relative for relative, _ in COVERAGE.values()]
    recorded += [path for paths in ALSO_CHECKS.values() for path in paths]
    for relative in recorded:
        path = REPO / relative
        if not path.is_file():
            missing.append(relative)
        elif assertions_in(path) == 0:
            empty.append(relative)
    assert not missing, f"recorded checkers that do not exist: {missing}"
    assert not empty, f"recorded checkers with no assertions: {empty}"


@pytest.mark.parametrize("section", sorted(COVERAGE))
def test_a_recorded_checker_is_reachable_by_one_command(section):
    """Historical runbook and explicit successor commands retain separate roles."""
    runbook = RUNBOOK.read_text(encoding="utf-8")
    current_contract = CONTRACT.read_text(encoding="utf-8")
    recorded = [COVERAGE[section][0], *ALSO_CHECKS.get(section, [])]
    for relative in recorded:
        if relative in CURRENT_CHECK_COMMANDS:
            assert CURRENT_CHECK_COMMANDS[relative] in current_contract, (
                f"section {section}'s successor checker lacks its current command: {relative}")
            continue
        # The runbook shows `cargo test --test <stem>` without the extension, so accept either.
        stem = Path(relative).name
        bare = Path(relative).stem
        assert stem in runbook or bare in runbook, (
            f"section {section}'s checker {stem} is not named in the acceptance runbook, so a UI "
            "reader cannot find it from the document they are given")


def test_the_runbook_gives_one_command_for_the_whole_contract():
    runbook = RUNBOOK.read_text(encoding="utf-8")
    assert "cargo test -p archeaxis-api --test contract_" in runbook or (
        "contract_" in runbook and "cargo test" in runbook
    ), "the runbook must show how to run the contract checks together"
    assert "test_contract_route_inventory" in runbook, (
        "the runbook must include the Python side of the contract check")
