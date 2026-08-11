"""Read-only Vault workbench boundary for the first compatibility vertical."""

from __future__ import annotations

import contextlib
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


def write_file(
    *,
    root: str | Path,
    store: str | Path,
    relative_path: str,
    content: str,
    expected_hash: str | None = None,
) -> dict[str, object]:
    """H3 C4-safe round-trip write: expected-hash optimistic lock + atomic write.

    - Verifies the target exists and is a text (Markdown/Canvas) file.
    - If ``expected_hash`` is provided and does not match the on-disk source
      hash, raises ``VaultWorkbenchConflict`` (fail-closed; caller must re-read).
    - Backs up the current bytes under the store boundary before replacing,
      so every write is revertible.
    - Writes via a sibling temp file + ``os.replace`` (atomic on same volume).
    """
    import hashlib
    import os
    import tempfile
    from datetime import datetime, timezone

    path = Path(root).expanduser().resolve()
    if not path.is_dir():
        raise VaultWorkbenchError("approved Vault root must be an existing directory")
    target = (path / relative_path).resolve()
    if path not in target.parents:
        raise VaultWorkbenchError("relative_path must stay inside the Vault root")
    if not target.is_file():
        raise VaultWorkbenchError("target file does not exist")
    if target.read_bytes().startswith(b"PK\x03\x04"):
        raise VaultWorkbenchError("binary attachments are metadata-only in the workbench")

    current = target.read_bytes()
    current_hash = hashlib.sha256(current).hexdigest()
    if expected_hash is not None and expected_hash != current_hash:
        raise VaultWorkbenchConflictError(
            "expected-hash mismatch; the Vault file changed on disk since it was read",
            current_hash=current_hash,
        )

    new_bytes = content.encode("utf-8")
    store_path = Path(store).expanduser().resolve()
    backup_dir = store_path / "vault-backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
    backup = backup_dir / f"{target.name}-{stamp}.bak"
    backup.write_bytes(current)

    fd, tmp_name = tempfile.mkstemp(dir=str(target.parent), prefix=".awx-", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(new_bytes)
        os.replace(tmp_name, target)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(tmp_name)
        raise

    new_hash = hashlib.sha256(new_bytes).hexdigest()
    return {
        "schema_version": "v1",
        "relative_path": relative_path,
        "source_hash": new_hash,
        "expected_hash_checked": expected_hash is not None,
        "backup_path": str(backup),
        "revert": f"restore {backup} over {target}",
    }


class VaultWorkbenchConflictError(VaultWorkbenchError):
    """Raised when an expected-hash optimistic lock fails (409)."""

    def __init__(self, message: str, *, current_hash: str) -> None:
        super().__init__(message)
        self.current_hash = current_hash
