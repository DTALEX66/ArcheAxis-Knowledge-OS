"""AXW-012A: RawAsset-first minimal store.

Contract: original bytes are persisted immutably (content-addressed by
SHA-256) BEFORE any conversion runs; a failed conversion must still retain the
original plus a durable failure record. Failure injection must never lose the
original.

The default storage root lives under the project's ignored `.hermes/`
runtime boundary; it never touches the source vault or a tracked path.
"""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from threading import Lock


class RawAssetStoreError(ValueError):
    """Raised on invalid input or an unrecoverable storage failure."""


_WRITE_LOCKS_GUARD = Lock()
_WRITE_LOCKS: dict[str, Lock] = {}


def _write_lock(digest: str) -> Lock:
    """Return the process-local lock for one immutable content address."""
    with _WRITE_LOCKS_GUARD:
        return _WRITE_LOCKS.setdefault(digest, Lock())


def _sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _default_root() -> Path:
    # Prefer HERMES_PROJECT_RUNTIME_ROOT if provided by the project data
    # wrapper; otherwise fall back to the repository .hermes/task-runtime.
    env_root = os.environ.get("HERMES_PROJECT_RUNTIME_ROOT")
    if env_root:
        return Path(env_root) / "raw-assets"
    # Repository root = <repo>/app/ingestion/raw_asset.py -> parents[2]
    repo_root = Path(__file__).resolve().parents[2]
    return repo_root / ".hermes" / "task-runtime" / "raw-assets"


@dataclass(frozen=True)
class RawAssetRecord:
    sha256: str
    size_bytes: int
    source_name: str
    mime_type: str = "application/octet-stream"
    retention_policy: str = "retained"
    save_state: str = "saved"
    converted: str | None = None
    error: str | None = None

    @property
    def original_sha(self) -> str:
        return self.sha256


class RawAssetStore:
    """Content-addressed immutable store for original source bytes."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = (root or _default_root()).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self._failures_dir = self.root / "_failures"
        self._failures_dir.mkdir(parents=True, exist_ok=True)
        # Sidecar metadata makes the archive inspectable without exposing a
        # storage path to the product UI. The original content remains the
        # source of truth; a missing/corrupt sidecar must never hide it.
        self._metadata_dir = self.root / "_metadata"
        self._metadata_dir.mkdir(parents=True, exist_ok=True)

    def _original_path(self, digest: str) -> Path:
        return self.root / digest

    def _failure_path(self, digest: str) -> Path:
        return self._failures_dir / f"{digest}.json"

    def _metadata_path(self, digest: str) -> Path:
        return self._metadata_dir / f"{digest}.json"

    def has(self, digest: str) -> bool:
        return self._original_path(digest).exists()

    def remove_original(self, digest: str) -> bool:
        """Delete a stored original by digest. Returns True if it existed and
        was removed. Used to clean up an orphaned file when an enclosing
        import transaction is rolled back after the byte write."""
        p = self._original_path(digest)
        if p.exists():
            p.unlink()
            return True
        return False

    def has_failure(self, digest: str) -> bool:
        return self._failure_path(digest).exists()

    def resolve(self, digest: str) -> Path:
        p = self._original_path(digest)
        if not p.exists():
            raise RawAssetStoreError(f"raw asset not present: {digest}")
        return p

    def store_original(
        self,
        blob: bytes,
        source_name: str,
        *,
        mime_type: str | None = None,
        retention_policy: str | None = None,
    ) -> RawAssetRecord:
        """Persist the original bytes immutably and return a record. Raises on
        empty input so empty content can never masquerade as a source asset.
        MIME and retention policy are optional; sane defaults are applied.
        """
        if not source_name.strip():
            raise RawAssetStoreError("source_name is required")
        if not blob:
            raise RawAssetStoreError("empty original bytes cannot be stored")
        digest = _sha256(blob)
        dest = self._original_path(digest)
        # Write through a sibling temporary file then atomically replace the
        # content-addressed destination. Two identical concurrent uploads must
        # never observe each other's partially-written bytes.
        with _write_lock(digest):
            if not dest.exists():
                temporary_path: Path | None = None
                try:
                    with tempfile.NamedTemporaryFile(
                        mode="wb", dir=self.root, prefix=f".{digest}.", delete=False
                    ) as temporary:
                        temporary.write(blob)
                        temporary_path = Path(temporary.name)
                    if _sha256(temporary_path.read_bytes()) != digest:
                        raise RawAssetStoreError("raw asset hash mismatch before publish")
                    os.replace(temporary_path, dest)
                    temporary_path = None
                finally:
                    if temporary_path is not None:
                        temporary_path.unlink(missing_ok=True)
            if _sha256(dest.read_bytes()) != digest:
                raise RawAssetStoreError("raw asset hash mismatch after publish")
        record = RawAssetRecord(
            sha256=digest,
            size_bytes=len(blob),
            source_name=source_name,
            mime_type=mime_type or "application/octet-stream",
            retention_policy=retention_policy or "retained",
            save_state="saved",
            converted=None,
        )
        metadata_path = self._metadata_path(digest)
        if not metadata_path.exists():
            metadata_path.write_text(
                json.dumps(
                    {
                        "sha256": record.sha256,
                        "size_bytes": record.size_bytes,
                        "source_name": record.source_name,
                        "mime_type": record.mime_type,
                        "retention_policy": record.retention_policy,
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                ),
                encoding="utf-8",
            )
        return record

    def list_records(self) -> list[RawAssetRecord]:
        """List retained originals without leaking their archive paths.

        This is intentionally a resilient read projection: historical assets
        created before sidecars are still shown with a neutral display name.
        A durable failure record surfaces its real, sanitised reason instead
        of a generic marker so the product UI can explain why an original
        needs attention.
        """
        records: list[RawAssetRecord] = []
        for asset in sorted(self.root.iterdir(), key=lambda item: item.name):
            digest = asset.name
            if (
                not asset.is_file()
                or len(digest) != 64
                or any(char not in "0123456789abcdef" for char in digest)
            ):
                continue
            metadata: dict[str, object] = {}
            try:
                candidate = json.loads(self._metadata_path(digest).read_text(encoding="utf-8"))
                if isinstance(candidate, dict):
                    metadata = candidate
            except (OSError, json.JSONDecodeError):
                pass
            source_name = metadata.get("source_name")
            mime_type = metadata.get("mime_type")
            retention_policy = metadata.get("retention_policy")
            records.append(
                RawAssetRecord(
                    sha256=digest,
                    size_bytes=asset.stat().st_size,
                    source_name=source_name if isinstance(source_name, str) and source_name else "未标注原件",
                    mime_type=mime_type if isinstance(mime_type, str) and mime_type else "application/octet-stream",
                    retention_policy=(
                        retention_policy
                        if isinstance(retention_policy, str) and retention_policy
                        else "retained"
                    ),
                    error=self._read_failure_reason(digest),
                )
            )
        return records

    def _read_failure_reason(self, digest: str) -> str | None:
        """Return the durable failure reason for one digest, if recorded."""
        failure = self._failure_path(digest)
        if not failure.exists():
            return None
        try:
            payload = json.loads(failure.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return "conversion failed"
        if not isinstance(payload, dict):
            return "conversion failed"
        reason = payload.get("error")
        return reason if isinstance(reason, str) and reason.strip() else "conversion failed"

    def _record_failure(self, digest: str, source_name: str, error: str) -> None:
        payload = {
            "sha256": digest,
            "source_name": source_name,
            "error": error,
            "original_retained": True,
        }
        fp = self._failure_path(digest)
        if not fp.exists():
            fp.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")


def preserve_then_convert(
    store: RawAssetStore,
    blob: bytes,
    source_name: str,
    convert: Callable[[bytes], str],
) -> RawAssetRecord:
    """Persist the original first, then convert. On any converter failure the
    original is retained and a durable failure record is written. Returns a
    record whose `converted` is None and `error` populated on failure."""
    original = store.store_original(blob, source_name)
    try:
        converted = convert(blob)
    except BaseException as exc:  # noqa: BLE001 — we must not lose the original
        store._record_failure(original.sha256, source_name, str(exc))
        return RawAssetRecord(
            sha256=original.sha256,
            size_bytes=original.size_bytes,
            source_name=source_name,
            converted=None,
            error=str(exc),
        )
    return RawAssetRecord(
        sha256=original.sha256,
        size_bytes=original.size_bytes,
        source_name=source_name,
        converted=converted,
    )
