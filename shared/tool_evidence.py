"""Shared truthfulness checks for attributable tool execution evidence."""

from __future__ import annotations

from typing import Any

REAL_EVIDENCE_TOOLS = {"file_read", "safe_write", "kb_search", "mk_search"}
NON_REAL_EVIDENCE_TOOLS = {"echo", "noop", "no_op", "context_pack_build", "taskpack_generate"}


def has_real_tool_evidence(tool: str, result: dict[str, Any]) -> tuple[bool, str]:
    """Return whether a non-dry-run tool result contains attributable evidence."""
    tool_name = str(tool).strip()
    if result.get("dry_run") is True:
        return False, "dry_run_result_is_not_real_evidence"
    if tool_name in NON_REAL_EVIDENCE_TOOLS:
        return False, f"non_real_tool_has_no_evidence:{tool_name}"
    if tool_name == "file_read":
        if result.get("path") and "content" in result:
            return True, "file_read_content_evidence"
        return False, "missing_file_read_evidence"
    if tool_name == "safe_write":
        if result.get("written") is True and result.get("path"):
            return True, "safe_write_written_evidence"
        return False, "missing_safe_write_evidence"
    if tool_name in {"kb_search", "mk_search"}:
        if isinstance(result.get("count"), int) and isinstance(result.get("items"), list):
            return True, f"{tool_name}_count_evidence"
        return False, f"missing_{tool_name}_evidence"
    return False, f"unsupported_tool_has_no_evidence:{tool_name or '<missing>'}"
