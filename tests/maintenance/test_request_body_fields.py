"""The exact request-body field names, read from the source rather than remembered.

Every body struct is deserialised with serde's default behaviour, so an unknown field is silently
dropped: the request succeeds without doing what the caller meant. That has cost real time on this
branch three times - `review_state` sent where the route wants `status`, then again on a different
route, then `body` sent where the field is `new_body` and the successor revision came out as a
clone of the old one.

The contract now lists these fields. This test keeps the list and the source in step, and fails if
a field in the document is not a field in the struct - so a reader can rely on the table.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
LIB = REPO / "crates/archeaxis-api/src/lib.rs"
CONTRACT = REPO / "docs/current/AAOS-PRODUCTION-HTTP-CONTRACT-20261001.md"

# struct -> the fields the contract must list, with `?` marking an Option field.
EXPECTED: dict[str, tuple[str, ...]] = {
    "ImportBody": ("name", "content_base64", "origin_kind?", "origin_ref?", "origin_name?",
                   "received_at?"),
    "EnqueueBody": ("job_id", "kind", "input_ref"),
    "AnchorBody": ("revision", "position", "checksum?"),
    "KnowledgeBody": ("knowledge_type", "body", "status", "created_by", "v3?"),
    "KnowledgeFromTransformBody": ("knowledge_type", "body", "source_id", "job_id", "transform_id",
                                   "selection_start_utf16", "selection_end_utf16", "quote"),
    "ReviewBody": ("action", "reviewer", "note?", "new_body?"),
    "ItemReferenceBody": ("knowledge_id",),
    "AssessmentBody": ("knowledge_id",),
    "LearningEventBody": ("item_key", "kind", "correct", "client_event_id?", "schedule_state?",
                          "now?"),
    "StatefulReviewBody": ("item_key", "client_event_id", "correct", "rating?", "now?", "answer?",
                           "assessment_id?", "question_version?", "knowledge_version?",
                           "exposure_id?", "assist_strategy?", "rating_version?", "correction_id?"),
    "MachineTaskBody": ("task_id", "conditions", "model_version", "scope", "outcome",
                        "knowledge_version?", "method_version?", "tool_version?", "failure?",
                        "retest_of?"),
    "SearchQuery": ("q", "active_only"),
}


def struct_fields(name: str) -> tuple[str, ...]:
    source = LIB.read_text(encoding="utf-8")
    match = re.search(rf"struct\s+{name}\s*\{{(.*?)\n\}}", source, re.S)
    assert match, f"{name} is no longer declared in the API"
    fields: list[str] = []
    for line in match.group(1).splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("//") or stripped.startswith("#["):
            continue
        found = re.match(r"(?:pub\s+)?(\w+)\s*:", stripped)
        if found:
            fields.append(found.group(1) + ("?" if "Option<" in stripped else ""))
    return tuple(fields)


@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_the_struct_still_has_the_fields_this_repository_documents(name: str):
    actual = struct_fields(name)
    assert actual == EXPECTED[name], (
        f"{name} changed: the source has {actual}, this file expects {EXPECTED[name]}")


def test_the_contract_lists_every_documented_field_name():
    contract = CONTRACT.read_text(encoding="utf-8")
    missing: list[str] = []
    for name, fields in EXPECTED.items():
        for field in fields:
            bare = field.rstrip("?")
            # Only distinctive names are worth requiring in the prose; `body` and `kind` appear
            # everywhere and would match trivially.
            if len(bare) < 5 or bare in {"body", "kind", "state", "action"}:
                continue
            if bare not in contract:
                missing.append(f"{name}.{bare}")
    assert not missing, (
        f"the contract does not name these request fields, so a reader would guess: {missing}")


def test_the_route_that_caused_the_confusion_names_the_right_field():
    """`new_body` specifically: sending `body` yields a successor that clones the old revision."""
    contract = CONTRACT.read_text(encoding="utf-8")
    assert "new_body" in contract, "the contract must name `new_body` for the modified action"
    review = struct_fields("ReviewBody")
    assert "new_body?" in review, f"ReviewBody no longer carries new_body: {review}"
    assert "body" not in review, (
        "ReviewBody gained a `body` field; the contract's warning about the wrong name needs "
        f"rewriting, because both would then exist: {review}")


def test_search_has_no_paging_parameters():
    """A UI looking for limit/offset/sort must be told they do not exist."""
    search = struct_fields("SearchQuery")
    assert set(search) == {"q", "active_only"}, f"SearchQuery changed: {search}"
    contract = CONTRACT.read_text(encoding="utf-8")
    assert "no** `limit`, `offset`" in contract or "no** `limit`" in contract, (
        "the contract must state that search has no paging parameters")
    source = LIB.read_text(encoding="utf-8")
    assert re.search(r"search::search\(conn,\s*&query\.q,\s*20\)", source), (
        "the hardcoded search limit changed; the contract states it is 20")
