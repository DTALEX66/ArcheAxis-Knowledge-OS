"""Isolated test workspace cloning (AXW-DEV-303).

``clone_test_workspace`` deep-copies a workspace's four asset domains
(real files) plus its manifest file into a brand-new destination with a
fresh ``workspace_id`` — the isolation primitive behind the
``external-dev`` profile's ``isolated-test-workspace`` data policy.

Fail-closed rules:

* the destination must not already exist (raise instead of merging);
* the source must be a directory containing a workspace manifest
  (canonical ``manifest.json``, schema ``workspace-manifest.schema.json``;
  the alternate ``workspace-manifest.json`` name is also accepted);
* the manifest is re-validated structurally and the four asset domain
  paths are rewritten to point into the clone;
* every top-level manifest field that is not rewritten (e.g.
  ``data_ownership``, ``capability_lock``, ``backup``) is preserved
  verbatim;
* a partial copy is rolled back before re-raising (no half-clones).
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any
from uuid import uuid4

from shared.workspace_manifest import ASSET_DOMAINS

# Canonical manifest name first; the task-pack spelling is accepted too.
MANIFEST_FILENAMES: tuple[str, ...] = ("manifest.json", "workspace-manifest.json")

_REQUIRED_MANIFEST_FIELDS = ("schema_version", "workspace_id", "created_at", "name", "domains")


def _load_manifest(manifest_path: Path) -> dict[str, Any]:
    try:
        raw = manifest_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ValueError(f"cannot read workspace manifest {manifest_path}") from exc
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid workspace manifest JSON in {manifest_path}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"workspace manifest must be an object: {manifest_path}")
    missing = [key for key in _REQUIRED_MANIFEST_FIELDS if key not in data]
    if missing:
        raise ValueError(
            f"workspace manifest {manifest_path} missing required field(s): {sorted(missing)}"
        )
    domains = data.get("domains")
    if not isinstance(domains, dict):
        raise ValueError(f"workspace manifest {manifest_path}: domains must be an object")
    for key in ASSET_DOMAINS:
        entry = domains.get(key)
        if not isinstance(entry, dict) or not isinstance(entry.get("path"), str):
            raise ValueError(
                f"workspace manifest {manifest_path}: domains.{key} missing a string path"
            )
    return data


def clone_test_workspace(src_workspace: str | Path, dst: str | Path) -> dict[str, Any]:
    """Clone a workspace's four asset domains + manifest into ``dst``.

    Copies the real domain directories (``shutil.copytree``) and the
    manifest file, regenerates ``workspace_id`` as a fresh UUID4 string,
    rewrites domain paths to the clone location, and preserves every
    other top-level manifest field (including ``data_ownership``)
    verbatim.

    Raises ``ValueError`` when the source is missing/malformed or when
    ``dst`` already exists (fail-closed). Returns the new manifest dict.
    """
    src = Path(src_workspace)
    dst_path = Path(dst)
    if not src.is_dir():
        raise ValueError(f"source workspace not found: {src}")
    if dst_path.exists():
        raise ValueError(f"destination already exists: {dst_path}")

    manifest_path = next(
        (src / name for name in MANIFEST_FILENAMES if (src / name).is_file()), None
    )
    if manifest_path is None:
        raise ValueError(f"no workspace manifest found in source workspace: {src}")
    manifest = _load_manifest(manifest_path)

    new_manifest: dict[str, Any] = dict(manifest)
    new_manifest["workspace_id"] = str(uuid4())
    new_domains: dict[str, Any] = {}
    for key in ASSET_DOMAINS:
        entry = dict(manifest["domains"][key])
        new_domains[key] = entry

    try:
        dst_path.mkdir(parents=True)
        for key in ASSET_DOMAINS:
            entry = new_domains[key]
            src_domain = Path(str(entry["path"]))
            if not src_domain.is_dir():
                raise ValueError(f"domain directory missing in source workspace: {src_domain}")
            dst_domain = dst_path / key
            shutil.copytree(src_domain, dst_domain)
            entry["path"] = str(dst_domain)
        new_manifest["domains"] = new_domains
        # Copy the real manifest file, then persist the rewritten manifest.
        shutil.copy2(manifest_path, dst_path / manifest_path.name)
        (dst_path / manifest_path.name).write_text(
            json.dumps(new_manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    except Exception:
        shutil.rmtree(dst_path, ignore_errors=True)
        raise
    return new_manifest
