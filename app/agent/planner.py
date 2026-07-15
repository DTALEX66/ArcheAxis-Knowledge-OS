from __future__ import annotations

import re
from typing import Any

from app.schemas import TaskPack

_FILE_READ_GOAL = re.compile(r"^read\s+file\s*:\s*(?P<path>.+?)\s*$", re.IGNORECASE)


def plan_goal(goal: str) -> list[dict[str, Any]]:
    """Derive the smallest supported real-tool plan from an explicit goal."""
    match = _FILE_READ_GOAL.fullmatch(goal.strip())
    if not match:
        return []
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


def plan(task: TaskPack) -> list[dict[str, Any]]:
    """Preserve explicit plans, otherwise derive one from the task goal."""
    return task.steps or plan_goal(task.goal)
