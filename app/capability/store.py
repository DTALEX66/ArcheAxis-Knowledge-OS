"""Capability Store v1 (AXW-CAP-501).

A partitioned, fail-closed store for capability packs:

    <root>/
      registry/     — index.json (single source of truth for records)
      staging/      — staged packs awaiting activation (hash-verified)
      installed/    — activated packs (atomic os.replace from staging)
      disabled/     — disabled packs
      quarantine/   — quarantined packs (with reason journal)
      packages/     — immutable pack archives (reserved for future use)
      plugins/      — builtin plugin registrations (AXW-CAP-503)

Lifecycle: stage(pack) → activate(staged_id) → disable/enable(id) →
quarantine(id, reason). Every transition moves the pack directory and
updates the registry index; hash verification happens at activate time,
so a tampered staged pack is refused (fail-closed).
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from shared.plugin_manifest import PluginManifest, load_manifest_from_mapping
from shared.plugin_manifest import load as load_plugin_manifest

REGISTRY_INDEX_VERSION = 1
MANIFEST_FILENAME = "plugin-manifest.json"
STAGE_SIDECAR = ".stage.json"
CAPABILITY_SIDECAR = ".capability.json"
QUARANTINE_JOURNAL = ".quarantine.json"

PARTITIONS = ("registry", "installed", "disabled", "staging", "quarantine", "packages", "plugins")


class CapabilityStoreError(ValueError):
    """Raised for any fail-closed store refusal (missing/invalid/tampered)."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _compute_content_hash(pack_dir: Path) -> str:
    """SHA-256 over the manifest bytes plus every other file (path+bytes),
    sorted by relative path — any file tamper changes the digest."""
    if not pack_dir.is_dir():
        raise CapabilityStoreError(f"pack directory missing: {pack_dir}")
    manifest_path = pack_dir / MANIFEST_FILENAME
    if not manifest_path.is_file():
        raise CapabilityStoreError(f"pack has no {MANIFEST_FILENAME}: {pack_dir}")
    hasher = hashlib.sha256()
    entries: list[tuple[str, bytes]] = []
    for path in sorted(pack_dir.rglob("*")):
        if path.is_file():
            rel = path.relative_to(pack_dir).as_posix()
            if rel in (STAGE_SIDECAR, CAPABILITY_SIDECAR, QUARANTINE_JOURNAL):
                continue
            entries.append((rel, path.read_bytes()))
    for rel, payload in entries:
        hasher.update(len(rel).to_bytes(4, "big"))
        hasher.update(rel.encode("utf-8"))
        hasher.update(payload)
    return hasher.hexdigest()


@dataclass(frozen=True)
class CapabilityRecord:
    plugin_id: str
    version: str
    status: str
    content_hash: str
    staged_at: str | None = None
    activated_at: str | None = None
    disabled_at: str | None = None
    quarantined_at: str | None = None
    quarantine_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "plugin_id": self.plugin_id,
            "version": self.version,
            "status": self.status,
            "content_hash": self.content_hash,
            "staged_at": self.staged_at,
            "activated_at": self.activated_at,
            "disabled_at": self.disabled_at,
            "quarantined_at": self.quarantined_at,
            "quarantine_reason": self.quarantine_reason,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CapabilityRecord:
        return cls(
            plugin_id=data["plugin_id"],
            version=data["version"],
            status=data["status"],
            content_hash=data["content_hash"],
            staged_at=data.get("staged_at"),
            activated_at=data.get("activated_at"),
            disabled_at=data.get("disabled_at"),
            quarantined_at=data.get("quarantined_at"),
            quarantine_reason=data.get("quarantine_reason"),
        )


class CapabilityStore:
    """Filesystem-backed capability store with fail-closed transitions."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.registry_dir = self.root / "registry"
        self.staging_dir = self.root / "staging"
        self.installed_dir = self.root / "installed"
        self.disabled_dir = self.root / "disabled"
        self.quarantine_dir = self.root / "quarantine"
        self.packages_dir = self.root / "packages"
        self.plugins_dir = self.root / "plugins"
        for partition in PARTITIONS:
            (self.root / partition).mkdir(parents=True, exist_ok=True)
        self._index_path = self.registry_dir / "index.json"
        self._activators: dict[str, Callable[[], Any]] = {}

    # ── registry index ──────────────────────────────────────────────────

    def _read_index(self) -> dict[str, dict[str, Any]]:
        if not self._index_path.exists():
            return {}
        try:
            data = json.loads(self._index_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise CapabilityStoreError(f"registry index unreadable: {self._index_path}") from exc
        records = data.get("records", {}) if isinstance(data, dict) else {}
        if not isinstance(records, dict):
            raise CapabilityStoreError("registry index has no records mapping")
        return records

    def _write_index(self, records: dict[str, dict[str, Any]]) -> None:
        payload = {"version": REGISTRY_INDEX_VERSION, "records": records}
        tmp = self._index_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        tmp.replace(self._index_path)

    def _record(self, plugin_id: str) -> CapabilityRecord:
        records = self._read_index()
        if plugin_id not in records:
            raise CapabilityStoreError(f"unknown capability: {plugin_id}")
        return CapabilityRecord.from_dict(records[plugin_id])

    # ── staging ─────────────────────────────────────────────────────────

    def stage(self, pack_path: str | Path) -> CapabilityRecord:
        """Copy a pack directory into staging after manifest validation."""
        source = Path(pack_path)
        manifest_path = source / MANIFEST_FILENAME
        if not source.is_dir():
            raise CapabilityStoreError(f"pack is not a directory: {source}")
        if not manifest_path.is_file():
            raise CapabilityStoreError(
                f"pack has no {MANIFEST_FILENAME}; refusing to stage {source}"
            )
        manifest: PluginManifest = load_plugin_manifest(manifest_path)

        manifest_bytes = manifest_path.read_bytes()
        staged_id = hashlib.sha256(manifest_bytes).hexdigest()[:16]
        staged_dir = self.staging_dir / staged_id
        if staged_dir.exists():
            shutil.rmtree(staged_dir)
        shutil.copytree(source, staged_dir)

        content_hash = _compute_content_hash(staged_dir)
        now = _utc_now()
        sidecar = {
            "staged_id": staged_id,
            "plugin_id": manifest.plugin_id,
            "version": manifest.version,
            "content_hash": content_hash,
            "staged_at": now,
            "status": "staged",
        }
        (staged_dir / STAGE_SIDECAR).write_text(
            json.dumps(sidecar, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        return CapabilityRecord(
            plugin_id=manifest.plugin_id,
            version=manifest.version,
            status="staged",
            content_hash=content_hash,
            staged_at=now,
        )

    # ── activation ──────────────────────────────────────────────────────

    def activate(self, staged_id: str) -> CapabilityRecord:
        """Verify the staged pack hash, then atomically move it to installed/."""
        staged_dir = self.staging_dir / staged_id
        sidecar_path = staged_dir / STAGE_SIDECAR
        if not staged_dir.is_dir() or not sidecar_path.is_file():
            raise CapabilityStoreError(f"unknown staged pack: {staged_id}")
        try:
            sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise CapabilityStoreError(f"staged sidecar unreadable: {staged_id}") from exc

        recorded_hash = sidecar.get("content_hash")
        actual_hash = _compute_content_hash(staged_dir)
        if not recorded_hash or actual_hash != recorded_hash:
            raise CapabilityStoreError(
                f"staged pack hash mismatch (tampered?); refusing to activate {staged_id}"
            )

        plugin_id = sidecar["plugin_id"]
        version = sidecar["version"]
        target = self.installed_dir / f"{plugin_id}@{version}"
        if target.exists():
            raise CapabilityStoreError(f"already installed: {plugin_id}@{version}")

        # Atomic move (same volume): staging/<id> → installed/<id>@<version>
        os.replace(staged_dir, target)

        now = _utc_now()
        records = self._read_index()
        records[plugin_id] = CapabilityRecord(
            plugin_id=plugin_id,
            version=version,
            status="installed",
            content_hash=recorded_hash,
            staged_at=sidecar.get("staged_at"),
            activated_at=now,
        ).to_dict()
        self._write_index(records)

        (target / CAPABILITY_SIDECAR).write_text(
            json.dumps(records[plugin_id], indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return self._record(plugin_id)

    # ── builtin injection (AXW-CAP-503) ─────────────────────────────────

    def install_builtin(
        self,
        manifest: PluginManifest | dict[str, Any],
        activator: Callable[[], Any] | None = None,
    ) -> CapabilityRecord:
        """Register a builtin plugin; idempotent and fail-closed.

        First call materializes the validated manifest under
        ``installed/<plugin_id>@<version>/`` (with its content hash
        recorded), registers ``plugins/<plugin_id>.json`` and invokes the
        optional ``activator`` exactly once. Subsequent calls with the
        same manifest are idempotent: the existing record is returned and
        the activator is NOT re-invoked. The installed pack is immutable:
        any modification is detected via content-hash re-verification and
        refused with CapabilityStoreError.
        """
        parsed = (
            manifest
            if isinstance(manifest, PluginManifest)
            else load_manifest_from_mapping(manifest)
        )
        plugin_id = parsed.plugin_id
        version = parsed.version
        target = self.installed_dir / f"{plugin_id}@{version}"

        records = self._read_index()
        existing = records.get(plugin_id)

        if target.is_dir():
            actual_hash = _compute_content_hash(target)
            if existing is None or existing.get("content_hash") != actual_hash:
                raise CapabilityStoreError(
                    f"builtin pack modified (hash mismatch); refusing to register {plugin_id}@{version}"
                )
            return CapabilityRecord.from_dict(existing)
        if existing is not None:
            raise CapabilityStoreError(
                f"builtin {plugin_id}@{version} already registered at status "
                f"{existing.get('status')!r}"
            )

        target.mkdir(parents=True, exist_ok=False)
        (target / MANIFEST_FILENAME).write_text(
            json.dumps(parsed.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        content_hash = _compute_content_hash(target)
        now = _utc_now()
        record = CapabilityRecord(
            plugin_id=plugin_id,
            version=version,
            status="installed",
            content_hash=content_hash,
            activated_at=now,
        )
        records[plugin_id] = record.to_dict()
        self._write_index(records)
        (target / CAPABILITY_SIDECAR).write_text(
            json.dumps(records[plugin_id], indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        (self.plugins_dir / f"{plugin_id}.json").write_text(
            json.dumps(
                {
                    "kind": "builtin",
                    "plugin_id": plugin_id,
                    "version": version,
                    "content_hash": content_hash,
                    "manifest": parsed.to_dict(),
                    "activated_at": now,
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        if activator is not None:
            self._activators[plugin_id] = activator
            activator()
        return record

    def get_activator(self, plugin_id: str) -> Callable[[], Any] | None:
        """Return the registered activator for a builtin plugin, if any."""
        return self._activators.get(plugin_id)

    # ── disable / enable ────────────────────────────────────────────────

    def disable(self, plugin_id: str) -> CapabilityRecord:
        record = self._record(plugin_id)
        if record.status != "installed":
            raise CapabilityStoreError(f"capability {plugin_id} is not installed")
        source = self.installed_dir / f"{plugin_id}@{record.version}"
        target = self.disabled_dir / f"{plugin_id}@{record.version}"
        if not source.is_dir():
            raise CapabilityStoreError(f"installed pack missing: {source}")
        if target.exists():
            raise CapabilityStoreError(f"disabled pack already exists: {target}")
        os.replace(source, target)

        records = self._read_index()
        updated = CapabilityRecord(
            plugin_id=record.plugin_id,
            version=record.version,
            status="disabled",
            content_hash=record.content_hash,
            staged_at=record.staged_at,
            activated_at=record.activated_at,
            disabled_at=_utc_now(),
        ).to_dict()
        records[plugin_id] = updated
        self._write_index(records)
        return CapabilityRecord.from_dict(updated)

    def enable(self, plugin_id: str) -> CapabilityRecord:
        record = self._record(plugin_id)
        if record.status != "disabled":
            raise CapabilityStoreError(f"capability {plugin_id} is not disabled")
        source = self.disabled_dir / f"{plugin_id}@{record.version}"
        target = self.installed_dir / f"{plugin_id}@{record.version}"
        if not source.is_dir():
            raise CapabilityStoreError(f"disabled pack missing: {source}")
        if target.exists():
            raise CapabilityStoreError(f"installed pack already exists: {target}")
        os.replace(source, target)

        records = self._read_index()
        updated = CapabilityRecord(
            plugin_id=record.plugin_id,
            version=record.version,
            status="installed",
            content_hash=record.content_hash,
            staged_at=record.staged_at,
            activated_at=record.activated_at,
        ).to_dict()
        records[plugin_id] = updated
        self._write_index(records)
        return CapabilityRecord.from_dict(updated)

    # ── quarantine ──────────────────────────────────────────────────────

    def quarantine(self, plugin_id: str, reason: str) -> CapabilityRecord:
        if not reason or not str(reason).strip():
            raise CapabilityStoreError("quarantine reason must be non-empty")
        record = self._record(plugin_id)
        if record.status not in ("installed", "disabled"):
            raise CapabilityStoreError(f"capability {plugin_id} is not installed/disabled")
        source_partition = self.installed_dir if record.status == "installed" else self.disabled_dir
        source = source_partition / f"{plugin_id}@{record.version}"
        target = self.quarantine_dir / f"{plugin_id}@{record.version}"
        if not source.is_dir():
            raise CapabilityStoreError(f"pack missing: {source}")
        if target.exists():
            raise CapabilityStoreError(f"quarantine target already exists: {target}")
        os.replace(source, target)

        now = _utc_now()
        (target / QUARANTINE_JOURNAL).write_text(
            json.dumps(
                {"plugin_id": plugin_id, "reason": reason, "quarantined_at": now},
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        records = self._read_index()
        updated = CapabilityRecord(
            plugin_id=record.plugin_id,
            version=record.version,
            status="quarantined",
            content_hash=record.content_hash,
            staged_at=record.staged_at,
            activated_at=record.activated_at,
            disabled_at=record.disabled_at,
            quarantined_at=now,
            quarantine_reason=reason,
        ).to_dict()
        records[plugin_id] = updated
        self._write_index(records)
        return CapabilityRecord.from_dict(updated)

    # ── queries ─────────────────────────────────────────────────────────

    def list_installed(self) -> list[CapabilityRecord]:
        records = self._read_index()
        return [
            CapabilityRecord.from_dict(record)
            for record in records.values()
            if record.get("status") == "installed"
        ]

    def list_all(self) -> list[CapabilityRecord]:
        records = self._read_index()
        return [CapabilityRecord.from_dict(record) for record in records.values()]
