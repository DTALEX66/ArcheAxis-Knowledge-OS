"""Compose the runtime handshake the product shell validates, from the Core's own answer.

The Tauri frontend refuses to read any projection unless it first receives a handshake carrying
product identity, contract, versions, runtime mode, workspace, capabilities and migration state
(frontend/src/api/client.ts). The Rust Core answers only runtime, contract and schema version
(/api/v1/system/version), and says of itself that the contract is an outline.

This module is therefore the projection boundary for that one exchange: it takes the Core's answer
plus the identity facts the host owns and returns the document the shell expects. It reads nothing
and writes nothing - no database handle is opened here, and the Core stays the only canonical
writer. Keeping the composition in one pure function is what makes the slice testable before any
transport is wired to it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Final

# The values the shell pins. A handshake that disagrees is refused as incompatible, so these are
# requirements rather than defaults, and this module fails closed when it cannot meet them.
REQUIRED_PRODUCT_ID: Final = "archeaxis-workspace"
REQUIRED_API_CONTRACT: Final = "1.x"
READY_MIGRATION_STATE: Final = "ready"


class HandshakeCompositionError(ValueError):
    """The Core's answer or the supplied identity cannot form a valid handshake."""


@dataclass(frozen=True)
class RuntimeIdentity:
    """The facts the host owns, which the Core neither knows nor should."""

    product_name: str
    backend_version: str
    source_commit: str
    runtime_mode: str
    workspace_id: str
    capabilities: tuple[str, ...] = ()
    migration_state: str = READY_MIGRATION_STATE


def _require_non_empty(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise HandshakeCompositionError(f"{field} must be a non-empty string")
    return value


def compose_handshake(version: Any, identity: RuntimeIdentity) -> dict[str, Any]:
    """Return the handshake document the shell validates, or fail closed.

    The Core's answer supplies the schema version, which is the one field it truly owns. The
    contract string is reported under the name the shell expects; the Core's own `contract` value
    stays available as `core_contract` so the outline status is not lost in translation.
    """
    if not isinstance(version, dict):
        raise HandshakeCompositionError("core version answer must be an object")

    schema_version = version.get("schema_version")
    if not isinstance(schema_version, int) or isinstance(schema_version, bool) or schema_version < 1:
        raise HandshakeCompositionError("core version answer carries no usable schema_version")

    core_runtime = version.get("runtime")
    if not isinstance(core_runtime, str) or not core_runtime.strip():
        raise HandshakeCompositionError("core version answer carries no runtime identity")

    if identity.migration_state != READY_MIGRATION_STATE:
        raise HandshakeCompositionError(
            f"migration_state {identity.migration_state!r} is not ready; the shell refuses it"
        )

    capabilities = list(identity.capabilities)
    if any(not isinstance(item, str) or not item.strip() for item in capabilities):
        raise HandshakeCompositionError("capabilities must be non-empty strings")

    return {
        "product_id": REQUIRED_PRODUCT_ID,
        "product_name": _require_non_empty(identity.product_name, "product_name"),
        "api_contract": REQUIRED_API_CONTRACT,
        "backend_version": _require_non_empty(identity.backend_version, "backend_version"),
        "source_commit": _require_non_empty(identity.source_commit, "source_commit"),
        "schema_version": schema_version,
        "runtime_mode": _require_non_empty(identity.runtime_mode, "runtime_mode"),
        "workspace_id": _require_non_empty(identity.workspace_id, "workspace_id"),
        "capabilities": capabilities,
        "migration_state": identity.migration_state,
        # Kept so the Core's outline self-description survives the projection.
        "core_runtime": core_runtime,
        "core_contract": str(version.get("contract", ""))
    }
