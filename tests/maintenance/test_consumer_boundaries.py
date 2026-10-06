"""The layer boundaries the contract tells a UI to respect, checked against the tree.

`docs/LANGUAGE_BOUNDARY_AUTHORITY_INDEX.md` fixes what each layer owns: the desktop owns UI and
supervision and must not execute SQL or duplicate business rules, Rust is the one authoritative
writer, and the Python workers hold no main-database handle. The contract's §0 turns that into
instructions for a UI, and two other claims in §8 are about packaging and about a *second* backend
that is easy to confuse with this one.

Assertions about prose are weak, so where a claim has a source of truth in the tree it is checked
against that instead: the writer boundary has a guard script, and the wheel's contents are
declared in its own build configuration.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CONTRACT = REPO / "docs/current/AAOS-PRODUCTION-HTTP-CONTRACT-20261001.md"
LANGUAGE_INDEX = REPO / "docs/LANGUAGE_BOUNDARY_AUTHORITY_INDEX.md"
BOUNDARY_GUARD = REPO / "scripts/check_language_boundaries.py"


def test_the_contract_states_the_consumer_boundaries():
    contract = CONTRACT.read_text(encoding="utf-8")
    # the four instructions a UI branch needs, one assertion each so a removal is specific
    assert "surface to call, not a specification to reimplement" in contract, (
        "the contract must say it is a surface rather than a specification to reimplement")
    assert "duplicate business rules" in contract, (
        "the contract must forbid duplicating business rules in the UI")
    assert "never opens the workspace database" in contract, (
        "the contract must say the UI never opens the workspace database")
    assert "re-checks workspace identity after a restart" in contract, (
        "the contract must require re-checking workspace identity after a restart")


def test_the_language_index_still_says_what_the_contract_quotes():
    index = LANGUAGE_INDEX.read_text(encoding="utf-8")
    # the contract paraphrases these three rows; if the authority changes, the paraphrase is wrong
    assert "no direct SQL or duplicated business rules" in index, (
        "the desktop boundary changed; the contract's paraphrase of it needs rewriting")
    assert "one authoritative writer" in index, (
        "the single-writer claim changed; the contract leans on it")
    assert "no main database handle or human approval" in index, (
        "the worker boundary changed; the contract quotes it")


def test_the_single_writer_boundary_has_a_guard_that_still_exists():
    """The contract's strongest boundary claim is enforced by a script, not just asserted."""
    assert BOUNDARY_GUARD.is_file(), (
        "the language-boundary guard is gone, so the one-writer claim has no enforcement")
    text = BOUNDARY_GUARD.read_text(encoding="utf-8")
    assert "database owner" in text or "canonical" in text.lower(), (
        "the guard no longer expresses the database-ownership rule the contract relies on")


def test_the_contract_does_not_confuse_the_two_backends():
    """The wheel's schema baseline and the Core's are different databases, and that is a trap."""
    contract = CONTRACT.read_text(encoding="utf-8")
    assert "python_compatibility" in contract, (
        "the contract must name the wheel's schema baseline so it cannot be mistaken for the Core's")
    assert "kb_attachment_facts" in contract, (
        "the contract must name a table that only the wheel's baseline has")
    assert re.search(r"not\*{0,2}\s+the same database", contract), (
        "the contract must state plainly that the two backends are different databases")
    assert "workspace_meta" in contract, "the contract must name the Core's own baseline"


def test_the_contract_records_that_the_wheel_omits_the_workers():
    contract = CONTRACT.read_text(encoding="utf-8")
    assert "does **not** contain" in contract and "services/python-workers" in contract, (
        "the contract must record that the wheel omits the workers, so nobody promises a "
        "wheel-only full loop")
    # and the packaging configuration must actually exclude them, or the claim is stale
    pyproject = REPO / "pyproject.toml"
    if pyproject.is_file():
        text = pyproject.read_text(encoding="utf-8")
        packages = re.search(r"packages\s*=\s*\[(.*?)\]", text, re.S)
        if packages:
            listed = packages.group(1)
            assert "services" not in listed, (
                "the wheel now packages services/, so the contract's note about it is stale")


def test_the_migration_acceptance_reference_is_the_current_one():
    contract = CONTRACT.read_text(encoding="utf-8")
    assert "R6 A13" in contract and "M0 P5" in contract, (
        "the contract must point at the current migration acceptance, not a historical gate")
    index = LANGUAGE_INDEX.read_text(encoding="utf-8")
    assert "R6 A13 and" in index and "M0 P5" in index, (
        "the language authority no longer names those gates; the contract's reference is stale")
