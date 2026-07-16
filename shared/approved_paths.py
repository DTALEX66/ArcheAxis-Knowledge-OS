"""Fail-closed approved source/output path containment."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path


class ApprovedRootsError(ValueError):
    """Raised when a path is missing, ambiguous, or outside an approved root."""


class ApprovedRoots:
    """Resolve local paths only inside explicit approved roots.

    Roots must already exist and be directories. Candidate paths are resolved
    before containment checks, so traversal, symlink, and Windows junction
    escapes are rejected. Output files may be new; their approved root must
    exist before the operation starts.
    """

    def __init__(
        self,
        *,
        source_roots: Iterable[str | Path] = (),
        output_roots: Iterable[str | Path] = (),
    ) -> None:
        self.source_roots = self._normalize_roots(source_roots, "source")
        self.output_roots = self._normalize_roots(output_roots, "output")
        if not self.source_roots and not self.output_roots:
            raise ApprovedRootsError("at least one explicit source or output root is required")

    @staticmethod
    def _normalize_roots(roots: Iterable[str | Path], label: str) -> tuple[Path, ...]:
        normalized: list[Path] = []
        for raw in roots:
            if not str(raw).strip():
                raise ApprovedRootsError(f"{label} root must not be empty")
            root = Path(raw).expanduser().resolve()
            if not root.is_dir():
                raise ApprovedRootsError(f"{label} root must be an existing directory: {root}")
            if root not in normalized:
                normalized.append(root)
        return tuple(normalized)

    @staticmethod
    def _candidate(raw: str | Path, root: Path) -> Path:
        path = Path(raw).expanduser()
        return path if path.is_absolute() else root / path

    @staticmethod
    def _inside(candidate: Path, root: Path) -> bool:
        try:
            candidate.relative_to(root)
            return True
        except ValueError:
            return False

    def _resolve(self, raw: str | Path, roots: tuple[Path, ...], label: str, *, must_exist: bool) -> Path:
        if not str(raw).strip():
            raise ApprovedRootsError(f"{label} path must not be empty")
        for root in roots:
            candidate = self._candidate(raw, root).resolve(strict=False)
            if not self._inside(candidate, root):
                continue
            if must_exist and not candidate.exists():
                raise ApprovedRootsError(f"{label} path does not exist: {raw}")
            return candidate
        raise ApprovedRootsError(f"{label} path is outside approved roots: {raw}")

    def resolve_source(self, path: str | Path, *, must_exist: bool = True) -> Path:
        """Resolve an existing source path inside an approved source root."""
        return self._resolve(path, self.source_roots, "source", must_exist=must_exist)

    def resolve_output(self, path: str | Path) -> Path:
        """Resolve a new or existing output path inside an approved output root."""
        return self._resolve(path, self.output_roots, "output", must_exist=False)

    def relative_output(self, path: str | Path) -> Path:
        """Return a validated path relative to the matching output root."""
        resolved = Path(path).expanduser().resolve(strict=False)
        for root in self.output_roots:
            if self._inside(resolved, root):
                return resolved.relative_to(root)
        raise ApprovedRootsError(f"output path is outside approved roots: {path}")
