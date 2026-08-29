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
    current_bytes = target.read_bytes()
    if current_bytes.startswith(b"PK\x03\x04"):
        raise VaultWorkbenchError("binary attachments are metadata-only in the workbench")

    # Hash the canonical text form (read_text normalises CRLF→LF) so the
    # source_hash returned by read_file always matches what write_file
    # compares.  The raw bytes are preserved separately for faithful backup.
    current_text = target.read_text(encoding="utf-8")
    current_hash = hashlib.sha256(current_text.encode("utf-8")).hexdigest()
    if expected_hash is not None and expected_hash != current_hash:
        raise VaultWorkbenchConflictError(
            "expected-hash mismatch; the Vault file changed on disk since it was read",
            current_hash=current_hash,
        )

    new_bytes = content.encode("utf-8")
    store_path = Path(store).expanduser().resolve()
    # ``store`` is the SQLite database file path; backups live beside it.
    backup_dir = store_path.parent / "vault-backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
    backup = backup_dir / f"{target.name}-{stamp}.bak"
    backup.write_bytes(current_bytes)

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


def write_canvas(
    *,
    root: str | Path,
    store: str | Path,
    relative_path: str,
    canvas: dict[str, object],
    expected_hash: str | None = None,
) -> dict[str, object]:
    """AXW-043B: validate + write a JSON Canvas document with C3 safety.

    - Reuses the C3 revision-safe machinery (expected-hash optimistic lock,
      sibling-temp atomic replace, revertible backup, fail-closed conflicts).
    - Validates the document against the JSON Canvas spec before writing;
      invalid documents are rejected and the file is left untouched.
    - Unknown fields are preserved on round-trip (never silently dropped).
    """
    import json

    from shared.json_canvas import CanvasError, validate_json_canvas

    try:
        normalized = validate_json_canvas(canvas)
    except CanvasError as exc:
        raise VaultWorkbenchError(f"invalid JSON Canvas: {exc}") from None

    # Serialize with the same key order as provided (unknown fields kept),
    # stable 2-space indent, ASCII-escaped-safe round trip via utf-8.
    content = json.dumps(normalized, ensure_ascii=False, indent=2)
    return write_file(
        root=root,
        store=store,
        relative_path=relative_path,
        content=content + "\n",
        expected_hash=expected_hash,
    )


def read_canvas(
    *,
    root: str | Path,
    store: str | Path,
    relative_path: str,
) -> dict[str, object]:
    """AXW-043B: read + validate a JSON Canvas document.

    Returns the parsed document (unknown fields preserved) plus the source
    hash for optimistic-lock writes. Raises when the file is not a valid
    JSON Canvas — the caller must not trust malformed canvas data.
    """
    import json

    from shared.json_canvas import CanvasError, validate_json_canvas

    result = read_file(root=root, store=store, relative_path=relative_path)
    raw = result["raw_text"]
    try:
        data = json.loads(raw)
    except (ValueError, TypeError) as exc:
        raise VaultWorkbenchError(f"invalid JSON Canvas: not valid JSON: {exc}") from None
    try:
        validate_json_canvas(data)
    except CanvasError as exc:
        raise VaultWorkbenchError(f"invalid JSON Canvas: {exc}") from None
    result["canvas"] = data
    return result


class VaultWorkbenchConflictError(VaultWorkbenchError):
    """Raised when an expected-hash optimistic lock fails (409)."""

    def __init__(self, message: str, *, current_hash: str) -> None:
        super().__init__(message)
        self.current_hash = current_hash


def _backup_dir(store: str | Path) -> Path:
    store_path = Path(store).expanduser().resolve()
    return store_path.parent / "vault-backups"


def list_backups(*, store: str | Path, relative_path: str) -> dict[str, object]:
    """List revertible backups for one Vault file (newest first)."""
    directory = _backup_dir(store)
    prefix = f"{Path(relative_path).name}-"
    backups: list[dict[str, object]] = []
    if directory.is_dir():
        for candidate in sorted(directory.glob(f"{prefix}*.bak"), reverse=True):
            backups.append(
                {
                    "backup_name": candidate.name,
                    "file_size": candidate.stat().st_size,
                    "modified": candidate.stat().st_mtime,
                }
            )
    return {"schema_version": "v1", "relative_path": relative_path, "backups": backups}


def restore_backup(
    *,
    root: str | Path,
    store: str | Path,
    relative_path: str,
    backup_name: str,
) -> dict[str, object]:
    """Restore a backup over the Vault file (atomic replace, creates a new backup).

    The current on-disk state is backed up first so the restore itself is
    revertible. ``backup_name`` must be an exact filename from ``list_backups``
    to avoid path traversal.
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

    backup = _backup_dir(store) / backup_name
    if backup.parent != _backup_dir(store) or not backup.is_file():
        raise VaultWorkbenchError("backup_name must be an exact existing backup filename")
    if not backup.name.startswith(f"{target.name}-") or not backup.name.endswith(".bak"):
        raise VaultWorkbenchError("backup_name does not belong to this Vault file")

    current = target.read_bytes()
    restored = backup.read_bytes()

    # Keep a revertible snapshot of the current state before restoring.
    directory = _backup_dir(store)
    directory.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
    safety = directory / f"{target.name}-{stamp}.pre-restore.bak"
    safety.write_bytes(current)

    fd, tmp_name = tempfile.mkstemp(dir=str(target.parent), prefix=".awx-", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(restored)
        os.replace(tmp_name, target)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(tmp_name)
        raise

    return {
        "schema_version": "v1",
        "relative_path": relative_path,
        "restored_from": backup_name,
        "source_hash": hashlib.sha256(restored).hexdigest(),
        "pre_restore_backup": str(safety),
    }
