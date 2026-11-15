"""Exact owned workspace report check for Core's Windows verbatim path.

Rust ``canonicalize()`` returns a Windows extended-local verbatim path and SQLite reports
that string verbatim in ``/api/v1/system/version.workspace_db``.  Probes must
not hand that UNC-looking value to path guards, and must not strip prefixes
unconditionally.  Only the exact ordinary path this launch owns, or its exact
extended-local spelling, is accepted; the known ordinary Path is returned so
the existing owned-path guards stay unchanged.
"""
from __future__ import annotations

from pathlib import Path

EXTENDED_LOCAL = "\\\\?\\"


def checked_workspace_report(reported, expected, *, repo=None):
    """Return the known ordinary owned path only for an exact Core report."""
    if not isinstance(expected, Path) or not expected.is_absolute():
        raise ValueError("invalid expected owned workspace path")
    if expected.drive.upper() in {"E:", "F:"} or ".." in expected.parts:
        raise ValueError("invalid expected owned workspace path")
    if expected.parent.name != "data" or expected.suffix != ".sqlite":
        raise ValueError("invalid expected owned workspace path")
    if repo is not None:
        root = Path(repo)
        if expected.drive != root.drive or not expected.is_relative_to(root / ".project-local/runs"):
            raise ValueError("expected workspace is outside this project's owned runs")
    plain = str(expected)
    if not isinstance(reported, str) or reported not in (plain, EXTENDED_LOCAL + plain):
        raise ValueError("Core workspace differs from the exact launched owned workspace")
    return expected
