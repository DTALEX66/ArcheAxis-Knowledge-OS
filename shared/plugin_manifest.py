"""Plugin Manifest v1 (AXW-CAP-502).

Every capability pack shipped to the Capability Store must carry a valid
`plugin-manifest.json`. Validation is fail-closed: missing fields, unknown
keys, unknown permissions, or malformed platform entries reject the pack
with ValueError (JSON Schema from contracts/ when jsonschema is available,
otherwise an equivalent hand-written validator).

`is_compatible()` decides whether a manifest may run against a host API
contract range and platform — unparseable ranges or mismatched platforms
always resolve to incompatible (never a permissive default).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

MANIFEST_VERSION = "1.0"

ALLOWED_PERMISSIONS = (
    "files.read",
    "files.write",
    "network",
    "process",
    "model.load",
    "ui.contribution",
)
ALLOWED_OS = ("windows", "linux", "macos", "any")
ALLOWED_ARCH = ("x86_64", "aarch64", "arm64", "any")

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_SCHEMA_PATH = _PROJECT_ROOT / "contracts" / "plugin" / "plugin-manifest.schema.json"

_REQUIRED_TOP_LEVEL = (
    "manifest_version",
    "plugin_id",
    "name",
    "version",
    "api_contract",
    "permissions",
    "platform",
    "entry",
)
_KNOWN_TOP_LEVEL = {
    "manifest_version",
    "plugin_id",
    "name",
    "version",
    "api_contract",
    "permissions",
    "platform",
    "resources",
    "license",
    "data_ownership",
    "healthcheck",
    "size_bytes",
    "entry",
    "dependencies",
}
_PLUGIN_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,127}$")
_VERSION_RE = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")


@dataclass(frozen=True)
class PlatformSpec:
    os: str
    arch: str


@dataclass(frozen=True)
class PluginManifest:
    """Validated plugin manifest v1."""

    manifest_version: str
    plugin_id: str
    name: str
    version: str
    api_contract: str
    permissions: tuple[str, ...]
    platform: PlatformSpec
    entry: str
    resources: dict[str, Any] = field(default_factory=dict)
    license: str | None = None
    data_ownership: dict[str, Any] = field(default_factory=dict)
    healthcheck: str | None = None
    size_bytes: int | None = None
    dependencies: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "manifest_version": self.manifest_version,
            "plugin_id": self.plugin_id,
            "name": self.name,
            "version": self.version,
            "api_contract": self.api_contract,
            "permissions": list(self.permissions),
            "platform": {"os": self.platform.os, "arch": self.platform.arch},
            "entry": self.entry,
        }
        if self.resources:
            data["resources"] = self.resources
        if self.license is not None:
            data["license"] = self.license
        if self.data_ownership:
            data["data_ownership"] = self.data_ownership
        if self.healthcheck is not None:
            data["healthcheck"] = self.healthcheck
        if self.size_bytes is not None:
            data["size_bytes"] = self.size_bytes
        if self.dependencies:
            data["dependencies"] = list(self.dependencies)
        return data


# ── Hand-written fail-closed validator (used when jsonschema is absent) ──


def _require_mapping(value: Any, where: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"plugin manifest: {where} must be an object")
    return value


def _require_nonempty_string(value: Any, where: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"plugin manifest: {where} must be a non-empty string")
    return value


def _validate_handwritten(data: Any) -> None:
    manifest = _require_mapping(data, "manifest")
    unknown = set(manifest) - _KNOWN_TOP_LEVEL
    if unknown:
        raise ValueError(f"plugin manifest: unknown field(s): {sorted(unknown)}")
    for key in _REQUIRED_TOP_LEVEL:
        if key not in manifest:
            raise ValueError(f"plugin manifest: missing required field '{key}'")
    if manifest["manifest_version"] != MANIFEST_VERSION:
        raise ValueError(
            f"plugin manifest: unsupported manifest_version {manifest['manifest_version']!r}; "
            f"expected {MANIFEST_VERSION!r}"
        )
    plugin_id = _require_nonempty_string(manifest["plugin_id"], "plugin_id")
    if not _PLUGIN_ID_RE.match(plugin_id):
        raise ValueError(f"plugin manifest: plugin_id {plugin_id!r} is not a valid identifier")
    _require_nonempty_string(manifest["name"], "name")
    version = _require_nonempty_string(manifest["version"], "version")
    if not _VERSION_RE.match(version):
        raise ValueError(f"plugin manifest: version {version!r} must be x.y.z")
    _require_nonempty_string(manifest["api_contract"], "api_contract")

    permissions = manifest["permissions"]
    if not isinstance(permissions, list):
        raise ValueError("plugin manifest: permissions must be an array")
    if len(set(permissions)) != len(permissions):
        raise ValueError("plugin manifest: permissions must be unique")
    for perm in permissions:
        if perm not in ALLOWED_PERMISSIONS:
            raise ValueError(f"plugin manifest: unknown permission {perm!r}")

    platform = _require_mapping(manifest["platform"], "platform")
    unknown_platform = set(platform) - {"os", "arch"}
    if unknown_platform:
        raise ValueError(f"plugin manifest: platform unknown field(s): {sorted(unknown_platform)}")
    if "os" not in platform or "arch" not in platform:
        raise ValueError("plugin manifest: platform requires os and arch")
    if platform["os"] not in ALLOWED_OS:
        raise ValueError(f"plugin manifest: platform.os {platform['os']!r} not allowed")
    if platform["arch"] not in ALLOWED_ARCH:
        raise ValueError(f"plugin manifest: platform.arch {platform['arch']!r} not allowed")

    _require_nonempty_string(manifest["entry"], "entry")

    if "size_bytes" in manifest and (
        isinstance(manifest["size_bytes"], bool)
        or not isinstance(manifest["size_bytes"], int)
        or manifest["size_bytes"] < 0
    ):
        raise ValueError("plugin manifest: size_bytes must be a non-negative integer")
    if "dependencies" in manifest:
        deps = manifest["dependencies"]
        if not isinstance(deps, list) or len(set(deps)) != len(deps):
            raise ValueError("plugin manifest: dependencies must be a unique array")
        for dep in deps:
            _require_nonempty_string(dep, "dependencies")


# ── Public validation API ──────────────────────────────────────────────────


def validate(manifest: dict[str, Any]) -> dict[str, Any]:
    """Validate a plugin manifest mapping; raise ValueError when invalid."""
    try:
        import jsonschema  # type: ignore[import-not-found]
    except ImportError:
        _validate_handwritten(manifest)
        return manifest
    if not _SCHEMA_PATH.exists():
        _validate_handwritten(manifest)
        return manifest
    try:
        schema = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"plugin manifest: cannot load schema {_SCHEMA_PATH}") from exc
    try:
        jsonschema.validate(instance=manifest, schema=schema)
    except jsonschema.ValidationError as exc:
        raise ValueError(f"plugin manifest: {exc.message}") from exc
    return manifest


def load(path: str | Path) -> PluginManifest:
    """Load, validate and parse a plugin manifest file (fail-closed)."""
    manifest_path = Path(path)
    try:
        raw = manifest_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ValueError(f"plugin manifest: cannot read {manifest_path}") from exc
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"plugin manifest: invalid JSON in {manifest_path}") from exc
    validate(data)

    platform = PlatformSpec(os=data["platform"]["os"], arch=data["platform"]["arch"])
    return PluginManifest(
        manifest_version=data["manifest_version"],
        plugin_id=data["plugin_id"],
        name=data["name"],
        version=data["version"],
        api_contract=data["api_contract"],
        permissions=tuple(data["permissions"]),
        platform=platform,
        entry=data["entry"],
        resources=dict(data.get("resources", {})),
        license=data.get("license"),
        data_ownership=dict(data.get("data_ownership", {})),
        healthcheck=data.get("healthcheck"),
        size_bytes=data.get("size_bytes"),
        dependencies=tuple(data.get("dependencies", [])),
    )


# ── Version-range compatibility (fail-closed) ──────────────────────────────

Version = tuple[int, int, int]
_INFINITY = (10**9, 10**9, 10**9)


def _parse_version(text: str) -> Version:
    parts = [int(part) for part in text.strip().split(".")]
    while len(parts) < 3:
        parts.append(0)
    return (parts[0], parts[1], parts[2])


@dataclass(frozen=True)
class _Range:
    lower: Version | None
    upper: Version | None
    lower_inclusive: bool = True
    upper_inclusive: bool = False


def _parse_range(spec: str) -> _Range | None:
    """Parse a version range spec; None means unparseable (fail-closed).

    Supported shapes: "1.x", "1.2.x", "1.2.3", ">=1.0,<2.0", "*".
    """
    text = spec.strip()
    if not text or text == "*":
        return _Range(lower=None, upper=None)
    if text.endswith(".x"):
        head = text[:-2]
        parts = [int(part) for part in head.split(".") if part != ""]
        if not parts or len(parts) > 2:
            return None
        if len(parts) == 1:
            return _Range(lower=(parts[0], 0, 0), upper=(parts[0] + 1, 0, 0))
        return _Range(lower=(parts[0], parts[1], 0), upper=(parts[0], parts[1] + 1, 0))
    if "," in text:
        lower: Version | None = None
        upper: Version | None = None
        lower_inclusive = True
        upper_inclusive = False
        for clause in text.split(","):
            clause = clause.strip()
            parsed = _parse_single_clause(clause)
            if parsed is None:
                return None
            kind, version, inclusive = parsed
            if kind == "lower":
                if lower is None or version > lower:
                    lower, lower_inclusive = version, inclusive
            elif kind == "upper":
                if upper is None or version < upper:
                    upper, upper_inclusive = version, inclusive
            else:  # exact
                return _Range(lower=version, upper=version, lower_inclusive=True, upper_inclusive=True)
        return _Range(lower=lower, upper=upper, lower_inclusive=lower_inclusive, upper_inclusive=upper_inclusive)
    single = _parse_single_clause(text)
    if single is not None:
        kind, version, inclusive = single
        if kind == "lower":
            return _Range(lower=version, upper=None, lower_inclusive=inclusive)
        if kind == "upper":
            return _Range(lower=None, upper=version, upper_inclusive=inclusive)
        return _Range(lower=version, upper=version, lower_inclusive=True, upper_inclusive=True)
    return _exact_or_single(text)


def _parse_single_clause(clause: str) -> tuple[str, Version, bool] | None:
    """Return (kind, version, inclusive) for one comparator clause."""
    clause = clause.strip()
    for op, kind, inclusive in ((">=", "lower", True), (">", "lower", False),
                                ("<=", "upper", True), ("<", "upper", False),
                                ("==", "exact", True)):
        if clause.startswith(op):
            rest = clause[len(op):].strip()
            if not rest:
                return None
            try:
                return kind, _parse_version(rest), inclusive
            except ValueError:
                return None
    return None


def _exact_or_single(text: str) -> _Range | None:
    """Handle a bare version ("1.2.3" or "1.2") as an exact range."""
    try:
        version = _parse_version(text)
    except ValueError:
        return None
    return _Range(lower=version, upper=version, lower_inclusive=True, upper_inclusive=True)


def _ranges_overlap(left: _Range, right: _Range) -> bool:
    """Two half-open ranges intersect iff neither is entirely left of the other."""

    def left_of(a: _Range, b: _Range) -> bool:
        if b.lower is None:
            return False
        if a.upper is None:
            return False
        if a.upper < b.lower:
            return True
        return a.upper == b.lower and not (a.upper_inclusive and b.lower_inclusive)

    return not (left_of(left, right) or left_of(right, left))


def is_compatible(
    manifest: PluginManifest | dict[str, Any],
    host_contract: str,
    platform: dict[str, str] | None = None,
) -> bool:
    """Decide whether a plugin may run on this host. Fail-closed.

    - The plugin's api_contract range must intersect the host's contract
      range; any unparseable range makes the plugin incompatible.
    - When `platform` is given, the manifest platform must match the host
      os/arch (wildcard "any" matches everything).
    """
    if isinstance(manifest, dict):
        manifest = load_manifest_from_mapping(manifest)
    plugin_range = _parse_range(manifest.api_contract)
    host_range = _parse_range(host_contract)
    if plugin_range is None or host_range is None:
        return False
    if not _ranges_overlap(plugin_range, host_range):
        return False
    if platform is not None:
        host_os = platform.get("os")
        host_arch = platform.get("arch")
        if host_os is None or host_arch is None:
            return False
        if manifest.platform.os != "any" and manifest.platform.os != host_os:
            return False
        if manifest.platform.arch != "any" and manifest.platform.arch != host_arch:
            return False
    return True


def load_manifest_from_mapping(data: dict[str, Any]) -> PluginManifest:
    """Build a PluginManifest from an already-validated mapping."""
    validate(data)
    platform = PlatformSpec(os=data["platform"]["os"], arch=data["platform"]["arch"])
    return PluginManifest(
        manifest_version=data["manifest_version"],
        plugin_id=data["plugin_id"],
        name=data["name"],
        version=data["version"],
        api_contract=data["api_contract"],
        permissions=tuple(data["permissions"]),
        platform=platform,
        entry=data["entry"],
        resources=dict(data.get("resources", {})),
        license=data.get("license"),
        data_ownership=dict(data.get("data_ownership", {})),
        healthcheck=data.get("healthcheck"),
        size_bytes=data.get("size_bytes"),
        dependencies=tuple(data.get("dependencies", [])),
    )
