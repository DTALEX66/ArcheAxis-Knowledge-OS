"""Fail-closed preflight for the indexed ArcheAxis resource roots.

Only directory metadata is inspected.  Canonical roots come from the absolute
paths in the checked-in shared-resource index, independently of checkout location; contents are
never enumerated.  ``integration`` is Green-only and ``test`` is ceshi-only.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path, PureWindowsPath

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
    return path.is_symlink() or bool(getattr(path.stat(follow_symlinks=False), "st_file_attributes", 0) & 0x400)


def _allowed_absolute_path(text: str) -> bool:
    windows = PureWindowsPath(text)
    return (
        windows.drive.upper() not in {"E:", "F:"}
        and not windows.drive.startswith("\\\\")
        and Path(text).is_absolute()
        and ".." not in Path(text).parts
    )


def _indexed_paths(index: Path) -> dict[str, Path]:
    registrations: dict[str, list[str]] = {key: [] for key in RESOURCE_NAMES}
    for line in index.read_text(encoding="utf-8-sig").splitlines():
        match = re.match(r"^\s*\|\s*`([^`]+)`\s*\|\s*`([^`]+)`\s*\|", line)
        if match and match[1] in registrations:
            registrations[match[1]].append(match[2])
    paths = {}
    for resource_id, name in RESOURCE_NAMES.items():
        values = registrations[resource_id]
        if len(values) != 1 or not _allowed_absolute_path(values[0]) or Path(values[0]).name != name:
            raise ValueError(f"resource index drift or missing entry: {resource_id}")
        paths[resource_id] = Path(values[0])
    if len({path.parent for path in paths.values()}) != 1:
        raise ValueError("resource index roots must share their registered parent")
    return paths


def check_resource_boundaries(project_root: Path, *, purpose: str | None = None) -> dict:
    if not _allowed_absolute_path(str(project_root)) and (PureWindowsPath(str(project_root)).drive or Path(project_root).is_absolute()):
        raise ValueError("project root must be a Git checkout outside E:/F:")
    root = Path(os.path.abspath(project_root))
    if not _allowed_absolute_path(str(root)):
        raise ValueError("project root must be a Git checkout outside E:/F:")
    for ancestor in [*reversed(root.parents), root]:
        if ancestor.is_symlink() or getattr(ancestor.stat(follow_symlinks=False), "st_file_attributes", 0) & 0x400:
            raise ValueError("project root has a reparse ancestor")
    try:
        git_reparse = _is_reparse(root / ".git")
    except FileNotFoundError as exc:
        raise ValueError("project root must be a Git checkout outside E:/F:") from exc
    if git_reparse:
        raise ValueError("project Git marker is a reparse point")
    if not (root / ".git").exists():
        raise ValueError("project root must be a Git checkout outside E:/F:")
    index = root / INDEX_PATH
    for ancestor in [*reversed(index.parent.parents), index.parent]:
        try:
            metadata = ancestor.stat(follow_symlinks=False)
        except FileNotFoundError:
            break
        if ancestor.is_symlink() or getattr(metadata, "st_file_attributes", 0) & 0x400:
            raise ValueError("resource index has a reparse ancestor")
    try:
        index.stat(follow_symlinks=False)
        index_present = True
    except FileNotFoundError:
        index_present = False
    if index_present:
        if _is_reparse(index):
            raise ValueError("resource index is a reparse point")
        if not index.is_file():
            raise ValueError("resource index is not a file")
        paths = _indexed_paths(index)
    else:
        raise ValueError(f"resource index is missing: {index}")
    rows = []
    for resource_id in RESOURCE_NAMES:
        path = paths[resource_id]
        for ancestor in [*reversed(path.parents), path]:
            try:
                linked = _is_reparse(ancestor)
            except FileNotFoundError as exc:
                raise ValueError(f"indexed resource is missing or not a directory: {resource_id}: {path}") from exc
            if linked:
                raise ValueError(f"indexed resource has a reparse ancestor: {resource_id}: {ancestor}")
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


def _write_report(project_root: Path, output: Path, report: dict) -> None:
    root = Path(os.path.abspath(project_root))
    target = Path(os.path.abspath(output))
    if not _allowed_absolute_path(str(root)) or not _allowed_absolute_path(str(target)):
        raise ValueError("report output must stay outside E:/F: and UNC paths")
    target.relative_to(root / ".project-local")
    for ancestor in [*reversed(target.parents), target]:
        try:
            if _is_reparse(ancestor):
                raise ValueError(f"report output has a reparse ancestor: {ancestor}")
        except FileNotFoundError:
            break
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("project_root", nargs="?", type=Path, default=Path("."))
    parser.add_argument("--purpose", choices=sorted(PURPOSE_TARGET))
    parser.add_argument("--output", type=Path, help="JSON output under project .project-local")
    args = parser.parse_args()
    try:
        report = check_resource_boundaries(args.project_root, purpose=args.purpose)
        if args.output:
            _write_report(args.project_root, args.output, report)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError) as exc:
        print(f"resource boundary check failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
