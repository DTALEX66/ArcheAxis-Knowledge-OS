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
CONTRACT = REPO / "docs/current/AAOS-PRODUCTION-HTTP-CONTRACT-20261001.md"
RUNBOOK = REPO / "docs/current/AAOS-BACKEND-ACCEPTANCE-RUNBOOK-20261001.md"

# Contract section number -> (artifact, what the artifact establishes). Keyed by number rather
# than title, because the titles carry suffixes that change as the document is edited.
COVERAGE: dict[str, tuple[str, str]] = {
    "1": ("crates/archeaxis-api/tests/contract_process_model.rs",
          "readiness line, IPv4-only binding, port precedence, exit code 2 for every launch-input "
          "failure"),
    "2": ("crates/archeaxis-api/tests/contract_auth_boundaries.rs",
          "one credential header, both principals in it, the actor derived from which token "
          "matched, 401 and 403 shapes"),
    "3": ("tests/maintenance/test_contract_route_inventory.py",
          "all 30 documented method+path pairs are served and none is undocumented, plus the one "
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
}

# Additional artifacts that check a section without being its primary one.
ALSO_CHECKS: dict[str, list[str]] = {
    "3": ["crates/archeaxis-api/tests/contract_job_outputs.rs"],
}

# Sections whose evidence is not a single test file, with where it actually lives.
EVIDENCE_ELSEWHERE: dict[str, str] = {
    "7": "the probes and the readiness checker referenced by the section itself, recorded in "
         "docs/current/AAOS-BACKEND-LOOP-EVIDENCE-20261001.md",
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
    """The runbook must name the artifacts, or the UI branch cannot run them."""
    relative, _what = COVERAGE[section]
    runbook = RUNBOOK.read_text(encoding="utf-8")
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
