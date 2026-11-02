"""Stage a relocatable Windows Python runtime for the Tauri bundle."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

if __package__:
    from scripts.release import runtime_growth as growth
else:
    spec = importlib.util.spec_from_file_location("desktop_runtime_growth",
        Path(__file__).resolve().parents[2] / "scripts/release/runtime_growth.py")
    growth = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(growth)


def _ignored(_: str, names: list[str]) -> set[str]:
    return {
        name
        for name in names
        if name in {"__pycache__", "site-packages"} or name.endswith((".pyc", ".pyo"))
    }


def runtime_inputs(source, *, interpreter_binding=None):
    source = growth.safe(source)
    def validate(path):
        if any(growth.portable.storage_report.protected_name(part) for part in path.relative_to(source).parts):
            raise ValueError("protected base Python donor member")
    return growth.snapshot(source, _ignored, validate=validate, interpreter_binding=interpreter_binding)


def stage_runtime(*, repository: Path, destination: Path, _backend_in_place: bool = False,
                  storage_context=None) -> Path:
    repository = growth.safe(repository)
    destination = growth.safe(destination)
    ignored_root = (repository / ".project-local").resolve()
    if ignored_root not in destination.parents:
        raise RuntimeError("desktop runtime destination must stay under repository .project-local")
    if _backend_in_place:
        # The authoritative stager just exclusively created this empty root.
        if not destination.is_dir() or any(destination.iterdir()):
            raise RuntimeError("in-place runtime requires a newly created empty candidate root")
    elif destination.exists():
        raise RuntimeError(f"desktop runtime destination already exists: {destination}")

    binding = growth.interpreter_source()
    source = Path(binding["physical_root"])
    python_source = source / "python.exe"
    if not python_source.is_file():
        raise RuntimeError(f"base Python executable is missing: {python_source}")

    python_destination = destination / "runtime" if _backend_in_place else destination / "runtime/python"
    inputs = runtime_inputs(source, interpreter_binding=binding)
    with growth.batch(destination, inputs, sum(item["bytes"] for item in inputs.values()), storage_context,
                      interpreter_binding=binding):
        python_destination.parent.mkdir(parents=True, exist_ok=_backend_in_place)
        growth.copytree(source, python_destination, ignore=_ignored, inputs=inputs)
        if not _backend_in_place:
            with (destination / "python-source-binding.json").open("x", encoding="utf-8") as receipt:
                json.dump(binding, receipt, indent=2)
                receipt.write("\n")
    staged_python = python_destination / "python.exe"
    if not staged_python.is_file():
        raise RuntimeError("staged Python executable is missing after copy")
    return staged_python


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--run-id")
    parser.add_argument("--storage-purpose")
    parser.add_argument("--storage-sharing")
    parser.add_argument("--storage-retention-reason")
    args = parser.parse_args()
    context = None
    if args.run_id:
        context = {"paths": growth.portable.dev.layout(args.repository, args.run_id),
                   "purpose": args.storage_purpose, "sharing": args.storage_sharing,
                   "retention_reason": args.storage_retention_reason}
    try:
        staged_python = stage_runtime(repository=args.repository, destination=args.destination, storage_context=context)
    except growth.portable.GrowthReviewRequiredError as error:
        print(str(error), file=sys.stderr)
        return 2
    print(staged_python)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
