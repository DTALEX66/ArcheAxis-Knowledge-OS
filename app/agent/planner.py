from __future__ import annotations

import re
from typing import Any

from app.schemas import TaskPack

_FILE_READ_GOAL = re.compile(r"^read\s+file\s*:\s*(?P<path>.+?)\s*$", re.IGNORECASE)
_KNOWLEDGE_SEARCH_GOAL = re.compile(
    r"^search\s+knowledge\s*:\s*(?P<query>.+?)\s*$", re.IGNORECASE
)


def plan_goal(goal: str) -> list[dict[str, Any]]:
    """Derive the smallest supported real-tool plan from an explicit goal."""
    match = _FILE_READ_GOAL.fullmatch(goal.strip())
    if match:
        return [
            {
                "id": 1,
                "name": "read_file",
                "type": "tool",
                "tool": "file_read",
                "path": match.group("path"),
                "dry_run": False,
            }
        ]
    match = _KNOWLEDGE_SEARCH_GOAL.fullmatch(goal.strip())
    if match:
        return [
            {
                "id": 1,
                "name": "search_knowledge",
                "type": "tool",
                "tool": "kb_search",
                "query": match.group("query"),
                "top_k": 5,
                "dry_run": False,
            }
        ]
    return []


def plan(task: TaskPack) -> list[dict[str, Any]]:
    """Preserve explicit plans, otherwise derive one from the task goal."""
    return task.steps or plan_goal(task.goal)
