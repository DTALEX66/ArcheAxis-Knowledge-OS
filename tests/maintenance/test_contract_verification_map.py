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
    "37": ("tests/test_git_snapshot_exchange.py", "native Git ZIP commit marker, pinned paths and independently retained file export"),
    "36": ("tests/test_worker_machine_answer.py", "structured SDK model identity, effective reasoning budget, usage and deadline"),
    "35": ("tests/test_logseq_exchange.py", "Logseq native outline identity, editable UTF-8 byte ranges and graph-local references"),
    "34": ("tests/test_packaged_knowledge_exchange.py", "the exchange clients, packaged Windows dispatch and a format subcommand in an isolated interpreter"),
    "33": ("tests/test_notion_exchange.py", "Notion CSV snapshots, repeated columns and rows, and local page / attachment links"),
    "32": ("tests/test_evernote_exchange.py", "annotated ENEX preserves existing rich content, entities, literal CDATA and line breaks"),
    "31": ("tests/test_text_format_facts.py", "CommonMark nesting, links, reference images and code fences"),
    "30": ("tests/test_obsidian_vault_sync.py", "synchronization after an interrupted write, rename ambiguity and cited block identity"),
    "29": ("tests/test_obsidian_vault_exchange.py", "Vault Markdown edits and preservation of unchanged source encodings"),
    "28": ("tests/test_adapters_longterm.py", "Zotero web item metadata including organization and native dates"),
    "27": ("tests/test_anki_apkg_readback.py", "edited native fields preserved across note type display-name collisions"),
    "26": ("tests/test_stage_backend_runtime_routes.py", "course donors present and importable in the staged runtime"),
    "25": ("tests/test_directory_batch.py", "completed file records survive process interruption and a changed Core port"),
    "24": ("tests/test_joplin_exchange_tags.py", "shared tag edits preserve other native JEX records and the attachment"),
    "23": ("crates/archeaxis-api/tests/operation_failure_log_api.rs", "bounded metadata-only Store reopen, scope/generation guards, explicit corruption repair and human-only access; not native or installed-runtime qualification"),
    "22": ("crates/archeaxis-api/tests/external_context_api.rs", "offline bounded human-only candidate intake, fixed NOT_CONNECTED status and strict rejection; not external-provider qualification"),
    "21": ("crates/archeaxis-api/tests/template_lifecycle.rs", "guarded bundled template lifecycle, old-object preservation and stale/tampered request refusal"),
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
    "36": ["tests/test_backend_launcher_routes.py"],
    "33": ["tests/test_worker_archive_route.py"],
    "32": ["crates/archeaxis-domain/tests/document_tags.rs"],
    "23": ["tests/maintenance/test_contract_route_inventory.py"],
    "22": ["crates/archeaxis-domain/tests/external_context_candidates.rs",
           "tests/maintenance/test_contract_route_inventory.py"],
    "21": ["crates/archeaxis-domain/tests/template_lifecycle.rs",
           "crates/archeaxis-archive/tests/template_lifecycle_archive.rs"],
    "20": ["tests/test_backend_runtime_safety.py"],
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
    "tests/test_git_snapshot_exchange.py": "python -m pytest tests/test_git_snapshot_exchange.py -q",
    "tests/test_worker_machine_answer.py": "python -m pytest tests/test_worker_machine_answer.py -k staged -q",
    "tests/test_backend_launcher_routes.py": "python -m pytest tests/test_backend_launcher_routes.py -k session_worker -q",
    "tests/test_packaged_knowledge_exchange.py": "python -m pytest tests/test_packaged_knowledge_exchange.py -q",
    "tests/test_logseq_exchange.py": "python -m pytest tests/test_logseq_exchange.py -q",
    "tests/test_worker_archive_route.py": "python -m pytest tests/test_worker_archive_route.py -k finder_metadata -q",
    "tests/test_backend_runtime_safety.py": "python -m pytest tests/test_backend_runtime_safety.py -k smoke_requires_a_matching_shutdown -q",
    "tests/test_notion_exchange.py": "python -m pytest tests/test_notion_exchange.py -q",
    "crates/archeaxis-domain/tests/document_tags.rs":
        "cargo test -p archeaxis-domain --test document_tags enex_tag_names --locked --offline",
    "tests/test_evernote_exchange.py": "python -m pytest tests/test_evernote_exchange.py -q",
    "tests/test_text_format_facts.py": "python -m pytest tests/test_text_format_facts.py -k markdown -q",
    "tests/test_obsidian_vault_sync.py": "python -m pytest tests/test_obsidian_vault_sync.py -q",
    "tests/test_obsidian_vault_exchange.py": "python -m pytest tests/test_obsidian_vault_exchange.py -q",
    "tests/test_adapters_longterm.py": "python -m pytest tests/test_adapters_longterm.py -k zotero_web_api -q",
    "tests/test_anki_apkg_readback.py": "python -m pytest tests/test_anki_apkg_readback.py -k edited_field_export -q",
    "tests/test_stage_backend_runtime_routes.py": "python -m pytest tests/test_stage_backend_runtime_routes.py -k prebuilt_course_stage -q",
    "tests/test_directory_batch.py": "python -m pytest tests/test_directory_batch.py -k interruption_preserves -q",
    "tests/test_joplin_exchange_tags.py": "python -m pytest tests/test_joplin_exchange_tags.py -q",
    "crates/archeaxis-api/tests/operation_failure_log_api.rs":
        "cargo test -p archeaxis-api --test operation_failure_log_api --offline --locked",
    "crates/archeaxis-api/tests/external_context_api.rs":
        "cargo test -p archeaxis-api --test external_context_api --offline --locked",
    "crates/archeaxis-domain/tests/external_context_candidates.rs":
        "cargo test -p archeaxis-domain --test external_context_candidates --offline --locked",
    "crates/archeaxis-api/tests/template_lifecycle.rs":
        "cargo test -p archeaxis-api --test template_lifecycle --offline --locked",
    "crates/archeaxis-domain/tests/template_lifecycle.rs":
        "cargo test -p archeaxis-domain --test template_lifecycle --offline --locked",
    "crates/archeaxis-archive/tests/template_lifecycle_archive.rs":
        "cargo test -p archeaxis-archive --test template_lifecycle_archive --offline --locked",
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
