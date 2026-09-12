#!/usr/bin/env python3
"""vNext contract-package structural gate (contracts-vnext).

Deterministic checks that run on every change touching packages/contracts/**:

- every *.schema.json parses and declares $schema/$id;
- YAML contract files (OpenAPI outline, error catalog) parse;
- compatibility policy exists;
- schema vocabulary files referenced by the worker-protocol are present;
- the semantic cross-language part: `scripts/check_language_boundaries.py` checks
  the language boundary against the real tree (who may hold the database) and
  requires Rust, Python and the JSON schemas to name the same protocol major.
  It used to be deferred to a later freeze; it is enforced here now.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONTRACTS = ROOT / "packages" / "contracts" / "v1"

EXPECTED_FILES = {
    "worker-protocol.schema.json",
    "coverage-receipt.schema.json",
    "assessment-vocabulary.schema.json",
    "compatibility-policy.md",
    "openapi-outline.yaml",
    "errors.catalog.yaml",
}

WORKER_PROTOCOL_REFERENCES = (
    # $ref targets inside worker-protocol.schema.json must resolve locally.
)


def language_boundary_result() -> tuple[list[str], dict]:
    """Run the language boundary check that lives in its own module.

    The module is loaded from this script's own location (where the code is) while
    the tree under test is passed in, so the two can never be confused. Loaded by
    path because `scripts/` is not an importable package.
    """
    module_path = Path(__file__).resolve().parents[2] / "scripts" / "check_language_boundaries.py"
    spec = importlib.util.spec_from_file_location("check_language_boundaries", module_path)
    if spec is None or spec.loader is None:  # pragma: no cover - broken checkout
        return [f"cannot load {module_path}"], {}
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.run(ROOT)


def main() -> int:
    failures: list[str] = []

    if not CONTRACTS.is_dir():
        print(f"ERROR: contracts dir missing: {CONTRACTS}")
        return 1

    present = {p.name for p in CONTRACTS.iterdir() if p.is_file()}
    missing = sorted(EXPECTED_FILES - present)
    if missing:
        failures.append(f"missing expected contract files: {', '.join(missing)}")

    for schema_path in sorted(CONTRACTS.glob("*.schema.json")):
        try:
            payload = json.loads(schema_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            failures.append(f"{schema_path.name}: invalid JSON: {exc}")
            continue
        for key in ("$schema", "$id"):
            if not isinstance(payload.get(key), str) or not payload[key]:
                failures.append(f"{schema_path.name}: missing non-empty {key}")

    for yaml_path in ("openapi-outline.yaml", "errors.catalog.yaml"):
        target = CONTRACTS / yaml_path
        if not target.is_file():
            continue
        try:
            import yaml

            payload = yaml.safe_load(target.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001 - report any parse failure
            failures.append(f"{yaml_path}: YAML parse failed: {exc}")
            continue
        if payload is None:
            failures.append(f"{yaml_path}: empty document")

    worker_protocol = CONTRACTS / "worker-protocol.schema.json"
    if worker_protocol.is_file():
        try:
            payload = json.loads(worker_protocol.read_text(encoding="utf-8"))
            raw = worker_protocol.read_text(encoding="utf-8")
            import re

            for ref in sorted(set(re.findall(r'"#/definitions/([A-Za-z0-9_]+)"', raw))):
                if ref not in payload.get("definitions", {}):
                    failures.append(f"worker-protocol: dangling local $ref #{ref}")
        except json.JSONDecodeError as exc:
            failures.append(f"worker-protocol: invalid JSON: {exc}")

    boundary_failures, boundary_detail = language_boundary_result()
    failures += [f"language boundary: {item}" for item in boundary_failures]

    if failures:
        print("contracts-vnext check failed:")
        for item in failures:
            print(f"  - {item}")
        return 1
    major = boundary_detail.get("protocol_version")
    print(
        "contracts-vnext check passed: "
        f"structure ok and the language boundary agrees on protocol major {major}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
