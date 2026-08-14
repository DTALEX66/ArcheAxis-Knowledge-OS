"""Generate release-manifest.json — the public asset manifest (AXW-SUP-701).

Differs from release-identity.json (provenance: commit/tree/run/locks) in
that this is the user-facing inventory of published artifacts with sizes
and hashes. Read from a staged release-assets directory; the source of
truth for hashes is SHA256SUMS.txt when present, else computed on the fly.

Usage:
  python scripts/release_manifest.py --version 0.5.0 --assets release-assets \
      --out release-assets/release-manifest.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

CHUNK = 1024 * 256


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(CHUNK), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _kind_for(name: str) -> str:
    if name.endswith("Setup.exe"):
        return "installer"
    if name.endswith("Green.zip"):
        return "green"
    if name.endswith("Portable.zip"):
        return "portable"
    if name.endswith(".whl"):
        return "wheel"
    if name == "SBOM.cdx.json":
        return "sbom"
    if name == "release-identity.json":
        return "identity"
    if name == "release-manifest.json":
        return "manifest"
    if name == "THIRD_PARTY_NOTICES.txt":
        return "notices"
    if name == "SHA256SUMS.txt":
        return "checksums"
    return "other"


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate public release manifest")
    parser.add_argument("--version", required=True)
    parser.add_argument("--assets", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()

    assets = sorted(p for p in args.assets.iterdir() if p.is_file() and p.name != ".gitignore")
    artifacts = []
    for p in assets:
        artifacts.append({
            "name": p.name,
            "kind": _kind_for(p.name),
            "size_bytes": p.stat().st_size,
            "sha256": _sha256(p),
        })
    artifacts.sort(key=lambda a: a["name"])

    manifest = {
        "schema_version": "1.0.0",
        "product": "ArcheAxis Knowledge",
        "version": args.version,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "webview2_mode": "evergreen-bootstrap",
        "capability_packs": [],
        "artifacts": artifacts,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"release-manifest written: {args.out} ({len(artifacts)} artifacts)")


if __name__ == "__main__":
    main()
