"""能力包仅声明校验：复用现有CAP/catalog/routes，不注册、不安装、不启动、不授权。"""

from __future__ import annotations

import hashlib
import json
import stat
import tomllib
from pathlib import Path, PurePosixPath

from jsonschema import Draft202012Validator

MAX_MANIFEST_BYTES = 262144
MAX_SOURCE_BYTES = 4194304


class ManifestValidationError(ValueError):
    """只抛有限错误码，不把未受信manifest内容/secret回显到日志。"""


def _fail(code):
    raise ManifestValidationError(code)


def _read_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _version(text):
    return tuple(int(x) for x in text.split("."))


def _range(value):
    low, high = _version(value["minimum"]), _version(value["maximum_exclusive"])
    if low >= high:
        _fail("MANIFEST_VERSION_RANGE_INVALID")
    return low, high


def _source(root, reference, contracts_only=False):
    name = reference["path"]
    pure = PurePosixPath(name)
    if pure.is_absolute() or ":" in name or "\\" in name:
        _fail("MANIFEST_SOURCE_PATH_REJECTED")
    parts = name.split("/")
    private = {
        "private",
        "secrets",
        "credentials",
        "sessions",
        "session",
        "memory",
        "memories",
        "tokens",
        "cookies",
        "auth",
        "data",
        "node_modules",
        "target",
        "dist",
    }
    if any(x in ("", ".", "..") or x.startswith(".") or x.casefold() in private for x in parts):
        _fail("MANIFEST_SOURCE_PATH_REJECTED")
    if not (
        name in ("LICENSE", "THIRD_PARTY_NOTICES.md")
        or name.startswith("docs/")
        or name.startswith("packages/contracts/")
    ):
        _fail("MANIFEST_SOURCE_PATH_REJECTED")
    if contracts_only and not (
        name.startswith("packages/contracts/") and name.endswith(".schema.json")
    ):
        _fail("MANIFEST_IO_CONTRACT_REQUIRED")
    # 在读取或resolve之前逐级拒绝链接/Windows junction，不追踪到其他盘或private对象。
    current = root
    try:
        for part in parts:
            current = current / part
            info = current.lstat()
            if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & getattr(
                stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400
            ):
                _fail("MANIFEST_SOURCE_LINK_REJECTED")
        info = current.stat()
        if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_SOURCE_BYTES:
            _fail("MANIFEST_SOURCE_SIZE_REJECTED")
        # Bounded read even if a source grows between stat and read.
        with current.open("rb") as handle:
            raw = handle.read(MAX_SOURCE_BYTES + 1)
        if len(raw) > MAX_SOURCE_BYTES:
            _fail("MANIFEST_SOURCE_SIZE_REJECTED")
    except OSError:
        _fail("MANIFEST_SOURCE_UNAVAILABLE")
    if hashlib.sha256(raw).hexdigest() != reference["sha256"]:
        _fail("MANIFEST_SOURCE_DRIFT")


def validate_manifest(value, root: Path, schema=None):
    """验证声明及显式公共引用；不返回任何runtime可用/安装/授权状态。"""
    root = Path(root)
    schema = schema or _read_json(root / "packages/contracts/v2/capability-package.schema.json")
    validator = Draft202012Validator(schema)
    if not validator.is_valid(value):
        _fail("MANIFEST_SCHEMA_REJECTED")
    mapping = _read_json(root / "config/capability-map.v1.json")["capabilities"]
    catalog = _read_json(root / "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json")[
        "entries"
    ]
    routes = _read_json(root / "services/python-workers/routes.json")["routes"]
    ids = {x["capability_id"] for x in mapping}
    keys = {x["stable_key"] for x in catalog}
    if not set(value["capability_ids"]) <= ids or not set(value["resource_keys"]) <= keys:
        _fail("MANIFEST_CATALOG_REFERENCE_UNKNOWN")
    allowed = {
        route
        for item in mapping
        if item["capability_id"] in value["capability_ids"]
        for route in item["runtime_capabilities"]
    }
    if not set(value["runtime_capabilities"]) <= allowed or not set(
        value["runtime_capabilities"]
    ) <= set(routes):
        _fail("MANIFEST_RUNTIME_ROUTE_NOT_MAPPED")
    dependency_keys = [x["resource_key"] for x in value["dependencies"]]
    if len(dependency_keys) != len(set(dependency_keys)) or not set(dependency_keys) <= keys:
        _fail("MANIFEST_DEPENDENCY_REFERENCE_INVALID")
    for item in value["dependencies"]:
        if item["version_range"] is not None:
            _range(item["version_range"])
    low, high = _range(value["compatibility"]["host_versions"])
    try:
        host = tomllib.loads(
            (root / "crates/archeaxis-api/Cargo.toml").read_text(encoding="utf-8")
        )["package"]["version"]
        host_version = _version(host)
    except (OSError, ValueError, KeyError, tomllib.TOMLDecodeError):
        _fail("MANIFEST_HOST_VERSION_UNAVAILABLE")
    if not low <= host_version < high:
        _fail("MANIFEST_HOST_INCOMPATIBLE")
    for item in value["compatibility"]["contract_refs"]:
        _source(root, item, True)
    for item in value["inputs"] + value["outputs"]:
        _source(root, item["contract"], True)
    for item in value["license"]["notice_refs"]:
        _source(root, item)
    if value["license"]["review"] == "DECLARED_ONLY" and not value["license"]["expression"]:
        _fail("MANIFEST_LICENSE_DECLARATION_INCOMPLETE")
    permissions = value["permissions"]
    if "model.remote.invoke" in permissions["requested"] and (
        permissions["network"] != "explicit_remote"
        or "model_service" not in value["contribution_points"]
    ):
        _fail("MANIFEST_PERMISSION_DECLARATION_CONFLICT")
    if value["runtime_capabilities"] and (
        value["lifecycle"]["cancellation"] != "host_propagated"
        or value["lifecycle"]["exit"] != "bounded_cleanup"
    ):
        _fail("MANIFEST_RUNTIME_LIFECYCLE_REQUIRED")
    return None


def parse_manifest_bytes(raw: bytes, root: Path, schema=None):
    """对明确提供的有界字节校验；SHA绑定原字节，拒绝重复JSON键。"""
    if not isinstance(raw, bytes) or len(raw) > MAX_MANIFEST_BYTES:
        _fail("MANIFEST_INPUT_SIZE_REJECTED")

    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                _fail("MANIFEST_DUPLICATE_KEY")
            result[key] = value
        return result

    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=unique)
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError):
        _fail("MANIFEST_JSON_REJECTED")
    validate_manifest(value, root, schema)
    return {
        "schema": value["schema"],
        "package_id": value["package_id"],
        "version": value["version"],
        "sha256": hashlib.sha256(raw).hexdigest(),
    }
