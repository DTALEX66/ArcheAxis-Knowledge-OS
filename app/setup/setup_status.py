"""First-run setup readiness checks (AXW-DATA-402).

Every check is fail-closed and reuses the existing facilities:

* workspace layout  — ``shared/workspace_manifest`` (create/load/validate)
* path resolution   — ``shared/path_policy`` (deployment-form data root)
* capability store  — ``app/capability/store.CapabilityStore`` (init probe)
* legacy database   — ``shared.config.resolve_runtime_path`` (same path
  derivation as ``shared.storage.DB_PATH``, computed fresh per call so
  the check never depends on import-time state)

Steps returned by ``readiness_steps()`` each carry
``id / state / message / action_hint`` with states limited to
``pending | ready | blocked | completed``.
"""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from app.capability.store import CapabilityStore, CapabilityStoreError
from app.workspace.supervisor import BackendSupervisorState, supervisor
from shared.config import config, resolve_runtime_path
from shared.path_policy import resolve_paths
from shared.runtime_profile import resolve_runtime_mode
from shared.workspace_manifest import ASSET_DOMAINS, create_workspace, load

WORKSPACE_NAME = "workspace"
SETUP_STATUS_VERSION = "v1"

_STEP_STATES = ("pending", "ready", "blocked", "completed")

# Migration marker written by app/workspace/migrate.py once the legacy
# single database has been moved into the four-asset-domain layout.
MIGRATION_MANIFEST_NAME = "migration-manifest.json"
LEGACY_DATABASE_PATH = "data/cognitive_os.sqlite"


class SetupValidationError(ValueError):
    """Stable preflight error returned by the setup API."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class SetupRequest:
    mode: Literal["quick", "advanced"]
    root: str | None = None
    domains: dict[str, str] | None = None


def workspaces_base() -> Path:
    """Data-root-relative parent directory holding all workspaces."""
    policy = resolve_paths(resolve_runtime_mode())
    return policy.data_root / "workspaces"


def workspace_root() -> Path:
    """Canonical workspace directory for this deployment."""
    return workspaces_base() / WORKSPACE_NAME


def manifest_path() -> Path:
    return workspace_root() / "manifest.json"


def legacy_db_path() -> Path:
    """Legacy monolithic SQLite path (same derivation as shared.storage.DB_PATH)."""
    return resolve_runtime_path(LEGACY_DATABASE_PATH)


def capability_store_root() -> Path:
    """Capability store root (same default as app/capability/router.get_store)."""
    return resolve_runtime_path("data") / "capabilities"


# ── individual steps ────────────────────────────────────────────────────


def _workspace_exists_step() -> dict[str, str]:
    manifest = manifest_path()
    if manifest.is_file():
        try:
            load(manifest)
        except ValueError as exc:
            return {
                "id": "workspace_exists",
                "state": "blocked",
                "message": f"workspace manifest exists but is invalid: {exc}",
                "action_hint": (
                    "repair or remove the manifest, then retry "
                    "POST /api/v1/setup/initialize"
                ),
            }
        return {
            "id": "workspace_exists",
            "state": "completed",
            "message": "workspace exists with a valid manifest",
            "action_hint": "",
        }
    if workspace_root().exists():
        return {
            "id": "workspace_exists",
            "state": "blocked",
            "message": "workspace directory exists but has no manifest",
            "action_hint": (
                "remove or repair the directory, then retry "
                "POST /api/v1/setup/initialize"
            ),
        }
    return {
        "id": "workspace_exists",
        "state": "pending",
        "message": "workspace has not been created yet",
        "action_hint": "POST /api/v1/setup/initialize creates the workspace",
    }


def _manifest_valid_step() -> dict[str, str]:
    manifest = manifest_path()
    if not manifest.is_file():
        return {
            "id": "manifest_valid",
            "state": "pending",
            "message": "no manifest exists yet",
            "action_hint": "POST /api/v1/setup/initialize writes the workspace manifest",
        }
    try:
        load(manifest)
    except ValueError as exc:
        return {
            "id": "manifest_valid",
            "state": "blocked",
            "message": f"workspace manifest failed validation: {exc}",
            "action_hint": "repair or remove the manifest and re-initialize",
        }
    return {
        "id": "manifest_valid",
        "state": "completed",
        "message": "workspace manifest is valid",
        "action_hint": "",
    }


def _legacy_db_step() -> dict[str, str]:
    database = legacy_db_path()
    if not database.is_file():
        return {
            "id": "legacy_db_migration",
            "state": "ready",
            "message": "no legacy single database found",
            "action_hint": "",
        }
    if supervisor.state is BackendSupervisorState.MIGRATING:
        return {
            "id": "legacy_db_migration",
            "state": "blocked",
            "message": "schema migration is in progress",
            "action_hint": "wait for the migration to finish, then refresh status",
        }
    if (workspace_root() / MIGRATION_MANIFEST_NAME).is_file():
        return {
            "id": "legacy_db_migration",
            "state": "completed",
            "message": "legacy database migrated into the workspace layout",
            "action_hint": "",
        }
    if not manifest_path().is_file():
        return {
            "id": "legacy_db_migration",
            "state": "blocked",
            "message": f"legacy database found at {database} but no workspace exists",
            "action_hint": "POST /api/v1/setup/initialize to create the workspace first",
        }
    return {
        "id": "legacy_db_migration",
        "state": "pending",
        "message": f"legacy database found at {database}; migration not started",
        "action_hint": "run the legacy migration (app/workspace/migrate.migrate)",
    }


def _paths_writable_step() -> dict[str, str]:
    base = workspaces_base()
    try:
        base.mkdir(parents=True, exist_ok=True)
        probe = base / ".setup-write-probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
    except OSError as exc:
        return {
            "id": "paths_writable",
            "state": "blocked",
            "message": f"workspace data path is not writable: {exc}",
            "action_hint": "grant write permission on the data directory",
        }
    return {
        "id": "paths_writable",
        "state": "ready",
        "message": f"workspace data path is writable ({base})",
        "action_hint": "",
    }


def _capability_store_step() -> dict[str, str]:
    root = capability_store_root()
    try:
        CapabilityStore(root)
    except (CapabilityStoreError, OSError, ValueError) as exc:
        return {
            "id": "capability_store_ready",
            "state": "blocked",
            "message": f"capability store cannot be initialized at {root}: {exc}",
            "action_hint": "check permissions on the data directory",
        }
    return {
        "id": "capability_store_ready",
        "state": "ready",
        "message": f"capability store initializable at {root}",
        "action_hint": "",
    }


# ── aggregate views ─────────────────────────────────────────────────────


def readiness_steps() -> list[dict[str, str]]:
    """Run every step; a step failure never raises (fail-closed)."""
    steps = [
        _workspace_exists_step(),
        _manifest_valid_step(),
        _legacy_db_step(),
        _paths_writable_step(),
        _capability_store_step(),
    ]
    for step in steps:
        if step["state"] not in _STEP_STATES:
            step["state"] = "blocked"
    return steps


def setup_status() -> dict[str, object]:
    """Full status payload for GET /api/v1/setup/status."""
    steps = readiness_steps()
    ready = all(step["state"] in ("ready", "completed") for step in steps)
    workspace_id: str | None = None
    manifest = manifest_path()
    if manifest.is_file():
        try:
            workspace_id = load(manifest).workspace_id
        except ValueError:
            workspace_id = None
    return {
        "schema_version": SETUP_STATUS_VERSION,
        "ready": ready,
        "workspace_id": workspace_id,
        "workspace_root": str(workspace_root()),
        "legacy_db_present": legacy_db_path().is_file(),
        "steps": steps,
    }


def _normalize_path(value: str, field: str) -> Path:
    if not value or not value.strip():
        raise SetupValidationError("invalid_path", f"{field} must be a non-empty path")
    raw = Path(value).expanduser()
    if not raw.is_absolute():
        raise SetupValidationError("path_not_absolute", f"{field} must be an absolute path")
    return raw.resolve(strict=False)


def _is_nested(first: Path, second: Path) -> bool:
    try:
        second.relative_to(first)
        return first != second
    except ValueError:
        return False


def _preflight_domain_paths(paths: dict[str, Path]) -> dict[str, dict[str, object]]:
    values = list(paths.values())
    if len(set(values)) != len(values):
        raise SetupValidationError("duplicate_path", "four library paths must be distinct")
    for index, path in enumerate(values):
        for other in values[index + 1 :]:
            if _is_nested(path, other) or _is_nested(other, path):
                raise SetupValidationError("nested_path", "four library paths must not be nested")

    health: dict[str, dict[str, object]] = {}
    for domain, path in paths.items():
        parent = path.parent
        probe_parent = parent
        while not probe_parent.exists() and probe_parent != probe_parent.parent:
            probe_parent = probe_parent.parent
        if not probe_parent.exists():
            raise SetupValidationError("parent_missing", f"no existing parent directory for {domain}")
        if not os.access(probe_parent, os.W_OK):
            raise SetupValidationError("permission_denied", f"parent directory is not writable for {domain}")
        try:
            usage = shutil.disk_usage(probe_parent)
        except OSError as exc:
            raise SetupValidationError("disk_unavailable", f"cannot inspect disk for {domain}") from exc
        health[domain] = {
            "path": str(path),
            "parent": str(probe_parent),
            "free_bytes": usage.free,
            "readonly": False,
            "filesystem": "local-or-policy-unclassified",
            "removable": "unknown",
        }
    return health


def _domain_paths(request: SetupRequest) -> tuple[dict[str, Path], dict[str, dict[str, object]]]:
    if request.mode == "quick":
        root = _normalize_path(request.root or str(workspace_root()), "root")
        paths = {domain: root / domain for domain in ASSET_DOMAINS}
    else:
        if request.domains is None or set(request.domains) != set(ASSET_DOMAINS):
            raise SetupValidationError(
                "invalid_domains", "advanced mode requires exactly the four named library paths"
            )
        paths = {
            domain: _normalize_path(request.domains[domain], f"domains.{domain}")
            for domain in ASSET_DOMAINS
        }
    return paths, _preflight_domain_paths(paths)


def initialize_workspace(request: SetupRequest | None = None) -> dict[str, object]:
    """Create the workspace (idempotent — an existing valid workspace is
    returned as-is). Raises ``ValueError`` when an existing manifest is
    invalid (fail-closed)."""
    request = request or SetupRequest(mode="quick", root=str(workspace_root()))
    paths, health = _domain_paths(request)
    already_existed = manifest_path().is_file()
    # create_workspace is idempotent: it loads and returns the existing
    # manifest when one is already present.
    manifest = create_workspace(
        workspaces_base(),
        WORKSPACE_NAME,
        domain_paths={domain: str(path) for domain, path in paths.items()},
    )
    return {
        "initialized": True,
        "already_existed": already_existed,
        "workspace_id": manifest.workspace_id,
        "workspace_root": str(workspace_root()),
        "mode": request.mode,
        "library_health": health,
        "domains": {key: value.path for key, value in manifest.domains.items()},
        "status": setup_status(),
    }
