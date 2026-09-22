"""Resolve active and explicitly selected task-pack paths.

The active R6 pack is the default. Historical packs remain runnable only when
their path is supplied explicitly, so audit tools cannot silently drift back to
an older pack.
"""

from pathlib import Path

DEFAULT_PACK_RELATIVE = Path("docs/authority/taskpack-0919-r6")


def default_pack_root(repo_root: Path) -> Path:
    return Path(repo_root) / DEFAULT_PACK_RELATIVE


def resolve_pack_root(repo_root: Path, pack_root: Path | None = None) -> Path:
    selected = Path(pack_root) if pack_root is not None else DEFAULT_PACK_RELATIVE
    if not selected.is_absolute():
        selected = Path(repo_root) / selected
    return selected
