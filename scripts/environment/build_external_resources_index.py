"""Build the verified external-resource index from the declared capability manifest.

Why this exists: the manifest declares where each external toolchain/engine/model is expected
to live, and the workers resolve only through that declaration (never by guessing on PATH). When
the declaration is right but nothing checks it against the actual roots, the failure mode is the
one that keeps recurring: an engine is installed, declared, and still reported missing.

This reads `config/environment/capability-requirements.yaml`, resolves every `external_paths`
entry against the declared roots, **runs the probe each entry declares**, and writes a single
machine-readable index (`config/environment/external-resources-index.json`) recording per entry
the resolved location, the required process environment, the binding that was used, and the
measured `verification_level` (REGISTERED / FILE_EXISTS / VERSION_PROBED / RESULT_VERIFIED, plus
explicit `unavailable` / `NOT_RUN` with the reason). A path that cannot be resolved is recorded as
absent, never as absent-by-assumption — and an entry is never credited with a version it did not
answer for itself.

Probing is not reporting: **an index entry is never evidence that a resource is available.** The
level column says what was actually executed on this host. `scripts/workflow/environment_registry.py`
holds the single resolution-and-probe implementation this builder consumes, so the inventory, the
index and the runtime resolver cannot disagree by construction.

Roots, in order: `ARCHEAXIS_EXTERNAL_ROOT`, `OS_EXTERNAL_CONFIG`. A shared resource beside the
external root is reached through a named `sibling_root`, never through a `..` declaration.
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

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.workflow import environment_registry  # noqa: E402  (single probe implementation)


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


def _ascii_reason(text: object) -> str:
    """Keep the tracked index free of host-codepage text.

    A refused loopback connection comes back from Windows as a locale-encoded message, and the
    mojibake in a tracked generated file is unreadable to every reader but this console.
    """
    value = str(text or "")
    try:
        value.encode("ascii")
    except UnicodeEncodeError:
        value = value.encode("ascii", "ignore").decode("ascii")
        value = value or "no answer from the declared lane"
    return value[:300]


def main() -> int:
    root = external_root()
    document = load_manifest()
    siblings = sibling_roots(root, document) if root is not None else {}
    # A probing interpreter needs somewhere to write its sample; the development launcher
    # points this at the run-scoped tmp directory so nothing lands outside the task path.
    workdir = Path(os.environ.get("ARCHEAXIS_RESOURCE_PROBE_WORKDIR", "").strip()
                   or os.path.join(os.environ.get("TEMP", "."), "archeaxis-resource-probe"))
    workdir.mkdir(parents=True, exist_ok=True)

    # With no declared root nothing can be resolved, so nothing is probed: the index then states
    # the declaration and no availability, exactly as before. CI is unaffected either way, and no
    # host without an external root reaches the network or spawns a process.
    report = environment_registry.resolve(MANIFEST, probe=root is not None, workdir=workdir)
    rows_by_id = {row["id"]: row for row in report["capabilities"]}

    rows = []
    missing: list[str] = []
    declared_missing: list[str] = []
    for entry in entries(document):
        declared = [p for p in (entry.get("external_paths") or []) if isinstance(p, str)]
        sibling_root = entry.get("sibling_root")
        base: Path | None = root
        if sibling_root is not None:
            base = siblings.get(str(sibling_root))
            if base is None:
                declared_missing.append(f"{entry.get('name')}: sibling root {sibling_root!r} does not resolve")
        resolutions = []
        for path in declared:
            resolved, exists = resolve(path, base)
            resolutions.append({"declared": path, "resolved": resolved, "exists": exists,
                                **({"sibling_root": sibling_root} if sibling_root is not None else {})})
            if root is not None and not exists:
                declared_missing.append(f"{entry.get('name')}: {path}")
        measured = rows_by_id[f"{entry['category']}/{entry['name']}"]
        level = measured["verification_level"]
        rows.append({
            "resource_id": entry.get("resource_id"),
            "type": entry.get("type"),
            "name": entry.get("name"),
            "category": entry.get("category"),
            "purpose": entry.get("purpose"),
            "platform": entry.get("platform"),
            "host_platform": measured["host_platform"],
            "version_range": entry.get("version_range"),
            "version_identification": entry.get("version_identification"),
            "pinned_version_observed": measured["version_observed"],
            "resolvable_location": measured["declared_location"],
            "resolved_absolute": (resolutions[0]["resolved"] if resolutions and resolutions[0]["resolved"]
                                  else None),
            "binding": measured["binding"],
            "path_also_offers": measured["path_also_offers"],
            "project_entry": entry.get("project_entry"),
            "required_env": measured["required_env"],
            "writability": entry.get("writability"),
            "local_only": entry.get("local_only") is True,
            "required_by": entry.get("required_by", []),
            "healthcheck_command": entry.get("healthcheck_command"),
            "detection": {"kind": measured["probe_kind"], "ceiling": measured["probe_ceiling"],
                          "evidence": measured["probe_evidence"]},
            "available": measured["available"],
            "verification_level": level,
            "ceiling_respected": measured["ceiling_respected"],
            "failure_message": (None if measured["available"] else
                                _ascii_reason(measured["unavailable_reason"]
                                              or entry.get("failure_message"))),
            "code_license": entry.get("license"),
            "asset_license": entry.get("asset_license"),
            "source_url": entry.get("source_url"),
            "fallback": entry.get("fallback"),
            "endpoint": entry.get("endpoint"),
            "external_paths": resolutions,
        })
        if not measured["available"] and level not in ("FILE_EXISTS",):
            missing.append(f"{entry['category']}/{entry['name']}: {level} - "
                           + _ascii_reason(measured["unavailable_reason"]
                                           or entry.get("failure_message") or "not certified"))

    index = {
        "schema": "archeaxis/external-resources-index/v2",
        "generated_by": "scripts/environment/build_external_resources_index.py",
        "probed": root is not None,
        "probe_workdir": str(workdir),
        "manifest": str(MANIFEST.relative_to(ROOT)).replace("\\", "/"),
        "manifest_updated": document.get("updated"),
        "roots_declared_by": list(ROOT_ENV),
        "external_root": str(root) if root else None,
        "root_present": bool(root and root.is_dir()),
        # Which sibling roots resolved, so a reader can tell "the model library was found beside
        # the external root" from "this host has no model library at all".
        "sibling_roots": {name: str(path) for name, path in sorted(siblings.items())},
        # Levels are measured by running the declared probe. An entry is never evidence of
        # availability; this counts what was actually certified on this host.
        "verification_summary": report["verification_summary"],
        "unbound_path_fallback": report["unbound_path_fallback"],
        "entries": rows,
        "not_certified_on_this_host": missing,
        "missing_on_this_host": declared_missing,
        "reporting_rule": ("index existence is not resource availability; REGISTERED/FILE_EXISTS "
                           "say only that a declared location exists, VERSION_PROBED says an "
                           "identity was answered by the entry's own executable or interpreter, "
                           "RESULT_VERIFIED says the declared functional round-trip succeeded, "
                           "and unavailable/NOT_RUN say what could not be run and why"),
    }
    # LF always: the index is a tracked file this host's own test regenerates in place, and platform
    # newlines made every Windows run leave it modified, which makes a dirty-tree development
    # receipt unattributable to a change that did not touch it.
    INDEX.write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
                     newline="\n")

    readable = [row for row in rows if row["external_paths"]]
    print(f"root={index['external_root']} entries={len(rows)} with_external_paths={len(readable)} "
          f"declared_paths_missing={len(declared_missing)} "
          f"levels={json.dumps(index['verification_summary'], ensure_ascii=False)}")
    for row in rows:
        mark = {"RESULT_VERIFIED": "RSLT", "VERSION_PROBED": "VER ", "FILE_EXISTS": "FILE",
                "REGISTERED": "REG ", "NOT_RUN": "NOT_RUN"}.get(row["verification_level"], "UNAVL")
        print(f"  {mark:<7} {row['category']:<10} {row['name']:<38} "
              f"{str(row['binding'] or '-'):<21} {str(row['pinned_version_observed'] or row['failure_message'] or '')[:64]}")
    if root is None:
        print("NOTE: no external root in the environment; the index records declared paths only")
    return 0


if __name__ == "__main__":
    sys.exit(main())
