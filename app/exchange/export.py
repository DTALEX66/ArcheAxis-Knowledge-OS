"""AXW-094A: open-exchange manifest/export.

Exports originals, derived artifacts, evidence, learning and AI assets
into an open, self-describing directory:

- ``manifest.json`` (schema_version, exported_at, tool + version, items)
- every item carries stable id, sha256, relative path, kind, and loss notes
- relationships (evidence anchors + relations) are recorded with hashes
- the export is verifiable: ``verify_export`` re-hashes every file and
  checks manifest coverage, so a corrupted or partial export is detected
  with an explicit failure message.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

EXPORT_SCHEMA_VERSION = "v1"

_ITEM_KINDS = {"raw", "derived", "evidence", "learning", "ai_asset"}


class ExportError(ValueError):
    """Raised when an export cannot be produced or verified."""


@dataclass(frozen=True)
class ExportItem:
    """One exported artifact with provenance and integrity metadata."""

    kind: str
    item_id: str
    sha256: str
    relative_path: str
    loss_notes: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "id": self.item_id,
            "sha256": self.sha256,
            "path": self.relative_path,
            "loss_notes": self.loss_notes,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExportItem:
        return cls(
            kind=str(data["kind"]),
            item_id=str(data["id"]),
            sha256=str(data["sha256"]),
            relative_path=str(data["path"]),
            loss_notes=str(data.get("loss_notes", "")),
            metadata=dict(data.get("metadata", {})),
        )


def _sha256_bytes(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _stable_relpath(item_id: str, suffix: str, kind: str) -> str:
    """Deterministic relative path inside the export, keyed by id."""
    return f"{kind}/{item_id}{suffix}"


def _copy_bytes(destination: Path, blob: bytes) -> str:
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(blob)
    return _sha256_bytes(blob)


def export_knowledge_exchange(
    *,
    destination: str | Path,
    raw_assets: dict[str, bytes] | None = None,
    evidence: dict[str, dict[str, Any]] | None = None,
    relations: list[dict[str, Any]] | None = None,
    learning: dict[str, bytes] | None = None,
    ai_assets: dict[str, dict[str, Any]] | None = None,
    tool_version: str = "archeaxis-workspace",
    overwrite: bool = False,
) -> dict[str, Any]:
    """Write an open exchange directory and return the manifest dict.

    Every source is optional; at least one item must be present. The
    manifest is written last, so a partial/crashed export is missing the
    manifest and fails verification with an explicit message.
    """
    destination = Path(destination)
    if destination.exists() and not destination.is_dir():
        raise ExportError(f"destination is not a directory: {destination}")
    if not overwrite and destination.exists() and any(destination.iterdir()):
        raise ExportError(
            f"destination is not empty (use overwrite=True to replace): {destination}"
        )

    items: list[ExportItem] = []

    for item_id, blob in (raw_assets or {}).items():
        if not isinstance(blob, bytes):
            raise ExportError(f"raw asset {item_id!r} must be bytes")
        rel = _stable_relpath(item_id, "", "raw")
        digest = _copy_bytes(destination / rel, blob)
        items.append(ExportItem(kind="raw", item_id=item_id, sha256=digest, relative_path=rel))

    for item_id, meta in (evidence or {}).items():
        payload = json.dumps(meta, ensure_ascii=False, sort_keys=True).encode("utf-8")
        rel = _stable_relpath(item_id, ".json", "evidence")
        digest = _copy_bytes(destination / rel, payload)
        items.append(
            ExportItem(
                kind="evidence",
                item_id=item_id,
                sha256=digest,
                relative_path=rel,
                metadata=meta,
            )
        )

    if relations:
        payload = json.dumps(relations, ensure_ascii=False, sort_keys=True).encode("utf-8")
        rel = "relations/relations.json"
        digest = _copy_bytes(destination / rel, payload)
        items.append(
            ExportItem(
                kind="evidence",
                item_id="relations",
                sha256=digest,
                relative_path=rel,
                metadata={"relation_count": len(relations)},
            )
        )

    for item_id, blob in (learning or {}).items():
        if not isinstance(blob, bytes):
            raise ExportError(f"learning artifact {item_id!r} must be bytes")
        rel = _stable_relpath(item_id, "", "learning")
        digest = _copy_bytes(destination / rel, blob)
        items.append(ExportItem(kind="learning", item_id=item_id, sha256=digest, relative_path=rel))

    for item_id, meta in (ai_assets or {}).items():
        payload = json.dumps(meta, ensure_ascii=False, sort_keys=True).encode("utf-8")
        rel = _stable_relpath(item_id, ".json", "ai_asset")
        digest = _copy_bytes(destination / rel, payload)
        items.append(
            ExportItem(
                kind="ai_asset",
                item_id=item_id,
                sha256=digest,
                relative_path=rel,
                metadata=meta,
            )
        )

    if not items:
        raise ExportError("nothing to export: at least one asset is required")

    manifest: dict[str, Any] = {
        "schema_version": EXPORT_SCHEMA_VERSION,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "tool": "archeaxis-knowledge-os",
        "tool_version": tool_version,
        "item_count": len(items),
        "items": [item.to_dict() for item in items],
    }
    manifest_rel = "manifest.json"
    # The manifest's own digest covers the body WITHOUT the self-referential
    # field; the digest is then added to the on-disk manifest, and
    # verification strips it back off before recomputing. Set the path
    # first so it participates in the hashed body.
    manifest["manifest_path"] = manifest_rel
    manifest_body = json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8")
    manifest_digest = _sha256_bytes(manifest_body)
    manifest["manifest_sha256"] = manifest_digest
    on_disk = json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8")
    (destination / manifest_rel).write_bytes(on_disk)
    return manifest


def verify_export(destination: str | Path) -> dict[str, Any]:
    """Verify an exchange directory: manifest present, coverage complete.

    Returns the manifest plus a per-item integrity verdict. Raises
    ``ExportError`` with an explicit failure message when the export is
    missing, partial, corrupted, or has an unsupported schema version.
    """
    destination = Path(destination)
    manifest_path = destination / "manifest.json"
    if not manifest_path.is_file():
        raise ExportError(
            f"export verification failed: manifest.json missing (partial export?): {destination}"
        )
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        raise ExportError(f"export verification failed: unreadable manifest: {exc}") from exc

    if manifest.get("schema_version") != EXPORT_SCHEMA_VERSION:
        raise ExportError(
            "export verification failed: unsupported schema version "
            f"{manifest.get('schema_version')!r} (expected {EXPORT_SCHEMA_VERSION!r})"
        )

    body = {key: value for key, value in manifest.items() if key != "manifest_sha256"}
    recomputed = _sha256_bytes(
        json.dumps(body, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8")
    )
    if manifest.get("manifest_sha256") != recomputed:
        raise ExportError("export verification failed: manifest.json hash mismatch")

    item_count = 0
    failures: list[str] = []
    for raw_item in manifest.get("items", []):
        try:
            item = ExportItem.from_dict(raw_item)
        except (KeyError, TypeError, ValueError) as exc:
            failures.append(f"invalid item entry {raw_item!r}: {exc}")
            continue
        item_count += 1
        target = destination / item.relative_path
        if not target.is_file():
            failures.append(f"{item.kind}:{item.item_id} missing file {item.relative_path}")
            continue
        actual = _sha256_file(target)
        if actual != item.sha256:
            failures.append(
                f"{item.kind}:{item.item_id} hash mismatch "
                f"(expected {item.sha256[:16]}…, got {actual[:16]}…) for {item.relative_path}"
            )

    if failures:
        raise ExportError(
            "export verification failed:\n- " + "\n- ".join(failures[:20])
        )
    if item_count != manifest.get("item_count"):
        raise ExportError(
            f"export verification failed: item_count mismatch "
            f"(manifest says {manifest.get('item_count')}, found {item_count})"
        )

    return {"manifest": manifest, "verified_items": item_count}


def extract_exchange_items(
    *,
    raw_root: str | Path | None = None,
    evidence_db: str | Path | None = None,
    learning_root: str | Path | None = None,
) -> dict[str, Any]:
    """Collect live-store artifacts into export-ready payloads.

    Convenience bridge from the on-disk stores to ``export_knowledge_exchange``:
    raw originals from a RawAssetStore root, evidence anchors from the
    SQLite evidence DB, learning artifacts from a learning root. Returns
    keyword arguments ready for the export function.
    """
    payload: dict[str, Any] = {"raw_assets": {}, "evidence": {}, "learning": {}}

    if raw_root is not None:
        for digest_path in sorted((Path(raw_root) / "originals").glob("*")):
            if digest_path.is_file():
                payload["raw_assets"][digest_path.name] = digest_path.read_bytes()

    if evidence_db is not None:
        from app.evidence.anchor import list_evidence_anchors

        anchors = list_evidence_anchors(db=evidence_db)
        for anchor in anchors:
            payload["evidence"][anchor.anchor_id] = {
                "raw_sha256": anchor.raw_sha256,
                "source_revision": anchor.source_revision,
                "locator": anchor.locator,
            }

    if learning_root is not None:
        learning_dir = Path(learning_root)
        for artifact_path in sorted(learning_dir.rglob("*")):
            if artifact_path.is_file() and artifact_path.suffix != ".json":
                rel = artifact_path.relative_to(learning_dir).as_posix()
                payload["learning"][rel] = artifact_path.read_bytes()

    return payload
