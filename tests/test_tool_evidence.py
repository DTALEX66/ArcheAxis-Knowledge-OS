"""Tests for shared.tool_evidence (attributable tool execution evidence)."""

from __future__ import annotations

from shared.tool_evidence import has_real_tool_evidence


def test_file_read_with_content_is_evidence() -> None:
    ok, reason = has_real_tool_evidence("file_read", {"path": "a.txt", "content": "text"})
    assert ok is True
    assert reason == "file_read_content_evidence"


def test_file_read_missing_path_not_evidence() -> None:
    ok, reason = has_real_tool_evidence("file_read", {"content": "text"})
    assert ok is False
    assert reason == "missing_file_read_evidence"


def test_safe_write_written_is_evidence() -> None:
    ok, reason = has_real_tool_evidence("safe_write", {"written": True, "path": "out.md"})
    assert ok is True
    assert reason == "safe_write_written_evidence"


def test_safe_write_not_written_not_evidence() -> None:
    ok, _ = has_real_tool_evidence("safe_write", {"written": False, "path": "out.md"})
    assert ok is False


def test_kb_search_count_evidence() -> None:
    ok, reason = has_real_tool_evidence("kb_search", {"count": 3, "items": [1, 2, 3]})
    assert ok is True
    assert reason == "kb_search_count_evidence"


def test_kb_search_missing_fields_not_evidence() -> None:
    ok, reason = has_real_tool_evidence("kb_search", {"count": "three", "items": None})
    assert ok is False
    assert reason == "missing_kb_search_evidence"


def test_dry_run_never_evidence() -> None:
    ok, reason = has_real_tool_evidence("file_read", {"dry_run": True, "path": "a", "content": "x"})
    assert ok is False
    assert reason == "dry_run_result_is_not_real_evidence"


def test_non_real_tools_no_evidence() -> None:
    for tool in ("echo", "noop", "no_op", "context_pack_build", "taskpack_generate"):
        ok, reason = has_real_tool_evidence(tool, {})
        assert ok is False
        assert tool in reason


def test_unsupported_tool_no_evidence() -> None:
    ok, reason = has_real_tool_evidence("random_tool", {"whatever": 1})
    assert ok is False
    assert "random_tool" in reason


def test_missing_tool_name() -> None:
    ok, reason = has_real_tool_evidence("", {})
    assert ok is False
    assert "<missing>" in reason


def test_tool_name_whitespace_stripped() -> None:
    ok, _ = has_real_tool_evidence("  file_read  ", {"path": "a", "content": "c"})
    assert ok is True
