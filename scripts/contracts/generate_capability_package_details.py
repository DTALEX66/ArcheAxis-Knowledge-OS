"""从明确内置说明原字节生成只读能力详情；不注册、安装或执行任何引擎。"""
from __future__ import annotations

import argparse
import hashlib
import json
import stat
import tomllib
from pathlib import Path

from validate_capability_package import ManifestValidationError, parse_manifest_bytes

# 这是随产品审阅的说明字节入口，不是运行引擎/安装状态注册表，也不自动枚举目录。
BUILTIN_MANIFEST = "config/capability-packages/pdf-extract.manifest.json"
TARGET = "frontend/src/api/generated/capability-package-details.ts"
SOURCES = (
    "packages/contracts/v2/capability-package.schema.json",
    "scripts/contracts/validate_capability_package.py",
    "scripts/contracts/generate_capability_package_details.py",
    "scripts/contracts/check_capability_package_details.mjs",
    "config/capability-map.v1.json",
    "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
    "services/python-workers/routes.json",
    "crates/archeaxis-api/Cargo.toml",
)
MAX_PUBLIC_BYTES = 4194304


def read_public(root: Path, name: str, limit=MAX_PUBLIC_BYTES):
    # 调用方仅传固定公开输入或已经由现有validator验证的公共引用；读取前再次拒绝链接。
    if not name or any(x in ("", ".", "..") for x in name.split("/")) or ":" in name or "\\" in name:
        raise ManifestValidationError("MANIFEST_PROJECTION_PATH_REJECTED")
    current = root
    try:
        for part in name.split("/"):
            current /= part
            info = current.lstat()
            if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
                raise ManifestValidationError("MANIFEST_PROJECTION_LINK_REJECTED")
        if not stat.S_ISREG(info.st_mode) or info.st_size > limit:
            raise ManifestValidationError("MANIFEST_PROJECTION_SIZE_REJECTED")
        with current.open("rb") as handle:
            raw = handle.read(limit + 1)
        if len(raw) > limit:
            raise ManifestValidationError("MANIFEST_PROJECTION_SIZE_REJECTED")
        return raw
    except OSError:
        raise ManifestValidationError("MANIFEST_PROJECTION_SOURCE_UNAVAILABLE") from None


def build(root: Path):
    raw = read_public(root, BUILTIN_MANIFEST, 262144)
    identity = parse_manifest_bytes(raw, root)
    manifest = json.loads(raw)
    catalog = json.loads(read_public(root, "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json"))["entries"]
    by_key = {item["stable_key"]: item for item in catalog}
    # 本切片只接受目录已明确联接的来源，不能用相似名/候选CAP建立新的吸收事实。
    for key in manifest["resource_keys"]:
        row = by_key[key]
        if row.get("atlas_capability_id") not in manifest["capability_ids"]:
            raise ManifestValidationError("MANIFEST_PROJECTION_CATALOG_JOIN_UNCONFIRMED")
        route = row["route_binding"].get("named_route")
        if route and route not in manifest["runtime_capabilities"]:
            raise ManifestValidationError("MANIFEST_PROJECTION_ROUTE_JOIN_UNCONFIRMED")
    paths = set(SOURCES) | {BUILTIN_MANIFEST}
    refs = manifest["compatibility"]["contract_refs"] + manifest["license"]["notice_refs"]
    refs += [item["contract"] for item in manifest["inputs"] + manifest["outputs"]]
    paths.update(ref["path"] for ref in refs)
    sources = [{"path": name, "sha256": hashlib.sha256(read_public(root, name)).hexdigest()}
               for name in sorted(paths)]
    host = tomllib.loads(read_public(root, "crates/archeaxis-api/Cargo.toml").decode("utf-8"))["package"]["version"]
    return {"sources": sources, "entries": [{
        "identity": identity,
        "manifest": manifest,
        "source_path": BUILTIN_MANIFEST,
        "validation": "VALIDATED_DECLARATION",
        "host_version": host,
        "source_authenticity": "UNVERIFIED",
        "qualification": "UNKNOWN",
        "runtime": "UNKNOWN",
    }]}


TYPES = """import type { CapabilityManifestIdentity, CapabilityPackageManifest } from './capability-package';
export type CapabilityPackageDetail = {
  identity: CapabilityManifestIdentity; manifest: CapabilityPackageManifest; source_path: string;
  validation: 'VALIDATED_DECLARATION'; host_version: string;
  source_authenticity: 'UNVERIFIED'; qualification: 'UNKNOWN'; runtime: 'UNKNOWN';
};
export type CapabilityPackageDetailProjection = {
  sources: { path: string; sha256: string }[]; entries: CapabilityPackageDetail[];
};
"""


def generate(root: Path):
    payload = build(root)
    return ("// Generated from exact builtin manifest and public validator inputs. Declaration only.\n"
            + TYPES + "export const CAPABILITY_PACKAGE_DETAILS: CapabilityPackageDetailProjection = "
            + json.dumps(payload, ensure_ascii=False, indent=2) + ";\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--output", type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        rendered = generate(args.root)
        target = args.output or args.root / TARGET
        if args.check:
            if not target.is_file() or target.read_text(encoding="utf-8") != rendered:
                raise ManifestValidationError("MANIFEST_PROJECTION_STALE")
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(rendered, encoding="utf-8", newline="\n")
    except (ManifestValidationError, OSError, ValueError, KeyError):
        # 不回显manifest、路径、来源正文、license任意文本或解析器错误。
        raise SystemExit("MANIFEST_PROJECTION_CHECK_FAILED") from None


if __name__ == "__main__":
    main()
