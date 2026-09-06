"""Stage a relocatable Windows Python runtime for the Tauri bundle."""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path


def _ignored(_: str, names: list[str]) -> set[str]:
    return {
        name
        for name in names
        if name in {"__pycache__", "site-packages"} or name.endswith((".pyc", ".pyo"))
    }


def stage_runtime(*, repository: Path, destination: Path) -> Path:
    repository = repository.resolve()
    destination = destination.resolve()
    ignored_root = (repository / ".project-local").resolve()
    if ignored_root not in destination.parents:
        raise RuntimeError("desktop runtime destination must stay under repository .project-local")
    if destination.exists():
        raise RuntimeError(f"desktop runtime destination already exists: {destination}")

    source = Path(sys.base_prefix).resolve()
    python_source = source / "python.exe"
    if not python_source.is_file():
        raise RuntimeError(f"base Python executable is missing: {python_source}")

    python_destination = destination / "runtime" / "python"
    python_destination.parent.mkdir(parents=True, exist_ok=False)
    shutil.copytree(source, python_destination, ignore=_ignored)
    staged_python = python_destination / "python.exe"
    if not staged_python.is_file():
        raise RuntimeError("staged Python executable is missing after copy")
    return staged_python


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()
    staged_python = stage_runtime(repository=args.repository, destination=args.destination)
    print(staged_python)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
