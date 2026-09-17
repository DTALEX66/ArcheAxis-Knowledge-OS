#!/usr/bin/env python3
"""Validate an approved, read-only pipeline source root.

This is a metadata-only gate.  It never opens source files and never writes to
the selected corpus; receipts must be routed to the project's .project-local.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
# Shared resources live beside the checkout.  Deriving these paths avoids
# embedding a machine-specific absolute root while preserving the exact
# boundary on this workstation.
SHARED_ROOT = ROOT.parent
CESHI = SHARED_ROOT / "ceshi"
REAL_LIBRARY = SHARED_ROOT / "资料库"
GREEN_DATA = SHARED_ROOT / "ArcheAxis.Knowledge.Green-x64" / "data"
FORBIDDEN_ROOTS = (SHARED_ROOT / "Model library",
                   SHARED_ROOT / "OS External Configuration")


def _absolute(path: Path) -> Path:
    return Path(os.path.abspath(path))


def _under(candidate: Path, parent: Path) -> bool:
    try:
        candidate.resolve().relative_to(parent.resolve())
    except ValueError:
        return False
    return True


def validate_source(path: Path) -> Path:
    candidate = _absolute(path)
    if candidate.drive.upper() in {"E:", "F:"} or str(candidate).startswith("\\\\"):
        raise ValueError("protected drive or UNC source root")
    if not candidate.is_dir():
        raise ValueError(f"source root is not a directory: {candidate}")
    forbidden_roots = (*FORBIDDEN_ROOTS, REAL_LIBRARY, GREEN_DATA)
    if any(_under(candidate, forbidden) for forbidden in forbidden_roots):
        raise ValueError("source root is a real library, Green data, model library, or external toolchain")
    if not _under(candidate, CESHI) and not _under(candidate, ROOT / ".project-local"):
        raise ValueError("source root must be under approved ceshi or project .project-local")
    return candidate


def preflight(path: Path) -> dict:
    source = validate_source(path)
    extensions: Counter[str] = Counter()
    file_count = 0
    directory_count = 0
    for _directory, directories, files in os.walk(source):
        directory_count += len(directories)
        file_count += len(files)
        extensions.update(Path(name).suffix.casefold() or "<none>" for name in files)
    return {
        "schema": "archeaxis.pipeline-source-preflight/v1",
        "status": "APPROVED_READ_ONLY_SOURCE",
        "source_root": str(source),
        "source_class": "project_test_corpus" if _under(source, CESHI) else "project_local_fixture",
        "file_count": file_count,
        "directory_count": directory_count,
        "extensions": dict(sorted(extensions.items())),
        "source_files_opened": False,
        "source_files_modified": False,
        "real_library_excluded": True,
        "green_data_excluded": True,
        "output_policy": "route receipts to project .project-local",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--output-json", type=Path)
    args = parser.parse_args()
    try:
        report = preflight(args.source_root)
        encoded = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
        if args.output_json:
            output = _absolute(args.output_json)
            if not _under(output, ROOT / ".project-local"):
                raise ValueError("output must stay inside .project-local")
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(encoded, encoding="utf-8")
        else:
            print(encoded, end="")
    except (OSError, ValueError) as exc:
        print(f"source_preflight: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
