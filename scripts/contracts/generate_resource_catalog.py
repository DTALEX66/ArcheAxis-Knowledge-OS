"""Lossless read-only resource projection; no donor reclassification or activation."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

CROSSWALK = "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json"
QUALIFICATION = "docs/current/AAOS-RESOURCE-QUALIFICATION-20261010.json"
LEDGER = "docs/truth/SUPPLY_CHAIN_LEDGER.json"
FREEZE = "docs/taskpacks/aaos-ui-first-20261009/FREEZE-REGISTER.json"
TARGET = "frontend/src/api/generated/resource-catalog.ts"
CLASSES = ("enableable_plugin", "absorbed_algorithm", "ux_donor", "format_spec", "base_dependency", "future_candidate", "not_adopted")


def load(path: Path):
    raw = path.read_bytes()
    return json.loads(raw), hashlib.sha256(raw).hexdigest()


PUBLIC_ROOT_FILES = frozenset({"Cargo.lock", "LICENSE", "THIRD_PARTY_NOTICES.md", "pyproject.toml", "uv.lock"})
PUBLIC_ROOT_DIRS = frozenset({"crates", "docs", "frontend", "packages", "scripts", "shared", "src-tauri", "tests", "config"})
PRIVATE_PARTS = frozenset({"credentials", "credential", "secrets", "secret", "private", "sessions", "session", "memory", "memories", "auth", "cookies", "tokens", "node_modules", "data", "target", "dist"})


def qualification_source_refs(value):
    """Visit recorded references at every depth, including top-level sources."""
    if isinstance(value, dict):
        if "sha256" in value:
            if "path" not in value:
                raise ValueError("Qualification source reference requires path/sha256")
            yield value
        for child in value.values():
            yield from qualification_source_refs(child)
    elif isinstance(value, list):
        for child in value:
            yield from qualification_source_refs(child)


def public_source_path(root: Path, name):
    if not isinstance(name, str) or not name or "\\" in name or ":" in name:
        raise ValueError("Qualification source path must be public project-relative")
    parts = name.split("/")
    if any(part in ("", ".", "..") or part.startswith(".") or part.casefold() in PRIVATE_PARTS
           or part.casefold().endswith((".pem", ".key", ".pfx", ".p12")) for part in parts):
        raise ValueError("Qualification source path must be public project-relative")
    if parts[0] not in PUBLIC_ROOT_DIRS and name not in PUBLIC_ROOT_FILES:
        raise ValueError("Qualification source path must be public project-relative")
    source = root / name
    try:
        resolved_name = source.resolve().relative_to(root.resolve()).as_posix()
    except ValueError as error:
        raise ValueError("Qualification source path escapes project") from error
    # Resolve links before reading: a public alias must not expose private bytes.
    if resolved_name != name:
        public_source_path(root, resolved_name)
    return source


def validate_qualification_sources(root: Path, qualification):
    checked = {}
    for reference in qualification_source_refs(qualification):
        source = public_source_path(root, reference["path"])
        digest = reference["sha256"]
        if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            raise ValueError("Qualification source SHA must be lowercase SHA-256")
        if not source.is_file():
            raise ValueError(f"Qualification source missing: {reference['path']}")
        actual = checked.get(reference["path"])
        if actual is None:
            actual = hashlib.sha256(source.read_bytes()).hexdigest()
            checked[reference["path"]] = actual
        if actual != digest:
            raise ValueError(f"Qualification source drift: {reference['path']}")


def build(root: Path, overlay: Path | None = None):
    crosswalk, cross_sha = load(root / CROSSWALK)
    qualification, qualification_sha = load(overlay or root / QUALIFICATION)
    ledger, ledger_sha = load(root / LEDGER)
    freeze, freeze_sha = load(root / FREEZE)
    entries = crosswalk["entries"]
    keys = [row["stable_key"] for row in entries]
    if len(keys) != 68 or len(set(keys)) != 68:
        raise ValueError("Crosswalk must preserve exactly 68 unique stable keys")
    if any(row["surface_class"] not in CLASSES for row in entries):
        raise ValueError("Unknown surface class")
    if sum(len(row["conflicts"]) for row in entries) != crosswalk["conflict_count"] or crosswalk["conflict_count"] != 115:
        raise ValueError("Original 115 conflicts must be retained")
    if sum(bool(row["conflicts"]) for row in entries) != crosswalk["entries_with_conflicts"]:
        raise ValueError("Conflict row count differs")
    if qualification["schema"] != "archeaxis.resource-qualification-overlay/v1":
        raise ValueError("Wrong qualification schema")
    qualification_keys = [row["stable_key"] for row in qualification["entries"]]
    if len(set(qualification_keys)) != len(qualification_keys) or set(qualification_keys) != set(keys):
        raise ValueError("Qualification must cover each original stable key exactly once")
    if not set(qualification["selected_scope"]).issubset(keys):
        raise ValueError("Selected scope contains an unknown donor")
    for row in qualification["entries"]:
        for name in ("version", "license", "permissions", "runtime", "qualification"):
            evidence = row["evidence"][name]
            if not isinstance(evidence["state"], str) or not isinstance(evidence["source_refs"], list):
                raise ValueError("Evidence state/source references required")
            if "value" not in evidence:
                raise ValueError("Evidence value cannot be silently dropped")
    qualification_by_key = {row["stable_key"]: row for row in qualification["entries"]}
    ledger_by_id = {row["id"]: row for row in ledger["components"]}
    if len(ledger_by_id) != len(ledger["components"]):
        raise ValueError("Ledger IDs must be unique")
    projected = []
    for row in entries:
        reference = row["namespaces"].get("supply_chain_ledger")
        ledger_row = ledger_by_id.get(reference["id"]) if reference else None
        if reference and ledger_row is None:
            raise ValueError("Declared ledger reference is missing")
        projected.append({
            "stable_key": row["stable_key"], "display_names": row["display_names"],
            "surface_class": row["surface_class"], "absorption_mode": row["absorption_mode"],
            "classification_reason": row["surface_class_reason"],
            "declared_runtime_route": row["route_binding"].get("named_route"),
            "original_surface": row, "ledger": ledger_row,
            "qualification": qualification_by_key[row["stable_key"]],
        })
    validate_qualification_sources(root, qualification)
    return {
        "schema": "archeaxis.resource-catalog-projection/v1",
        "sources": [{"path": path, "sha256": digest} for path, digest in [(CROSSWALK, cross_sha), (QUALIFICATION, qualification_sha), (LEDGER, ledger_sha), (FREEZE, freeze_sha)]],
        "crosswalk_metadata": {key: value for key, value in crosswalk.items() if key != "entries"},
        "qualification_metadata": {key: value for key, value in qualification.items() if key != "entries"},
        "freeze_register": freeze,
        "entries": projected,
    }


TYPES = '''export type ResourceJson = null | boolean | number | string | ResourceJson[] | { [key: string]: ResourceJson };
export type ResourceObject = { [key: string]: ResourceJson };
export type ResourceClass = "enableable_plugin" | "absorbed_algorithm" | "ux_donor" | "format_spec" | "base_dependency" | "future_candidate" | "not_adopted";
export type ResourceEvidence = { state: string; value: ResourceJson; source_refs: { path: string; sha256: string }[] };
export type ResourceQualification = { stable_key: string; disposition: string; reason: string; activation: { state: string; conditions: ResourceJson; scope: ResourceJson }; evidence: { version: ResourceEvidence; license: ResourceEvidence; permissions: ResourceEvidence; runtime: ResourceEvidence; qualification: ResourceEvidence; source_refs: ResourceJson }; [key: string]: ResourceJson };
export type ResourceEntry = { stable_key: string; display_names: string[]; surface_class: ResourceClass; absorption_mode: string; classification_reason: string; declared_runtime_route: string | null; original_surface: ResourceObject; ledger: ResourceObject | null; qualification: ResourceQualification };
export type ResourceCatalog = { schema: string; sources: { path: string; sha256: string }[]; crosswalk_metadata: ResourceObject; qualification_metadata: ResourceObject; freeze_register: ResourceObject; entries: ResourceEntry[] };
'''


def generate(payload):
    return "// Generated from the recorded crosswalk/qualification/ledger/freeze bytes. No runtime authority.\n" + TYPES + "export const RESOURCE_CATALOG: ResourceCatalog = " + json.dumps(payload, ensure_ascii=False, indent=2) + ";\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--overlay", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    output = generate(build(args.root, args.overlay))
    target = args.output or args.root / TARGET
    if args.check:
        if not target.is_file() or target.read_text(encoding="utf-8") != output:
            raise SystemExit("Resource projection stale; regenerate only from canonical sources")
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(output, encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
