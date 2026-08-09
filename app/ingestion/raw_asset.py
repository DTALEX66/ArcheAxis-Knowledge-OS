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
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path


class RawAssetStoreError(ValueError):
    """Raised on invalid input or an unrecoverable storage failure."""


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

    def _original_path(self, digest: str) -> Path:
        return self.root / digest

    def _failure_path(self, digest: str) -> Path:
        return self._failures_dir / f"{digest}.json"

    def has(self, digest: str) -> bool:
        return self._original_path(digest).exists()

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
        # Immutable write: only write when the content-addressed file is absent,
        # and verify the hash after writing (no silent partial/corrupt writes).
        if not dest.exists():
            dest.write_bytes(blob)
            if _sha256(dest.read_bytes()) != digest:
                raise RawAssetStoreError("raw asset hash mismatch after write")
        return RawAssetRecord(
            sha256=digest,
            size_bytes=len(blob),
            source_name=source_name,
            mime_type=mime_type or "application/octet-stream",
            retention_policy=retention_policy or "retained",
            save_state="saved",
            converted=None,
        )

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
