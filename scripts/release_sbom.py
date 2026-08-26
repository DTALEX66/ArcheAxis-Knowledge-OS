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


class MissingCoverageError(RuntimeError):
    """Raised when a canonical release dependency source is absent."""


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
    for package_path, entry in data.get("packages", {}).items():
        if not package_path:
            continue
        name = package_path.rsplit("node_modules/", 1)[-1]
        version = entry.get("version", "")
        out.append({
            "name": name,
            "version": version,
            "purl": f"pkg:npm/{name}@{version}",
            "type": "javascript",
            "license": entry.get("license", "") or "",
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


def _licenses_from_uv_lock(lock: Path) -> dict[str, str]:
    """name -> license id best effort from uv.lock package entries."""
    data = tomllib.loads(lock.read_text(encoding="utf-8"))
    return {pkg["name"]: (pkg.get("license") or "") for pkg in data.get("package", [])}


def _licenses_from_components(components: list[dict]) -> dict[str, str]:
    """name -> license id from component metadata (npm lock license field)."""
    return {c["name"]: (c.get("license") or "") for c in components if c.get("license")}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _vendored_component(
    *, name: str, version: str, kind: str, path: Path, license_id: str
) -> dict:
    return {
        "name": name,
        "version": version,
        "purl": f"pkg:generic/{name}@{version}",
        "type": kind,
        "license": license_id,
        "hashes": [{"alg": "SHA-256", "content": _sha256(path)}],
        "path": path.as_posix(),
    }


def collect_components(root: Path) -> list[dict]:
    """Collect canonical locks plus shipped vendored/model assets."""
    required = (
        (root / "uv.lock", _parse_uv_lock),
        (root / "frontend/package-lock.json", _parse_npm_lock),
        (root / "src-tauri/Cargo.lock", _parse_cargo_lock),
    )
    missing = [path.relative_to(root).as_posix() for path, _ in required if not path.is_file()]
    if missing:
        raise MissingCoverageError("missing canonical SBOM sources: " + ", ".join(missing))

    components: list[dict] = []
    for lock, parser_fn in required:
        components.extend(parser_fn(lock))
    for lock, parser_fn in (
        (root / "desktop/package-lock.json", _parse_npm_lock),
        (root / "desktop/src-tauri/Cargo.lock", _parse_cargo_lock),
    ):
        if lock.is_file():
            components.extend(parser_fn(lock))

    pdf_asset = root / "app/workspace/ui/assets/pdf.mjs"
    pdf_worker = root / "app/workspace/ui/assets/pdf.worker.mjs"
    pdf_license = root / "app/workspace/ui/assets/licenses/pdfjs-6.2.108-LICENSE.txt"
    magika_model = root / "shared/models/magika/model.onnx"
    magika_license = root / "shared/models/magika/LICENSE"
    vendored_required = (pdf_asset, pdf_worker, pdf_license, magika_model, magika_license)
    missing_vendored = [
        path.relative_to(root).as_posix() for path in vendored_required if not path.is_file()
    ]
    if missing_vendored:
        raise MissingCoverageError("missing vendored SBOM sources: " + ", ".join(missing_vendored))
    components.extend(
        [
            _vendored_component(
                name="pdfjs", version="6.2.108", kind="vendored-javascript",
                path=pdf_asset, license_id="Apache-2.0",
            ),
            _vendored_component(
                name="magika-model", version="0.6.3", kind="model",
                path=magika_model, license_id="Apache-2.0",
            ),
        ]
    )

    deduped = {component["purl"]: component for component in components}
    return sorted(deduped.values(), key=lambda component: (component["type"], component["name"]))


def _write_notices(components: list[dict], licenses: dict[str, str], out: Path) -> None:
    """THIRD_PARTY_NOTICES.txt: one section per component with license id."""
    lines = [
        "THIRD PARTY NOTICES",
        "===================",
        "",
        "ArcheAxis Knowledge bundles third-party components. Licenses below are",
        "declared by each package's metadata (best effort); \"unknown\" means the",
        "lock file did not declare a license. Full per-file verification: see",
        "SBOM.cdx.json (generated from locked dependency sources).",
        "",
    ]
    for comp in components:
        lic = licenses.get(comp["name"], "") or "unknown"
        lines.append(f"- {comp['name']} {comp['version']} [{comp['type']}] — {lic}")
    lines.append("")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"NOTICES written: {out} ({len(components)} entries)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate release SBOM")
    parser.add_argument("--version", required=True)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--notices-out", type=Path, help="THIRD_PARTY_NOTICES.txt path")
    parser.add_argument("--root", default=".", type=Path)
    args = parser.parse_args()

    root = args.root
    components = collect_components(root)
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
    if args.notices_out is not None:
        uv_lock = root / "uv.lock"
        licenses = _licenses_from_uv_lock(uv_lock) if uv_lock.exists() else {}
        licenses.update(_licenses_from_components(components))
        _write_notices(components, licenses, args.notices_out)


if __name__ == "__main__":
    main()
