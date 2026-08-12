from __future__ import annotations

from pathlib import Path
from typing import Any

from app.schemas import CoreObject
from shared.approved_paths import ApprovedRoots, ApprovedRootsError

PROJECT_ROOT = Path(__file__).resolve().parents[2]
APPROVED_ROOTS = ApprovedRoots(source_roots=[PROJECT_ROOT])
DEFAULT_EXTENSIONS = {".md", ".markdown", ".txt"}
MAX_FILE_BYTES = 2_000_000
MAX_DIRECTORY_FILES = 100


class IngestionError(ValueError):
    pass


def _resolve_project_path(path: str) -> Path:
    if not str(path).strip():
        raise IngestionError("path is required")

    try:
        return APPROVED_ROOTS.resolve_source(path, must_exist=False)
    except ApprovedRootsError as exc:
        raise IngestionError("path must stay inside the ArcheAxis project root") from exc


def _relative_source(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


def _read_text(path: Path, max_bytes: int = MAX_FILE_BYTES) -> str:
    if not path.exists():
        raise IngestionError(f"file does not exist: {_relative_source(path)}")
    if not path.is_file():
        raise IngestionError(f"path is not a file: {_relative_source(path)}")
    if path.suffix.lower() not in DEFAULT_EXTENSIONS:
        raise IngestionError(f"unsupported file extension: {path.suffix}")
    if path.stat().st_size > max_bytes:
        raise IngestionError(f"file is too large: {_relative_source(path)}")

    return path.read_text(encoding="utf-8", errors="ignore").strip()


def _metadata(path: Path, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    stat = path.stat()
    data: dict[str, Any] = {
        "input_type": "file",
        "file_path": _relative_source(path),
        "file_name": path.name,
        "extension": path.suffix.lower(),
        "size_bytes": stat.st_size,
    }
    if extra:
        data.update(extra)
    return data


def ingest_file(
    path: str, source: str | None = None, metadata: dict[str, Any] | None = None
) -> CoreObject:
    resolved = _resolve_project_path(path)
    content = _read_text(resolved)
    source_name = source or _relative_source(resolved)

    return CoreObject(
        object_type="document",
        content=content,
        source=source_name,
        metadata=_metadata(resolved, metadata),
    )


def ingest_directory(
    path: str,
    pattern: str = "*.md",
    limit: int = 50,
    source: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> list[CoreObject]:
    resolved = _resolve_project_path(path)
    if not resolved.exists():
        raise IngestionError(f"directory does not exist: {_relative_source(resolved)}")
    if not resolved.is_dir():
        raise IngestionError(f"path is not a directory: {_relative_source(resolved)}")

    safe_limit = max(1, min(int(limit), MAX_DIRECTORY_FILES))
    docs: list[CoreObject] = []
    for file_path in sorted(resolved.rglob(pattern)):
        if not file_path.is_file():
            continue
        if file_path.suffix.lower() not in DEFAULT_EXTENSIONS:
            continue
        doc = ingest_file(
            str(file_path),
            source=source or _relative_source(file_path),
            metadata={"batch_root": _relative_source(resolved), **(metadata or {})},
        )
        docs.append(doc)
        if len(docs) >= safe_limit:
            break

    return docs
