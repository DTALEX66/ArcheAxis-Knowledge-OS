"""Four-form runtime path policy (AXW-DATA-404).

Resolves the data/program roots for each deployment form and refuses any
resolution that would fall back to an uncontrolled location:

- ``installed-stable`` — data lives under %LOCALAPPDATA%/ArcheAxis/Workspace,
  or the desktop launcher's sanitized authoritative data root; the program
  directory (where the executable lives) is read-only.
- ``green-stable``    — data defaults to the same LOCALAPPDATA location but
  may be redirected with ARCHEAXIS_DATA_DIR.
- ``portable-stable`` — data must stay inside the desktop launcher's sanitized
  data root or ARCHEAXIS_PORTABLE_ROOT/data; when neither is set, resolution
  raises ValueError. It never falls back to LOCALAPPDATA or the user home.
- ``external-dev``    — data is confined to the isolated test workspace and
  must match the desktop launcher's authoritative root when present.

Every ``resolve_data()`` result is re-checked against the allowed root, so
``..`` traversal or symlink escapes fail closed instead of leaking data
outside the deployment's boundary.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

DeploymentMode = Literal["installed-stable", "green-stable", "portable-stable", "external-dev"]

MODES: tuple[DeploymentMode, ...] = (
    "installed-stable",
    "green-stable",
    "portable-stable",
    "external-dev",
)

_INSTALLED_DATA_SUBROOT = Path("ArcheAxis") / "Workspace"


class PathPolicyError(ValueError):
    """Raised when a deployment form cannot be resolved safely."""


@dataclass(frozen=True)
class PathPolicy:
    """Resolved roots and confinement rules for one deployment form."""

    mode: DeploymentMode
    data_root: Path
    program_dir: Path
    program_readonly: bool
    allowed_roots: tuple[Path, ...]

    def resolve_data(self, relative: str | Path) -> Path:
        """Resolve a relative path under the data root, fail-closed.

        The resolved path must stay inside the data root; anything else
        (absolute input, `..` traversal, symlink escape) raises
        PathPolicyError.
        """
        candidate = Path(relative)
        if candidate.is_absolute():
            raise PathPolicyError(
                f"absolute path not allowed under {self.mode}: {candidate}"
            )
        resolved = (self.data_root / candidate).resolve()
        try:
            resolved.relative_to(self.data_root.resolve())
        except ValueError as exc:
            raise PathPolicyError(
                f"path escapes data root under {self.mode}: {candidate}"
            ) from exc
        return resolved

    def is_within_data(self, path: str | Path) -> bool:
        """True only when the path is inside the data root (no exceptions)."""
        try:
            Path(path).resolve().relative_to(self.data_root.resolve())
            return True
        except (OSError, ValueError):
            return False


def _local_app_data() -> Path:
    value = os.getenv("LOCALAPPDATA", "").strip() or os.getenv("LOCAL_APP_DATA", "").strip()
    if not value:
        raise PathPolicyError(
            "installed/green deployment requires %LOCALAPPDATA% to be set"
        )
    return Path(value)


def _program_dir() -> Path:
    """Directory of the running executable (fallback: this package's root)."""
    executable = getattr(sys, "executable", None)
    if executable and Path(executable).parent.is_dir():
        return Path(executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def _launcher_data_dir() -> Path | None:
    """Return the desktop launcher's authoritative child data root, if any."""
    value = os.getenv("ARCHEAXIS_LAUNCHER_DATA_DIR", "").strip()
    if not value:
        return None
    root = Path(value).expanduser()
    if not root.is_absolute():
        raise PathPolicyError("ARCHEAXIS_LAUNCHER_DATA_DIR must be absolute")
    return root.resolve()


def resolve_paths(mode: DeploymentMode) -> PathPolicy:
    """Resolve the path policy for a deployment form (fail-closed)."""
    if mode not in MODES:
        raise PathPolicyError(f"unknown deployment mode: {mode!r}")

    if mode == "installed-stable":
        data_root = _launcher_data_dir() or (_local_app_data() / _INSTALLED_DATA_SUBROOT)
        return PathPolicy(
            mode=mode,
            data_root=data_root,
            program_dir=_program_dir(),
            program_readonly=True,
            allowed_roots=(data_root,),
        )

    if mode == "green-stable":
        override = os.getenv("ARCHEAXIS_DATA_DIR", "").strip() or os.getenv(
            "COGNITIVE_DATA_DIR", ""
        ).strip()
        data_root = (
            Path(override) if override else _local_app_data() / _INSTALLED_DATA_SUBROOT
        )
        return PathPolicy(
            mode=mode,
            data_root=data_root,
            program_dir=_program_dir(),
            program_readonly=True,
            allowed_roots=(data_root,),
        )

    if mode == "portable-stable":
        launcher_root = _launcher_data_dir()
        if launcher_root is not None:
            return PathPolicy(
                mode=mode,
                data_root=launcher_root,
                program_dir=_program_dir(),
                program_readonly=False,
                allowed_roots=(launcher_root,),
            )
        portable_root = os.getenv("ARCHEAXIS_PORTABLE_ROOT", "").strip()
        if not portable_root:
            raise PathPolicyError(
                "portable deployment requires ARCHEAXIS_PORTABLE_ROOT; "
                "refusing to fall back to LOCALAPPDATA or the user directory"
            )
        portable = Path(portable_root).resolve()
        data_root = portable / "data"
        return PathPolicy(
            mode=mode,
            data_root=data_root,
            program_dir=portable,
            program_readonly=False,
            allowed_roots=(portable, data_root),
        )

    # external-dev
    test_root = os.getenv("ARCHEAXIS_TEST_WORKSPACE_ROOT", "").strip()
    if not test_root:
        raise PathPolicyError(
            "external-dev deployment requires ARCHEAXIS_TEST_WORKSPACE_ROOT"
        )
    isolated = Path(test_root).resolve()
    launcher_root = _launcher_data_dir()
    if launcher_root is not None and launcher_root != isolated:
        raise PathPolicyError(
            "external-dev test root does not match the launcher-owned data root"
        )
    return PathPolicy(
        mode=mode,
        data_root=isolated,
        program_dir=_program_dir(),
        program_readonly=False,
        allowed_roots=(isolated,),
    )
