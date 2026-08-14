"""Runtime profile v1 (AXW-RUN-202) — fail-closed profile loader.

Profiles live in ``config/profiles/<name>.yaml`` and are selected at
runtime through the canonical ``ARCHEAXIS_RUNTIME_PROFILE`` environment
variable (default: ``installed-stable``). Unknown profile names fail
closed with ``ValueError`` instead of silently degrading.

Naming contract: ``ARCHEAXIS_*`` is canonical, ``COGNITIVE_*`` is legacy.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_PROFILES_DIR = _PROJECT_ROOT / "config" / "profiles"

_SUPPORTED_PROFILES = frozenset(
    {"installed-stable", "green-stable", "portable-stable", "external-dev"}
)
_BACKENDS = frozenset({"bundled", "external-source"})
_DATA_POLICIES = frozenset(
    {
        "installed-user-data",
        "selected-user-data",
        "portable-root-only",
        "isolated-test-workspace",
    }
)

DEFAULT_RUNTIME_MODE = "installed-stable"


@dataclass(frozen=True)
class RuntimeProfile:
    """Validated contents of one runtime profile YAML file."""

    name: str
    backend: str
    data_policy: str
    reload: bool
    source_root: str | None = None


def load_profile(name: str) -> RuntimeProfile:
    """Load and validate ``config/profiles/<name>.yaml`` (fail-closed).

    Raises ``ValueError`` for unknown names, missing files, or invalid
    field values — a broken profile must never silently degrade behavior.
    """
    if name not in _SUPPORTED_PROFILES:
        supported = ", ".join(sorted(_SUPPORTED_PROFILES))
        raise ValueError(f"unknown runtime profile: {name!r}; expected one of {supported}")
    path = _PROFILES_DIR / f"{name}.yaml"
    if not path.is_file():
        raise ValueError(f"runtime profile file not found: {path}")
    try:
        import yaml

        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except Exception as exc:
        raise ValueError(f"unable to parse runtime profile: {path}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"runtime profile must be a mapping: {path}")

    backend = data.get("backend")
    data_policy = data.get("data_policy")
    reload = data.get("reload")
    source_root = data.get("source_root")

    if backend not in _BACKENDS:
        raise ValueError(
            f"profile {name}: backend must be one of {sorted(_BACKENDS)}, got {backend!r}"
        )
    if data_policy not in _DATA_POLICIES:
        raise ValueError(
            f"profile {name}: data_policy must be one of {sorted(_DATA_POLICIES)}, "
            f"got {data_policy!r}"
        )
    if not isinstance(reload, bool):
        raise ValueError(f"profile {name}: reload must be a boolean, got {reload!r}")
    if source_root is not None and not isinstance(source_root, str):
        raise ValueError(f"profile {name}: source_root must be a string or absent")
    return RuntimeProfile(
        name=name,
        backend=backend,
        data_policy=data_policy,
        reload=reload,
        source_root=source_root,
    )


def resolve_runtime_mode() -> str:
    """Resolve the active runtime mode from ``ARCHEAXIS_RUNTIME_PROFILE``.

    Defaults to ``installed-stable`` when the variable is unset; an
    unknown value raises ``ValueError`` (fail-closed).
    """
    value = os.getenv("ARCHEAXIS_RUNTIME_PROFILE", "").strip() or DEFAULT_RUNTIME_MODE
    if value not in _SUPPORTED_PROFILES:
        supported = ", ".join(sorted(_SUPPORTED_PROFILES))
        raise ValueError(
            f"invalid ARCHEAXIS_RUNTIME_PROFILE: {value!r}; expected one of {supported}"
        )
    return value
