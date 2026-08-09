"""AXW-022A (backend): PDF content serving for the PDF.js reader.

The reader needs the original PDF bytes. This module serves them from the
RawAsset store by content hash — read-only, size-bounded, and content-addressed
so the reader never sees the storage path.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from app.ingestion.raw_asset import RawAssetStore


class PdfServeError(ValueError):
    """Raised when a PDF byte lookup or write is invalid."""


MAX_PDF_BYTES = 50 * 1024 * 1024  # 50 MB


@dataclass(frozen=True)
class PdfServingRoot:
    store: RawAssetStore


def build_pdf_serving_root(root: Path) -> PdfServingRoot:
    """Build a content-addressed PDF serving root backed by the RawAsset store."""
    return PdfServingRoot(store=RawAssetStore(root=root / "pdf"))


def _hash_sha256(blob: bytes) -> str:
    return "sha256:" + hashlib.sha256(blob).hexdigest()


def store_pdf_bytes(root: PdfServingRoot, blob: bytes) -> str:
    """Store PDF bytes content-addressed and return the content key. Empty or
    oversized input is rejected."""
    if not blob:
        raise PdfServeError("empty PDF bytes cannot be served")
    if len(blob) > MAX_PDF_BYTES:
        raise PdfServeError("PDF exceeds the serving size limit")
    digest = _hash_sha256(blob)
    root.store.store_original(blob, "pdf-bytes")
    return digest


def resolve_pdf_bytes(root: PdfServingRoot, content_key: str) -> bytes:
    """Resolve PDF bytes by content key. Content keys are sha256: prefixed;
    anything else is rejected (fail-closed)."""
    if not content_key.startswith("sha256:"):
        raise PdfServeError("pdf content key must be sha256: prefixed")
    digest = content_key[len("sha256:"):]
    if not root.store.has(digest):
        raise PdfServeError(f"pdf content not present: {content_key}")
    return root.store.resolve(digest).read_bytes()
