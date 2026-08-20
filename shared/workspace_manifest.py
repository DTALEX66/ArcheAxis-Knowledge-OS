"""Workspace Manifest (AXW-DATA-401).

One workspace = four asset domains (Source Archive / Evidence & Knowledge
Ledger / Human Learning Vault / AI Asset Vault) described by a single
`manifest.json`, plus optional capability locks and backup metadata.

Validation is fail-closed: a manifest that is missing required fields,
has unknown keys, or malformed domain entries is rejected with ValueError.
The JSON Schema in `contracts/workspace/workspace-manifest.schema.json` is
used when the `jsonschema` package is importable; otherwise a hand-written
validator enforcing the same required-field contract takes over.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

SCHEMA_VERSION = "1.0"

# The four asset domains of a workspace, in canonical order.
ASSET_DOMAINS = (
    "source_archive",
    "evidence_ledger",
    "human_learning_vault",
    "ai_asset_vault",
)

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_SCHEMA_PATH = _PROJECT_ROOT / "contracts" / "workspace" / "workspace-manifest.schema.json"

_REQUIRED_TOP_LEVEL = ("schema_version", "workspace_id", "created_at", "name", "domains")
_REQUIRED_DOMAIN = ("path", "type", "readonly")
_REQUIRED_LOCK = ("capability_id", "version_range")
_REQUIRED_BACKUP = ("location", "last_backup")

_KNOWN_TOP_LEVEL = {
    "schema_version",
    "workspace_id",
    "created_at",
    "name",
    "domains",
    "capability_lock",
    "backup",
    "derived_cache_path",
    "logs_path",
}
_KNOWN_DOMAIN_KEYS = {"path", "type", "readonly"}
_KNOWN_LOCK_KEYS = {"capability_id", "version_range"}
_KNOWN_BACKUP_KEYS = {"location", "last_backup"}

_IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


@dataclass(frozen=True)
class DomainInfo:
    """One asset domain entry from a workspace manifest."""

    path: str
    type: str
    readonly: bool


@dataclass(frozen=True)
class CapabilityLock:
    """A capability pinned to a version range by the workspace manifest."""

    capability_id: str
    version_range: str


@dataclass(frozen=True)
class BackupInfo:
    """Backup metadata block (may be absent from the manifest)."""

    location: str
    last_backup: str | None


@dataclass(frozen=True)
class WorkspaceManifest:
    """Validated workspace manifest."""

    schema_version: str
    workspace_id: str
    created_at: str
    name: str
    domains: dict[str, DomainInfo]
    capability_lock: list[CapabilityLock] = field(default_factory=list)
    backup: BackupInfo | None = None
    derived_cache_path: str | None = None
    logs_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize back to the canonical manifest mapping."""
        data: dict[str, Any] = {
            "schema_version": self.schema_version,
            "workspace_id": self.workspace_id,
            "created_at": self.created_at,
            "name": self.name,
            "domains": {
                key: {
                    "path": domain.path,
                    "type": domain.type,
                    "readonly": domain.readonly,
                }
                for key, domain in self.domains.items()
            },
        }
        if self.capability_lock:
            data["capability_lock"] = [
                {"capability_id": lock.capability_id, "version_range": lock.version_range}
                for lock in self.capability_lock
            ]
        if self.backup is not None:
            data["backup"] = {
                "location": self.backup.location,
                "last_backup": self.backup.last_backup,
            }
        if self.derived_cache_path is not None:
            data["derived_cache_path"] = self.derived_cache_path
        if self.logs_path is not None:
            data["logs_path"] = self.logs_path
        return data

    def write(self, path: str | Path) -> Path:
        """Persist the manifest as canonical JSON (indent=2, sorted keys)."""
        target = Path(path)
        target.write_text(
            json.dumps(self.to_dict(), indent=2, sort_keys=True, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return target


# ── Hand-written fail-closed validator (used when jsonschema is absent) ──


def _require_mapping(value: Any, where: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"workspace manifest: {where} must be an object")
    return value


def _require_nonempty_string(value: Any, where: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"workspace manifest: {where} must be a non-empty string")
    return value


def _validate_handwritten(data: Any) -> None:
    """Enforce the same required-field contract as the JSON Schema."""
    manifest = _require_mapping(data, "manifest")
    unknown = set(manifest) - _KNOWN_TOP_LEVEL
    if unknown:
        raise ValueError(
            f"workspace manifest: unknown top-level field(s): {sorted(unknown)}"
        )
    for key in _REQUIRED_TOP_LEVEL:
        if key not in manifest:
            raise ValueError(f"workspace manifest: missing required field '{key}'")
    if manifest["schema_version"] != SCHEMA_VERSION:
        raise ValueError(
            f"workspace manifest: unsupported schema_version "
            f"{manifest['schema_version']!r}; expected {SCHEMA_VERSION!r}"
        )
    _require_nonempty_string(manifest["workspace_id"], "workspace_id")
    if not _IDENTIFIER_RE.match(manifest["workspace_id"]):
        raise ValueError(
            f"workspace manifest: workspace_id {manifest['workspace_id']!r} "
            "must match ^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$"
        )
    _require_nonempty_string(manifest["created_at"], "created_at")
    _require_nonempty_string(manifest["name"], "name")

    domains = _require_mapping(manifest["domains"], "domains")
    for key in ASSET_DOMAINS:
        if key not in domains:
            raise ValueError(f"workspace manifest: domains missing required asset domain '{key}'")
    for key, entry in domains.items():
        domain = _require_mapping(entry, f"domains.{key}")
        unknown_domain = set(domain) - _KNOWN_DOMAIN_KEYS
        if unknown_domain:
            raise ValueError(
                f"workspace manifest: domains.{key} unknown field(s): {sorted(unknown_domain)}"
            )
        for field_name in _REQUIRED_DOMAIN:
            if field_name not in domain:
                raise ValueError(
                    f"workspace manifest: domains.{key} missing required field '{field_name}'"
                )
        _require_nonempty_string(domain["path"], f"domains.{key}.path")
        if domain["type"] not in ASSET_DOMAINS:
            raise ValueError(
                f"workspace manifest: domains.{key}.type {domain['type']!r} "
                f"must be one of {ASSET_DOMAINS}"
            )
        if not isinstance(domain["readonly"], bool):
            raise ValueError(f"workspace manifest: domains.{key}.readonly must be a boolean")

    if "capability_lock" in manifest:
        locks = manifest["capability_lock"]
        if not isinstance(locks, list):
            raise ValueError("workspace manifest: capability_lock must be an array")
        for index, lock in enumerate(locks):
            lock_map = _require_mapping(lock, f"capability_lock[{index}]")
            unknown_lock = set(lock_map) - _KNOWN_LOCK_KEYS
            if unknown_lock:
                raise ValueError(
                    f"workspace manifest: capability_lock[{index}] unknown field(s): "
                    f"{sorted(unknown_lock)}"
                )
            for field_name in _REQUIRED_LOCK:
                if field_name not in lock_map:
                    raise ValueError(
                        f"workspace manifest: capability_lock[{index}] missing "
                        f"required field '{field_name}'"
                    )
            _require_nonempty_string(
                lock_map["capability_id"], f"capability_lock[{index}].capability_id"
            )
            _require_nonempty_string(
                lock_map["version_range"], f"capability_lock[{index}].version_range"
            )

    if "backup" in manifest:
        backup = _require_mapping(manifest["backup"], "backup")
        unknown_backup = set(backup) - _KNOWN_BACKUP_KEYS
        if unknown_backup:
            raise ValueError(f"workspace manifest: backup unknown field(s): {sorted(unknown_backup)}")
        for field_name in _REQUIRED_BACKUP:
            if field_name not in backup:
                raise ValueError(f"workspace manifest: backup missing required field '{field_name}'")
        _require_nonempty_string(backup["location"], "backup.location")
        if backup["last_backup"] is not None and not isinstance(backup["last_backup"], str):
            raise ValueError("workspace manifest: backup.last_backup must be a string or null")

    for key in ("derived_cache_path", "logs_path"):
        if key in manifest and not isinstance(manifest[key], str):
            raise ValueError(f"workspace manifest: {key} must be a string")


# ── Public API ────────────────────────────────────────────────────────────


def validate(manifest: dict[str, Any]) -> dict[str, Any]:
    """Validate a workspace manifest mapping; raise ValueError when invalid.

    Uses the JSON Schema from contracts/ when `jsonschema` is importable,
    otherwise the hand-written fail-closed validator above.
    """
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
        raise ValueError(f"workspace manifest: cannot load schema {_SCHEMA_PATH}") from exc
    try:
        jsonschema.validate(instance=manifest, schema=schema)
    except jsonschema.ValidationError as exc:
        raise ValueError(f"workspace manifest: {exc.message}") from exc
    return manifest


def load(path: str | Path) -> WorkspaceManifest:
    """Load, validate and parse a workspace manifest file."""
    manifest_path = Path(path)
    try:
        raw = manifest_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ValueError(f"workspace manifest: cannot read {manifest_path}") from exc
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"workspace manifest: invalid JSON in {manifest_path}") from exc
    validate(data)

    domains = {
        key: DomainInfo(
            path=entry["path"],
            type=entry["type"],
            readonly=bool(entry["readonly"]),
        )
        for key, entry in data["domains"].items()
    }
    locks = [
        CapabilityLock(capability_id=entry["capability_id"], version_range=entry["version_range"])
        for entry in data.get("capability_lock", [])
    ]
    backup_data = data.get("backup")
    backup = (
        BackupInfo(
            location=backup_data["location"],
            last_backup=backup_data.get("last_backup"),
        )
        if backup_data is not None
        else None
    )
    return WorkspaceManifest(
        schema_version=data["schema_version"],
        workspace_id=data["workspace_id"],
        created_at=data["created_at"],
        name=data["name"],
        domains=domains,
        capability_lock=locks,
        backup=backup,
        derived_cache_path=data.get("derived_cache_path"),
        logs_path=data.get("logs_path"),
    )


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def create_workspace(
    root: str | Path,
    name: str,
    *,
    domain_paths: dict[str, str | Path] | None = None,
) -> WorkspaceManifest:
    """Create a workspace directory tree with the four asset domains.

    Creates `<root>/<name>/` containing one directory per asset domain,
    plus `manifest.json`. Existing directories are reused; the manifest is
    never overwritten when a valid one already exists (fail-closed).
    """
    workspace_root = Path(root)
    if not name or not str(name).strip():
        raise ValueError("workspace name must be non-empty")
    workspace_dir = workspace_root / str(name).strip()
    workspace_dir.mkdir(parents=True, exist_ok=True)

    manifest_path = workspace_dir / "manifest.json"
    if manifest_path.exists():
        existing = load(manifest_path)
        return existing

    if domain_paths is not None and set(domain_paths) != set(ASSET_DOMAINS):
        raise ValueError("workspace domain paths must name each of the four asset domains exactly once")
    resolved_domains = {
        domain_key: Path(domain_paths[domain_key]) if domain_paths is not None else workspace_dir / domain_key
        for domain_key in ASSET_DOMAINS
    }
    created_at = _now_iso()
    manifest = WorkspaceManifest(
        schema_version=SCHEMA_VERSION,
        workspace_id=f"ws-{uuid4().hex[:12]}",
        created_at=created_at,
        name=str(name).strip(),
        domains={
            domain_key: DomainInfo(
                path=str(resolved_domains[domain_key]),
                type=domain_key,
                readonly=False,
            )
            for domain_key in ASSET_DOMAINS
        },
        capability_lock=[],
        backup=BackupInfo(location=str(workspace_dir / "backups"), last_backup=None),
        derived_cache_path=str(workspace_dir / "derived"),
        logs_path=str(workspace_dir / "logs"),
    )
    for domain in manifest.domains.values():
        Path(domain.path).mkdir(parents=True, exist_ok=True)
    Path(manifest.backup.location).mkdir(parents=True, exist_ok=True)  # type: ignore[union-attr]
    Path(str(manifest.derived_cache_path)).mkdir(parents=True, exist_ok=True)
    Path(str(manifest.logs_path)).mkdir(parents=True, exist_ok=True)
    manifest.write(manifest_path)
    return manifest
