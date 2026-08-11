"""Tests for shared.research_boundary (unreviewed reference boundary)."""

from __future__ import annotations

from shared.research_boundary import unreviewed_research_references


def test_blocked_prefixes_detected() -> None:
    refs = [
        "research_package_alpha",
        "intake_2026",
        "source_syllabus",
        "claim_q1",
        "evidence_doc",
        "finding_42",
        "http://example.com",
        "https://example.org/page",
    ]
    blocked = unreviewed_research_references(refs)
    assert len(blocked) == 8
    assert blocked[0] == "research_package_alpha"
    assert "https://example.org/page" in blocked


def test_normal_references_not_blocked() -> None:
    refs = ["textbook", "lecture notes", "PDF doc", "section 3.2"]
    assert unreviewed_research_references(refs) == ()


def test_case_insensitive_prefix_match() -> None:
    blocked = unreviewed_research_references(["Research_Package_X", "HTTP://EXAMPLE.COM"])
    assert len(blocked) == 2
    assert "Research_Package_X" in blocked
    assert "HTTP://EXAMPLE.COM" in blocked


def test_whitespace_stripped() -> None:
    blocked = unreviewed_research_references(["  https://example.com  ", "  source_x  "])
    assert len(blocked) == 2
    assert all(not r.startswith(" ") and not r.endswith(" ") for r in blocked)


def test_empty_input() -> None:
    assert unreviewed_research_references([]) == ()
    assert unreviewed_research_references(()) == ()


def test_non_string_objects_coerced() -> None:
    blocked = unreviewed_research_references([12345, None, b"https://bytes.example"])
    # b"https://bytes.example" str() → "b'https://bytes.example'" which starts
    # with "b'..." — not blocked; None → "None" — not blocked
    assert blocked == ()
