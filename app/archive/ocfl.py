"""Minimal OCFL 1.1-compatible object export with strict fixity validation."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from app.contracts.source_anchor_v2 import AnchorV2, SourceObjectV2


def _json_bytes(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(content)
    os.replace(temporary, path)


def _sha512(path: Path) -> str:
    return hashlib.sha512(path.read_bytes()).hexdigest()


def export_object(
    root: str | Path,
    *,
    source: SourceObjectV2,
    content: bytes,
    anchors: list[AnchorV2],
) -> dict[str, Any]:
    destination = Path(root)
    if destination.exists() and any(destination.iterdir()):
        raise ValueError("OCFL export destination must be empty")
    actual_sha256 = hashlib.sha256(content).hexdigest()
    if actual_sha256 != source.sha256 or len(content) != source.byte_size:
        raise ValueError("source content does not match declared fixity")
    for anchor in anchors:
        if anchor.state_for(source) != "CURRENT":
            raise ValueError(f"cannot export stale anchor: {anchor.anchor_id}")

    content_path = destination / "v1/content/original.bin"
    source_path = destination / "v1/content/source.json"
    anchors_path = destination / "v1/content/anchors.json"
    _write(content_path, content)
    _write(source_path, _json_bytes(source.model_dump(mode="json")))
    _write(anchors_path, _json_bytes([anchor.model_dump(mode="json") for anchor in anchors]))
    _write(destination / "0=ocfl_object_1.1", b"ocfl_object_1.1\n")

    manifest = {
        _sha512(content_path): ["v1/content/original.bin"],
        _sha512(source_path): ["v1/content/source.json"],
        _sha512(anchors_path): ["v1/content/anchors.json"],
    }
    inventory = {
        "id": source.source_id,
        "type": "https://ocfl.io/1.1/spec/#inventory",
        "digestAlgorithm": "sha512",
        "head": "v1",
        "manifest": manifest,
        "versions": {
            "v1": {
                "created": source.created_at,
                "message": "ArcheAxis evidence-preserving export",
                "state": {digest: paths for digest, paths in manifest.items()},
            }
        },
    }
    inventory_bytes = _json_bytes(inventory)
    _write(destination / "inventory.json", inventory_bytes)
    _write(destination / "inventory.json.sha512", (hashlib.sha512(inventory_bytes).hexdigest() + " inventory.json\n").encode("ascii"))
    return validate_object(destination)


def validate_object(root: str | Path) -> dict[str, Any]:
    object_root = Path(root)
    declaration = object_root / "0=ocfl_object_1.1"
    inventory_path = object_root / "inventory.json"
    sidecar = object_root / "inventory.json.sha512"
    if declaration.read_text(encoding="utf-8").strip() != "ocfl_object_1.1":
        raise ValueError("invalid OCFL object declaration")
    inventory_bytes = inventory_path.read_bytes()
    expected_inventory = sidecar.read_text(encoding="ascii").split()[0]
    if hashlib.sha512(inventory_bytes).hexdigest() != expected_inventory:
        raise ValueError("inventory fixity mismatch")
    inventory = json.loads(inventory_bytes)
    checked = 0
    for digest, paths in inventory.get("manifest", {}).items():
        for relative in paths:
            candidate = object_root / relative
            if not candidate.is_file() or _sha512(candidate) != digest:
                raise ValueError(f"content fixity mismatch: {relative}")
            checked += 1
    return {
        "valid": True,
        "object_id": inventory["id"],
        "head": inventory["head"],
        "checked_files": checked,
    }
