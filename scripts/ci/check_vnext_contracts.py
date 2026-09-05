#!/usr/bin/env python3
"""vNext contract-package structural gate (contracts-vnext).

Deterministic checks that run on every change touching packages/contracts/**:

- every *.schema.json parses and declares $schema/$id;
- YAML contract files (OpenAPI outline, error catalog) parse;
- compatibility policy exists;
- schema vocabulary files referenced by the worker-protocol are present.

This is a structural gate only; semantic cross-language consistency and
positive/negative examples are owned by the T02 contract freeze and the
tests/contract suite that lands with it.
"""

from __future__ import annotations

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

    if failures:
        print("contracts-vnext check failed:")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("contracts-vnext check passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
