"""Generate the release SBOM (CycloneDX-style JSON) from locked dependency
sources: uv.lock (Python), package-lock.json (frontend), Cargo.lock (Rust)
(AXW-SUP-703).

Local-only generator — run at release time on the exact tagged SHA.

Usage:
  python scripts/release_sbom.py --version 0.5.0 --out release-assets/SBOM.cdx.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import tomllib
from pathlib import Path


def _parse_uv_lock(lock: Path) -> list[dict]:
    data = tomllib.loads(lock.read_text(encoding="utf-8"))
    out = []
    for pkg in data.get("package", []):
        out.append({
            "name": pkg["name"],
            "version": pkg.get("version", ""),
            "purl": f"pkg:pypi/{pkg['name']}@{pkg.get('version', '')}".lower(),
            "type": "python",
        })
    return out


def _parse_npm_lock(lock: Path) -> list[dict]:
    data = json.loads(lock.read_text(encoding="utf-8"))
    out = []
    for name, entry in data.get("packages", {}).items():
        if not name:
            continue
        version = entry.get("version", "")
        out.append({
            "name": name,
            "version": version,
            "purl": f"pkg:npm/{name}@{version}",
            "type": "javascript",
        })
    return out


def _parse_cargo_lock(lock: Path) -> list[dict]:
    text = lock.read_text(encoding="utf-8")
    out = []
    for m in re.finditer(r'\[\[package\]\]\nname = "([^"]+)"\nversion = "([^"]+)"', text):
        name, version = m.group(1), m.group(2)
        out.append({
            "name": name,
            "version": version,
            "purl": f"pkg:cargo/{name}@{version}",
            "type": "rust",
        })
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate release SBOM")
    parser.add_argument("--version", required=True)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--root", default=".", type=Path)
    args = parser.parse_args()

    root = args.root
    components: list[dict] = []
    for lock, parser_fn, kind in (
        (root / "uv.lock", _parse_uv_lock, "python"),
        (root / "desktop/package-lock.json", _parse_npm_lock, "javascript"),
        (root / "desktop/src-tauri/Cargo.lock", _parse_cargo_lock, "rust"),
    ):
        if lock.exists():
            components.extend(parser_fn(lock))
        else:
            print(f"WARNING: {lock} missing; {kind} components skipped")

    components.sort(key=lambda c: (c["type"], c["name"]))
    sbom = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "serialNumber": f"urn:uuid:archeaxis-{args.version}",
        "version": 1,
        "metadata": {
            "component": {
                "type": "application",
                "name": "ArcheAxis Knowledge",
                "version": args.version,
            }
        },
        "components": components,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(sbom, indent=2, ensure_ascii=False), encoding="utf-8")
    digest = hashlib.sha256(args.out.read_bytes()).hexdigest()
    print(f"SBOM written: {args.out} ({len(components)} components)")
    print(f"SHA256: {digest}")


if __name__ == "__main__":
    main()
