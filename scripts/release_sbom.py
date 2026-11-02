"""Generate the release SBOM (CycloneDX-style JSON) from locked dependency
sources: uv.lock (Python), package-lock.json (frontend), Cargo.lock (Rust)
(AXW-SUP-703).

Local-only generator — run at release time on the exact tagged SHA.

Usage:
  python scripts/release_sbom.py --version 0.5.0 --out .project-local/build/release-assets/SBOM.cdx.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import tomllib
from pathlib import Path, PurePosixPath


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


# These are source-reuse identities, not an assertion about a release payload.
# Each manifest is itself pinned before any member identities are trusted.
_OPENMAIC = "services/learning-providers/openmaic/vendor"
_DEEPTUTOR = "services/learning-providers/deeptutor"
_OPENMAIC_LICENSE = "ba252563743227138231604c9138dd400faca5a10c3cf206b466e5466c565a19"
SOURCE_ONLY_COMPONENTS = (
    {
        "name": "DeepTutor", "version": "1.7.1", "license": "Apache-2.0",
        "purl": "pkg:generic/deeptutor@1.7.1?scope=source-only", "type": "vendored-python",
        "files": {
            f"{_DEEPTUTOR}/upstream/answers.py": "fdfbaee6cd0fa2c0f31de9a792e220e6989434fc1f44359db3e6afc62cd2472f",
            f"{_DEEPTUTOR}/upstream/importing.py": "9ee4dd1abfa150fd81c3e3e31e2321761bab05509f6e4a5fca555ede2bbfd260",
            f"{_DEEPTUTOR}/upstream/question_pipeline.py": "b0e11748806225b286cff92a2dbf2f5722aa4538c8dc42138fa81def42cc392f",
            f"{_DEEPTUTOR}/upstream/question_pipeline.en.yaml": "148ccde0f60f2d96724e1cbaa3db1f4bc676e87ed086bda1dac1bcdc27f2ae89",
            f"{_DEEPTUTOR}/upstream/question_pipeline.zh.yaml": "ef14102e36f9c156528336b48112a3e8336269fdea5a3517119c651707a8ae58",
            f"{_DEEPTUTOR}/upstream/question_language.py": "7ef192bca1cc8d91c838a4601847a2b40d09becca704e5f74ed65af855f55ce3",
            f"{_DEEPTUTOR}/upstream/teaching.py": "79839b2d29c16146ba4ca6eba438941eacdd8cef2920ebca81e8541305013b4b",
            f"{_DEEPTUTOR}/upstream/learning_models.py": "97d4cd701700c31aaf421900fa3b403ac1b5fe334e70d884a5159d998c4b8507",
            f"{_DEEPTUTOR}/upstream/agentic_labels.py": "5b72f0efb922741b8dde7c9082c12778dfb21cf087c431d872d7f4c806705c05",
            f"{_DEEPTUTOR}/LICENSE": "cd2f54e1e5066644023203dcbd956776a9f4ef6eb8b6225afe1ffa2d380fede4",
            f"{_DEEPTUTOR}/upstream/THIRD_PARTY_NOTICES.md": "d59dc01b43d1916db9418bc1ebcc213a4859047dc07e2766c4234391f9db033c",
        },
        "license_files": [f"{_DEEPTUTOR}/LICENSE", f"{_DEEPTUTOR}/upstream/THIRD_PARTY_NOTICES.md"],
    },
    {
        "name": "@openmaic/generation", "version": "0.3.28", "license": "MIT",
        "purl": "pkg:npm/%40openmaic/generation@0.3.28?scope=source-only", "type": "vendored-javascript",
        "license_review": ("Upstream declares MIT; interactive-post-processor.ts identifies a port from "
                           "learn-your-way/concept_to_html.py. The referenced original and any additional "
                           "terms have not been verified."),
        "files": {
            f"{_OPENMAIC}/generation-0.3.28/scene-builder.ts": "e550ed528f9a017ea0fa1f9cc4a01f7eb22d541d5ada067967d3434393d1bf0a",
            f"{_OPENMAIC}/generation-0.3.28/LICENSE": _OPENMAIC_LICENSE,
            f"{_OPENMAIC}/generation-0.3.28-quiz/quiz-functions.ts": "4d051a9365509bcedfd10ac7a66e9e5ed4ba58e19d46909e7e8d2b8489a3dfa6",
            f"{_OPENMAIC}/generation-0.3.28-quiz-actions/quiz-actions-functions.ts": "ed230c8d45e795cbfdd2955165d259243112efc00e273dcb81ab06988ffcaf25",
        },
        "manifests": {
            f"{_OPENMAIC}/generation-0.3.28-outline/ORIGINALS.json": "e9e5396d1676de1bc25e3f9df81f65b5a52724ae9e3bcaf49fb109b82051e9d6",
            f"{_OPENMAIC}/generation-0.3.28-quiz/ORIGINALS.json": "54499d6b7840d2968a3b02d11a27ee70ceed92d865efe702882015044b597de8",
            f"{_OPENMAIC}/generation-0.3.28-quiz-actions/ORIGINALS.json": "8e4b62a07c4daf3085fadd126396e467084a7dd35c9c5e9159f863fb527e655a",
            f"{_OPENMAIC}/scene-content-0.3.28-original/generation/ORIGINALS.json": "5679a80166d41114448ab35a1e2128a56baca7c9611218af590c81f3889d1ce3",
        },
        "license_files": [f"{_OPENMAIC}/{item}/LICENSE" for item in (
            "generation-0.3.28", "generation-0.3.28-outline",
            "generation-0.3.28-quiz", "generation-0.3.28-quiz-actions",
            "scene-content-0.3.28-original/generation")],
    },
    {
        "name": "@openmaic/dsl", "version": "0.12.0", "license": "MIT",
        "purl": "pkg:npm/%40openmaic/dsl@0.12.0?scope=source-only", "type": "vendored-javascript",
        "files": {},
        "manifests": {
            f"{_OPENMAIC}/dsl-0.12.0-actions/ORIGINALS.json": "ef4102ca18abefcf0c5956a8caa356236d60d248416b1b666cfc6daa99066dc0",
            f"{_OPENMAIC}/scene-content-0.3.28-original/dsl/ORIGINALS.json": "c7564a5741c0807834ebcf77779a50590b927fa8b7e93f49494d1ef8eac6c317",
        },
        "license_files": [f"{_OPENMAIC}/dsl-0.12.0-actions/LICENSE",
                          f"{_OPENMAIC}/scene-content-0.3.28-original/dsl/LICENSE"],
    },
    {
        "name": "@openmaic/geometry", "version": "0.1.0", "license": "MIT",
        "purl": "pkg:npm/%40openmaic/geometry@0.1.0?scope=source-only", "type": "vendored-javascript",
        "files": {},
        "manifests": {f"{_OPENMAIC}/scene-content-0.3.28-original/geometry/ORIGINALS.json": "07c0ce415204aff5074fb3c74f6bd4f12e80bd4af0f919def3f715aede048f01"},
        "license_files": [f"{_OPENMAIC}/scene-content-0.3.28-original/geometry/LICENSE"],
    },
    *(
        {
            "name": name, "version": version, "license": license_id,
            "purl": f"pkg:npm/{name}@{version}?scope=source-only", "type": "vendored-javascript",
            "files": {},
            "manifests": {f"{_OPENMAIC}/npm/{name}-{version}/SOURCE.json": manifest_sha},
            "license_files": [f"{_OPENMAIC}/npm/{name}-{version}/{license_name}"] + (
                [f"{_OPENMAIC}/npm/source-map-js-1.2.1/lib/base64-vlq.js"]
                if (name, version) == ("source-map-js", "1.2.1") else []
            ),
        }
        for name, version, license_id, license_name, manifest_sha in (
            ("jsonrepair", "3.13.3", "ISC", "LICENSE.md", "11533c9ff27380455269407795ca6dd72a9c997ae4b4efa0285110ac23e60453"),
            ("nanoid", "5.1.14", "MIT", "LICENSE", "48edba08227f52a6b72e802292de3833a1ae82170c90ad836641f5b5b582cc75"),
            ("partial-json", "0.1.7", "MIT", "LICENSE", "b2513602f3097aa7f6d090fa50290b9f7e00603a61a71c20882f5fb0963e5403"),
            ("postcss-value-parser", "4.2.0", "MIT", "LICENSE", "d7b344a5bd2494aea12255918bf24e4dd4a34ba80a06d9bb399ea5469e145607"),
            ("es-module-lexer", "2.0.0", "MIT", "LICENSE", "2c222673e20d94f84a03d8a277df5a91c842053a6e991a44cec6b62e8aa45d71"),
            ("entities", "6.0.1", "BSD-2-Clause", "LICENSE", "2931e2cb2561ccdd29a1c14eb11527e983138ecc2dc31021ede7123f95d11bf6"),
            ("svg-pathdata", "8.0.0", "MIT", "LICENSE", "2d619e3e74942771048204c6740274bfb04e5eb544cde3ad11da982aa121481b"),
            ("tinycolor2", "1.6.0", "MIT", "LICENSE", "523960b84b6cde69b861ec911da3d58fdc75035f1bcf825ca75963402c958bfb"),
            ("parse5", "8.0.1", "MIT", "LICENSE", "fb5a2c507c9c2d2c59073df562e2131ada5860b3370ebc9508762bc4be1cad30"),
            ("entities", "8.0.0", "BSD-2-Clause", "LICENSE", "91fd19349c025f903464fe8d0e4ab5464708db4386024dbd9957c273c91a422c"),
            ("commander", "8.3.0", "MIT", "LICENSE", "bd5a268b5062ffa660dd441121059d453d193c681522ca5e490232399d093fea"),
            ("postcss", "8.5.23", "MIT", "LICENSE", "b0e2faa80c9539b2f9b5d5e8e67b328dbf421130a02cd1695a5da659447ca61f"),
            ("nanoid", "3.3.19", "MIT", "LICENSE", "3495da1b2b7f1c42952fc5090cd0eb818f207eb70a9f2083837ffedfa6dbdcf4"),
            ("picocolors", "1.1.1", "ISC", "LICENSE", "04718da4913e9256b832a9227dc9ee4a875e5f7f7b57c44592caadcc612bb057"),
            ("source-map-js", "1.2.1", "BSD-3-Clause", "LICENSE", "20eaf7236bed35a6bb8a316852680637c369ea7a3c0ec6aabc3fb51eb47c7bbe"),
        )
    ),
)


def _source_path(relative: str) -> PurePosixPath:
    path = PurePosixPath(relative)
    if (not relative or "\\" in relative or ":" in relative or "\x00" in relative or path.is_absolute()
            or any(part in (".", "..") for part in path.parts)
            or path.as_posix() != relative):
        raise MissingCoverageError(f"invalid source-only path: {relative}")
    return path


def _native_path(path: Path) -> Path:
    """Use extended Windows paths only for file operations, after lexical validation."""
    if os.name != "nt":
        return path
    text = os.path.abspath(path)
    if text.startswith("\\\\?\\"):
        return Path(text)
    if text.startswith("\\\\"):
        return Path("\\\\?\\UNC\\" + text[2:])
    return Path("\\\\?\\" + text)


def _pinned_bytes(root: Path, relative: str, expected: str) -> bytes:
    relative_path = _source_path(relative)
    if not re.fullmatch(r"[0-9a-f]{64}", expected):
        raise MissingCoverageError(f"invalid source-only digest: {relative}")
    try:
        path = root
        for part in relative_path.parts:
            path = path / part
            info = _native_path(path).lstat()
            if (stat.S_ISLNK(info.st_mode)
                    or getattr(info, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)):
                raise MissingCoverageError(f"redirected source-only path: {relative}")
        if not stat.S_ISREG(info.st_mode) or info.st_size > 1024 * 1024:
            raise MissingCoverageError(f"missing or oversized source-only file: {relative}")
        raw = _native_path(path).read_bytes()
    except OSError as error:
        raise MissingCoverageError(f"unreadable source-only file: {relative}") from error
    if hashlib.sha256(raw).hexdigest() != expected:
        raise MissingCoverageError(f"source-only identity mismatch: {relative}")
    return raw


def _source_only_component(root: Path, spec: dict) -> dict:
    identities: dict[str, str] = {}
    for relative, digest in spec["files"].items():
        _pinned_bytes(root, relative, digest)
        identities[relative] = digest
    for relative, digest in spec.get("manifests", {}).items():
        raw = _pinned_bytes(root, relative, digest)
        identities[relative] = digest
        try:
            manifest = json.loads(raw)
            entries = manifest.get("originals", manifest.get("files"))
            if not isinstance(entries, dict) or not entries:
                raise ValueError("empty source manifest")
            parent = _source_path(relative).parent
            for member, identity in entries.items():
                member_path = _source_path(member)
                member_relative = (parent / member_path).as_posix()
                member_digest = identity if isinstance(identity, str) else identity["sha256"]
                contents = _pinned_bytes(root, member_relative, member_digest)
                if isinstance(identity, dict) and len(contents) != identity["bytes"]:
                    raise ValueError("source member size mismatch")
                identities[member_relative] = member_digest
        except (ValueError, KeyError, TypeError, json.JSONDecodeError) as error:
            raise MissingCoverageError(f"invalid source-only manifest: {relative}") from error
    if not all(relative in identities for relative in spec["license_files"]):
        raise MissingCoverageError(f"missing pinned license for {spec['name']}")
    first_path = next(iter(identities))
    properties = [
        {"name": "archeaxis:scope", "value": "SOURCE_ONLY"},
        {"name": "archeaxis:packaging", "value": "NOT_PROVEN"},
        *({"name": "archeaxis:license-file", "value": path} for path in spec["license_files"]),
        *([{"name": "archeaxis:license-review", "value": spec["license_review"]}]
          if spec.get("license_review") else []),
        *({"name": "archeaxis:selected-file-sha256", "value": f"{path}={digest}"}
          for path, digest in sorted(identities.items())),
    ]
    return {
        "name": spec["name"], "version": spec["version"], "purl": spec["purl"],
        "type": spec["type"], "license": spec["license"], "path": first_path,
        "hashes": [{"alg": "SHA-256", "content": identities[first_path]}],
        "properties": properties,
    }


def collect_components(root: Path) -> list[dict]:
    """Collect canonical locks, model assets and identified source-only reuse."""
    required = (
        (root / "uv.lock", _parse_uv_lock),
        (root / "frontend/package-lock.json", _parse_npm_lock),
        (root / "Cargo.lock", _parse_cargo_lock),
        (root / "src-tauri/Cargo.lock", _parse_cargo_lock),
    )
    missing = [path.relative_to(root).as_posix() for path, _ in required if not path.is_file()]
    if missing:
        raise MissingCoverageError("missing canonical SBOM sources: " + ", ".join(missing))

    components: list[dict] = []
    for lock, parser_fn in required:
        for component in parser_fn(lock):
            component["properties"] = [{"name": "archeaxis:lock-source", "value": lock.relative_to(root).as_posix()}]
            components.append(component)
    for lock, parser_fn in (
        (root / "desktop/package-lock.json", _parse_npm_lock),
        (root / "desktop/src-tauri/Cargo.lock", _parse_cargo_lock),
    ):
        if lock.is_file():
            for component in parser_fn(lock):
                component["properties"] = [{"name": "archeaxis:lock-source", "value": lock.relative_to(root).as_posix()}]
                components.append(component)

    magika_model = root / "shared/models/magika/model.onnx"
    magika_license = root / "shared/models/magika/LICENSE"
    vendored_required = (magika_model, magika_license)
    missing_vendored = [
        path.relative_to(root).as_posix() for path in vendored_required if not path.is_file()
    ]
    if missing_vendored:
        raise MissingCoverageError("missing vendored SBOM sources: " + ", ".join(missing_vendored))
    components.extend(
        [
            _vendored_component(
                name="magika-model", version="0.6.3", kind="model",
                path=magika_model, license_id="Apache-2.0",
            ),
        ]
    )
    components.extend(_source_only_component(root, spec) for spec in SOURCE_ONLY_COMPONENTS)

    deduped = {}
    for component in components:
        existing = deduped.get(component["purl"])
        if existing is None:
            deduped[component["purl"]] = component
        else:
            # One package/version, all supplying lock roots; different versions retain distinct purls.
            properties = existing.setdefault("properties", [])
            for prop in component.get("properties", []):
                if prop not in properties:
                    properties.append(prop)
    return sorted(deduped.values(), key=lambda component: (component["type"], component["name"]))


def _write_notices(components: list[dict], licenses: dict[str, str], out: Path) -> None:
    """THIRD_PARTY_NOTICES.txt: one section per component with license id."""
    lines = [
        "THIRD PARTY NOTICES",
        "===================",
        "",
        "ArcheAxis Knowledge uses third-party dependency sources. Licenses below are",
        "declared by each package's metadata (best effort); \"unknown\" means the",
        "lock file did not declare a license. Selected source hashes and scope",
        "details are in SBOM.cdx.json. Source-only entries do not establish release packaging.",
        "",
    ]
    for comp in components:
        lic = comp.get("license") or licenses.get(comp["name"], "") or "unknown"
        props = comp.get("properties", [])
        source_only = any(p.get("name") == "archeaxis:scope" and p.get("value") == "SOURCE_ONLY"
                          for p in props)
        suffix = " [SOURCE_ONLY; packaging not proven]" if source_only else ""
        lines.append(f"- {comp['name']} {comp['version']} [{comp['type']}] — {lic}{suffix}")
        if source_only:
            for prop in props:
                if prop.get("name") == "archeaxis:license-file":
                    lines.append(f"  License/notice source: {prop['value']}")
                elif prop.get("name") == "archeaxis:license-review":
                    lines.append(f"  License review: {prop['value']}")
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
