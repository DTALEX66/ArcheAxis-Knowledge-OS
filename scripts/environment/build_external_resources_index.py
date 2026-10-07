"""Build the verified external-resource index from the declared capability manifest.

Why this exists: the manifest declares where each external toolchain/engine/model is expected
to live, and the workers resolve only through that declaration (never by guessing on PATH). When
the declaration is right but nothing checks it against the actual roots, the failure mode is the
one that keeps recurring: an engine is installed, declared, and still reported missing.

This reads `config/environment/capability-requirements.yaml`, resolves every `external_paths`
entry against the declared roots, and writes a single machine-readable index
(`config/environment/external-resources-index.json`) that records, per entry, the exact resolved
path and whether it exists *on this host*. A path that cannot be resolved is recorded as MISSING,
never as absent-by-assumption.

Roots, in order: `ARCHEAXIS_EXTERNAL_ROOT`, `OS_EXTERNAL_CONFIG`. A declared path beginning with
`../` is resolved against the parent of that root (this is how the model library is declared).
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "config" / "environment" / "capability-requirements.yaml"
INDEX = ROOT / "config" / "environment" / "external-resources-index.json"
ROOT_ENV = ("ARCHEAXIS_EXTERNAL_ROOT", "OS_EXTERNAL_CONFIG")


def external_root() -> Path | None:
    for name in ROOT_ENV:
        raw = os.environ.get(name, "").strip()
        if raw:
            candidate = Path(raw)
            if candidate.is_absolute():
                return candidate
    return None


def load_manifest() -> dict:
    import yaml
    return yaml.safe_load(MANIFEST.read_text(encoding="utf-8")) or {}


def entries(document: dict) -> list[dict]:
    found: list[dict] = []
    for category, group in (document.get("capabilities") or {}).items():
        for entry in group or []:
            if isinstance(entry, dict):
                found.append({**entry, "category": category})
    return found


def sibling_roots(root: Path, document: dict) -> dict[str, Path]:
    """The declared sibling roots, resolved — the same bounded rule the runtime resolver applies.

    This reader used to resolve the `../Model library/...` form itself, so the index recorded
    `exists: true` for a model the worker could not reach: the runtime rejects `..`, and an index
    that disagrees with the runtime is worse than no index, because it certifies the very failure
    it was built to catch. Both now resolve through a root the manifest names.
    """
    declared = document.get("sibling_roots") or {}
    resolved: dict[str, Path] = {}
    for name, relative in declared.items():
        if not isinstance(name, str) or not isinstance(relative, str):
            continue
        parts = Path(relative).parts
        if len(parts) != 2 or parts[0] != ".." or Path(relative).is_absolute():
            continue
        candidate = (root / Path(relative)).resolve()
        if candidate.is_dir():
            resolved[name] = candidate
    return resolved


def resolve(declared: str, base: Path | None) -> tuple[str, bool]:
    """The exact path a declaration names, and whether it exists — inside one declared root."""
    if base is None:
        return "", False
    relative = Path(declared)
    if relative.is_absolute() or ".." in relative.parts:
        return "", False
    candidate = (base / relative).resolve()
    return str(candidate), candidate.exists()


def main() -> int:
    root = external_root()
    document = load_manifest()
    siblings = sibling_roots(root, document) if root is not None else {}
    rows = []
    missing: list[str] = []
    for entry in entries(document):
        declared = [p for p in (entry.get("external_paths") or []) if isinstance(p, str)]
        sibling_root = entry.get("sibling_root")
        base: Path | None = root
        if sibling_root is not None:
            base = siblings.get(str(sibling_root))
            if base is None:
                missing.append(f"{entry.get('name')}: sibling root {sibling_root!r} does not resolve")
        resolutions = []
        for path in declared:
            resolved, exists = resolve(path, base)
            resolutions.append({"declared": path, "resolved": resolved, "exists": exists,
                                **({"sibling_root": sibling_root} if sibling_root is not None else {})})
            if root is not None and not exists:
                missing.append(f"{entry.get('name')}: {path}")
        rows.append({
            "name": entry.get("name"),
            "category": entry.get("category"),
            "purpose": entry.get("purpose"),
            "local_only": entry.get("local_only") is True,
            "healthcheck_command": entry.get("healthcheck_command"),
            "external_paths": resolutions,
        })
    index = {
        "schema": "archeaxis/external-resources-index/v1",
        "generated_by": "scripts/environment/build_external_resources_index.py",
        "manifest": str(MANIFEST.relative_to(ROOT)).replace("\\", "/"),
        "roots_declared_by": list(ROOT_ENV),
        "external_root": str(root) if root else None,
        "root_present": bool(root and root.is_dir()),
        # Which sibling roots resolved, so a reader can tell "the model library was found beside
        # the external root" from "this host has no model library at all".
        "sibling_roots": {name: str(path) for name, path in sorted(siblings.items())},
        "entries": rows,
        "missing_on_this_host": missing,
    }
    INDEX.write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    readable = [row for row in rows if row["external_paths"]]
    print(f"root={index['external_root']} entries={len(rows)} with_external_paths={len(readable)} missing={len(missing)}")
    for row in readable:
        for resolution in row["external_paths"]:
            mark = "OK " if resolution["exists"] else "MISS"
            print(f"  {mark} {row['category']:<10} {row['name']:<34} {resolution['declared']}")
    if root is None:
        print("NOTE: no external root in the environment; the index records declared paths only")
    return 0


if __name__ == "__main__":
    sys.exit(main())
