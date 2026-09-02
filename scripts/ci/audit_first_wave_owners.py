"""Produce the source-only G0 inventory of direct SQLite connection owners.

This script deliberately does not import product modules or open a database.
It is an input to the language-boundary audit, not evidence of a runtime
writer and not authorization to change one.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


AUDIT_ROOTS = ("app", "shared", "knowledge_base", "inspiration_research")
EXCLUDED_PATH_PARTS = {"tests", "docs", "__pycache__"}
SQLITE_CONNECTION = re.compile(r"sqlite3\s*\.\s*connect\s*\(")


def audit_sqlite_connection_owners(project_root: Path) -> list[str]:
    """Return sorted production Python paths containing direct connections."""

    owners: list[str] = []
    for root_name in AUDIT_ROOTS:
        source_root = project_root / root_name
        if not source_root.is_dir():
            continue
        for source in source_root.rglob("*.py"):
            relative = source.relative_to(project_root)
            if EXCLUDED_PATH_PARTS.intersection(relative.parts):
                continue
            if SQLITE_CONNECTION.search(source.read_text(encoding="utf-8")):
                owners.append(relative.as_posix())
    return sorted(owners)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path(__file__).resolve().parents[2],
        help="repository root to scan (default: this script's repository)",
    )
    args = parser.parse_args()
    root = args.project_root.resolve()
    owners = audit_sqlite_connection_owners(root)
    print(json.dumps({"project_root": str(root), "owner_count": len(owners), "owners": owners}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
