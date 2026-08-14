#!/usr/bin/env python3
"""Capability Pack builder CLI (AXW-CAP-504).

Assembles one or more validated plugin manifests plus an optional asset
directory into a single ``<name>-<version>.pack.zip`` with the layout::

    <name>-<version>.pack.zip
      pack.json            — pack metadata + manifests + per-file sha256
      files/...            — assets copied from the asset directory

``verify`` re-opens a pack and recomputes every per-file sha256; any
structural problem, missing file or hash mismatch is refused (non-zero
exit / PackBuildError). Builder and verifier share the same integrity
contract, so a pack built here always verifies here.

Consumption by ``scripts/capability_download.py``: that CLI governs
single-artifact downloads (stage -> verify -> activate) and consumes any
file, so a ``.pack.zip`` is staged/verified as one artifact via a
``file://`` URL with no interface change. Per-file integrity inside the
pack is governed by ``pack.json`` (this builder's ``verify``) and by
CapabilityStore's stage->activate content-hash check.

Usage::

    capability_pack.py build --manifest a.json --manifest b.json [--assets DIR] [--out DIR]
    capability_pack.py verify <name>-<version>.pack.zip
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PACK_FORMAT_VERSION = 1
PACK_JSON = "pack.json"
FILES_PREFIX = "files/"
CHUNK = 1024 * 256

_PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Load shared.plugin_manifest without mutating sys.path (architecture guard:
# scripts must not insert project root into sys.path).
_PLUGIN_MANIFEST_SPEC = importlib.util.spec_from_file_location(
    "shared.plugin_manifest",
    _PROJECT_ROOT / "shared" / "plugin_manifest.py",
)
_plugin_manifest_module = importlib.util.module_from_spec(_PLUGIN_MANIFEST_SPEC)
assert _PLUGIN_MANIFEST_SPEC.loader is not None
sys.modules["shared.plugin_manifest"] = _plugin_manifest_module
_PLUGIN_MANIFEST_SPEC.loader.exec_module(_plugin_manifest_module)
validate_plugin_manifest = _plugin_manifest_module.validate


class PackBuildError(ValueError):
    """Raised for any pack structural/hash refusal (fail-closed)."""


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(CHUNK), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _is_absolute_any_platform(p: str) -> bool:
    """Absolute-path detection that stays fail-closed on every OS.

    ``os.path.isabs`` only understands the host platform's form; a Windows
    drive/UNC path is relative on POSIX hosts. Pack entries must be rejected
    regardless of the platform the pack is built or verified on.
    """
    if os.path.isabs(p):
        return True
    return bool(re.match(r"^[A-Za-z]:[\\/]", p) or p.startswith("\\\\"))


def _assert_safe_rel(rel: str) -> None:
    """Refuse absolute paths and path traversal in pack entries."""
    if _is_absolute_any_platform(rel) or ".." in Path(rel).parts:
        raise PackBuildError(f"unsafe pack entry path: {rel!r}")


def _load_manifest(path: str | Path) -> dict[str, Any]:
    manifest_path = Path(path)
    try:
        raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PackBuildError(f"cannot read manifest {manifest_path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise PackBuildError(f"manifest {manifest_path} is not an object")
    validate_plugin_manifest(raw)
    return raw


def build_pack(
    manifests: list[dict[str, Any]],
    assets_dir: str | Path | None,
    out_dir: str | Path,
) -> Path:
    """Build a validated ``<name>-<version>.pack.zip``; refuse on any problem."""
    if not manifests:
        raise PackBuildError("at least one plugin manifest is required")
    for manifest in manifests:
        validate_plugin_manifest(manifest)

    name = manifests[0]["plugin_id"]
    version = manifests[0]["version"]
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    final = out_path / f"{name}-{version}.pack.zip"
    tmp = final.with_name(final.name + ".tmp")

    asset_root = Path(assets_dir) if assets_dir is not None else None
    if asset_root is not None and not asset_root.is_dir():
        raise PackBuildError(f"assets directory does not exist: {asset_root}")

    files: list[dict[str, Any]] = []
    try:
        with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            if asset_root is not None:
                for path in sorted(asset_root.rglob("*")):
                    if not path.is_file():
                        continue
                    rel = path.relative_to(asset_root).as_posix()
                    _assert_safe_rel(rel)
                    entry = f"{FILES_PREFIX}{rel}"
                    zf.write(path, entry)
                    files.append(
                        {
                            "path": entry,
                            "size_bytes": path.stat().st_size,
                            "sha256": _sha256_file(path),
                        }
                    )
            pack = {
                "pack_format": PACK_FORMAT_VERSION,
                "name": name,
                "version": version,
                "created_at": _utc_now(),
                "manifests": manifests,
                "files": files,
            }
            zf.writestr(PACK_JSON, json.dumps(pack, indent=2, sort_keys=True) + "\n")
    except OSError as exc:
        tmp.unlink(missing_ok=True)
        raise PackBuildError(f"failed to assemble pack: {exc}") from exc

    os.replace(tmp, final)
    return final


def verify_pack(pack_path: str | Path) -> list[str]:
    """Recompute per-file sha256 inside a pack; refuse on any mismatch.

    Returns the sorted list of ``files/...`` paths when the pack is intact.
    """
    path = Path(pack_path)
    if not path.is_file():
        raise PackBuildError(f"pack file not found: {path}")
    try:
        with zipfile.ZipFile(path) as zf:
            if PACK_JSON not in zf.namelist():
                raise PackBuildError(f"pack has no {PACK_JSON}: {path}")
            try:
                pack = json.loads(zf.read(PACK_JSON))
            except (OSError, json.JSONDecodeError) as exc:
                raise PackBuildError(f"{PACK_JSON} is not valid JSON: {exc}") from exc
            if not isinstance(pack, dict) or pack.get("pack_format") != PACK_FORMAT_VERSION:
                raise PackBuildError(f"unsupported pack_format in {PACK_JSON}")
            manifests = pack.get("manifests")
            if not isinstance(manifests, list) or not manifests:
                raise PackBuildError(f"{PACK_JSON} requires a non-empty manifests list")
            for manifest in manifests:
                if not isinstance(manifest, dict) or "plugin_id" not in manifest:
                    raise PackBuildError(f"{PACK_JSON} contains an invalid manifest entry")

            entries = pack.get("files")
            if not isinstance(entries, list):
                raise PackBuildError(f"{PACK_JSON} requires a files list")
            by_path: dict[str, dict[str, Any]] = {}
            for entry in entries:
                if not isinstance(entry, dict):
                    raise PackBuildError(f"{PACK_JSON} contains an invalid file entry")
                rel = entry.get("path")
                if not isinstance(rel, str) or not rel.startswith(FILES_PREFIX):
                    raise PackBuildError(
                        f"file entry path must start with {FILES_PREFIX!r}: {rel!r}"
                    )
                _assert_safe_rel(rel)
                if rel in by_path:
                    raise PackBuildError(f"duplicate file entry: {rel}")
                by_path[rel] = entry

            listed = set(by_path)
            actual = {
                name
                for name in zf.namelist()
                if name.startswith(FILES_PREFIX) and not name.endswith("/")
            }
            if listed != actual:
                missing = sorted(actual - listed)
                orphan = sorted(listed - actual)
                raise PackBuildError(
                    "pack file list mismatch "
                    f"(missing from pack.json: {missing}; not in zip: {orphan})"
                )

            for rel, entry in sorted(by_path.items()):
                data = zf.read(rel)
                if entry.get("sha256") != _sha256_bytes(data):
                    raise PackBuildError(f"sha256 mismatch for {rel}")
                if entry.get("size_bytes") != len(data):
                    raise PackBuildError(f"size mismatch for {rel}")
            return sorted(by_path)
    except (OSError, zipfile.BadZipFile) as exc:
        raise PackBuildError(f"cannot open pack {path}: {exc}") from exc


def cmd_build(args: argparse.Namespace) -> int:
    try:
        manifests = [_load_manifest(path) for path in args.manifest]
        pack_path = build_pack(manifests, args.assets, args.out)
    except (PackBuildError, ValueError) as exc:
        print(f"[capability_pack] build refused: {exc}", file=sys.stderr)
        return 1
    print(f"[capability_pack] built {pack_path}")
    print(f"[capability_pack] manifests={len(manifests)}  assets={args.assets or '-'}")
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    try:
        verified = verify_pack(args.pack)
    except PackBuildError as exc:
        print(f"[capability_pack] verify REFUSED: {exc}", file=sys.stderr)
        return 1
    print(f"[capability_pack] verify OK: {args.pack}")
    for rel in verified:
        print(f"[capability_pack]   {rel}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="capability_pack.py",
        description="Capability Pack builder: manifests + assets -> <name>-<version>.pack.zip",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_build = sub.add_parser("build", help="assemble a .pack.zip from manifests and assets")
    p_build.add_argument(
        "--manifest", action="append", required=True, help="plugin manifest JSON (repeatable)"
    )
    p_build.add_argument("--assets", default=None, help="asset directory copied into files/")
    p_build.add_argument("--out", default=".", help="output directory (default: current dir)")
    p_build.set_defaults(func=cmd_build)

    p_verify = sub.add_parser("verify", help="verify pack structure + per-file sha256")
    p_verify.add_argument("pack", help="path to a .pack.zip")
    p_verify.set_defaults(func=cmd_verify)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
