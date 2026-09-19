"""R6 A03 capability absorption registry contract tests."""
from __future__ import annotations

import json
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "docs/truth/CAPABILITY_ABSORPTION_REGISTRY.yaml"
SCHEMA = ROOT / "config/schemas/capability-absorption-registry.schema.json"


def load_registry() -> dict:
    return yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))


def test_r6_registry_matches_schema_and_uses_rust_truth_owner() -> None:
    payload = load_registry()
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    errors = sorted(
        Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(payload),
        key=lambda error: list(error.path),
    )
    assert not errors, "\n".join(error.message for error in errors)
    assert payload["canonical_truth_owner"] == "ArcheAxis Rust SQLite writer"
    assert len(payload["entries"]) >= 10


def test_r6_registry_ids_and_modes_are_unique_and_explicit() -> None:
    payload = load_registry()
    entries = payload["entries"]
    ids = [entry["capability_id"] for entry in entries]
    assert len(ids) == len(set(ids))
    allowed = set(payload["allowed_absorption_modes"])
    assert allowed == {
        "DIRECT_DEPENDENCY",
        "VENDORED_COMPONENT",
        "CONTRACT_ADAPTER",
        "PYTHON_WORKER",
        "SIDECAR",
        "ALGORITHM_DONOR",
        "UX_DONOR",
        "REFERENCE_ONLY",
        "SELF_BUILD_GAP",
    }
    assert all(entry["absorption_mode"] in allowed for entry in entries)


def test_r6_registry_does_not_claim_unproven_integration() -> None:
    payload = load_registry()
    for entry in payload["entries"]:
        if entry["status"] == "integrated":
            assert entry.get("implementation_evidence"), entry["capability_id"]
        else:
            assert entry["status"] in {
                "candidate",
                "reference",
                "adapter",
                "provider",
                "benchmark",
                "blocked",
                "rejected",
            }
            assert entry["reason_not_absorbed"].strip()
            assert entry["upstream_commit_or_release"] in (None, "UNPINNED_REVIEW_REQUIRED") or entry["upstream_commit_or_release"].strip()
