"""Read-only Vault workbench boundary for the first compatibility vertical."""

from __future__ import annotations

from pathlib import Path

from shared.compat.import_session import ImportSession


class VaultWorkbenchError(ValueError):
    """Raised when a read-only Vault request is invalid."""


def _session(root: str | Path, store: str | Path) -> ImportSession:
    path = Path(root).expanduser().resolve()
    if not path.is_dir():
        raise VaultWorkbenchError("approved Vault root must be an existing directory")
    return ImportSession(Path(store), path)


def inspect_vault(*, root: str | Path, store: str | Path) -> dict[str, object]:
    """Return a safe file tree and loss summary without writing to the Vault."""
    session = _session(root, store)
    files = session.scan()
    entries: list[dict[str, object]] = []
    for item in sorted(files, key=lambda value: value.relative_path.casefold()):
        entries.append(
            {
                "relative_path": item.relative_path,
                "kind": "attachment" if item.is_binary else "canvas" if item.is_canvas else "markdown",
                "file_size": item.file_size,
                "source_hash": item.source_hash,
                "mime_type": item.mime_type,
                "frontmatter": item.frontmatter if not item.is_binary else {},
            }
        )
    return {
        "schema_version": "v1",
        "root_name": Path(root).resolve().name,
        "files": entries,
        "loss_report": session.loss_report(),
    }


def read_file(*, root: str | Path, store: str | Path, relative_path: str) -> dict[str, object]:
    """Read one Markdown/Canvas file by stable relative identity."""
    session = _session(root, store)
    item = session.import_path(Path(root) / relative_path)
    if item.is_binary:
        raise VaultWorkbenchError("binary attachments are metadata-only in the read-only workbench")
    return {
        "schema_version": "v1",
        "relative_path": item.relative_path,
        "raw_text": item.raw_text,
        "frontmatter": item.frontmatter,
        "body": item.body,
        "is_canvas": item.is_canvas,
        "source_hash": item.source_hash,
        "loss_report": session.loss_report(),
    }


def search_vault(*, root: str | Path, store: str | Path, query: str) -> dict[str, object]:
    """Search text in Markdown/Canvas files and return relative-path snippets."""
    term = query.strip().casefold()
    if not term:
        raise VaultWorkbenchError("search query must not be empty")
    session = _session(root, store)
    results: list[dict[str, object]] = []
    for item in session.scan():
        if item.is_binary:
            continue
        haystack = item.raw_text.casefold()
        if term not in haystack:
            continue
        index = haystack.index(term)
        results.append(
            {
                "relative_path": item.relative_path,
                "snippet": item.raw_text[max(0, index - 80) : index + len(term) + 120],
                "source_hash": item.source_hash,
            }
        )
    return {"schema_version": "v1", "query": query, "results": results}
