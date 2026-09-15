"""Fail-closed preflight for the indexed ArcheAxis resource roots.

Only directory metadata is inspected.  The canonical roots are derived from
the repository parent and the checked-in shared-resource index; contents are
never enumerated.  ``integration`` is Green-only and ``test`` is ceshi-only.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

RESOURCE_NAMES = {
    "shared_models": "Model library",
    "shared_tools": "OS External Configuration",
    "green_application": "ArcheAxis.Knowledge.Green-x64",
    "green_material_library": "资料库",
    "project_test_corpus": "ceshi",
}
PURPOSE_TARGET = {"integration": "green_application", "test": "project_test_corpus"}
INDEX_PATH = "docs/SHARED_RESOURCE_PATH_INDEX.md"


def _is_reparse(path: Path) -> bool:
    return bool(getattr(path.stat(follow_symlinks=False), "st_file_attributes", 0) & 0x400)


def check_resource_boundaries(project_root: Path, *, purpose: str | None = None) -> dict:
    root = Path(os.path.abspath(project_root))
    if root.drive.upper() == "E:" or not (root / ".git").exists():
        raise ValueError("project root must be a Git checkout outside E:")
    index = root / INDEX_PATH
    if index.is_file():
        index_text = index.read_text(encoding="utf-8")
        for resource_id, name in RESOURCE_NAMES.items():
            if f"`{resource_id}`" not in index_text or f"`D:\\All projects\\{name}`" not in index_text:
                raise ValueError(f"resource index drift or missing entry: {resource_id}")
    elif root == Path(__file__).resolve().parents[2]:
        raise ValueError(f"resource index is missing: {index}")
    shared_root = root.parent
    rows = []
    for resource_id, name in RESOURCE_NAMES.items():
        path = shared_root / name
        if not path.is_dir():
            raise ValueError(f"indexed resource is missing or not a directory: {resource_id}: {path}")
        if _is_reparse(path):
            raise ValueError(f"indexed resource is a reparse point: {resource_id}: {path}")
        rows.append({"id": resource_id, "canonical_path": str(path), "type": "directory", "reparse": False})
    if purpose is not None:
        if purpose not in PURPOSE_TARGET:
            raise ValueError(f"unknown purpose: {purpose}")
        target = PURPOSE_TARGET[purpose]
        rows_by_id = {row["id"]: row for row in rows}
        return {"schema": "archeaxis.resource-boundaries/v1", "purpose": purpose,
                "target": rows_by_id[target], "resources": rows}
    return {"schema": "archeaxis.resource-boundaries/v1", "purpose": None,
            "target": None, "resources": rows}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("project_root", nargs="?", type=Path, default=Path("."))
    parser.add_argument("--purpose", choices=sorted(PURPOSE_TARGET))
    parser.add_argument("--output", type=Path, help="JSON output under project .project-local")
    args = parser.parse_args()
    try:
        report = check_resource_boundaries(args.project_root, purpose=args.purpose)
        if args.output:
            output = Path(os.path.abspath(args.output))
            project_local = Path(os.path.abspath(args.project_root)) / ".project-local"
            output.relative_to(project_local)
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError) as exc:
        print(f"resource boundary check failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
