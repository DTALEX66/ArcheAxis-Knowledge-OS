"""AXW-022A (backend): PDF content serving for the reader.

The PDF.js reader needs the original PDF bytes; this module serves them from
the RawAsset store by content hash. It is read-only, size-bounded, and never
exposes the full storage path (only the content-addressed bytes).
"""
from __future__ import annotations

import pytest

from app.evidence.pdf_serve import (
    PdfServeError,
    build_pdf_serving_root,
    resolve_pdf_bytes,
    store_pdf_bytes,
)


def test_store_and_resolve_pdf_bytes(tmp_path) -> None:
    root = build_pdf_serving_root(tmp_path)
    blob = b"%PDF-1.4\n" + b"x" * 100
    sha = store_pdf_bytes(root, blob)
    assert sha
    resolved = resolve_pdf_bytes(root, sha)
    assert resolved == blob


def test_resolve_missing_pdf_raises(tmp_path) -> None:
    root = build_pdf_serving_root(tmp_path)
    with pytest.raises(PdfServeError, match="not present"):
        resolve_pdf_bytes(root, "sha256:" + "a" * 64)


def test_serving_is_content_addressed_not_path_based(tmp_path) -> None:
    """The serving key is the content hash, not a filesystem path, so the
    reader never sees the storage location."""
    root = build_pdf_serving_root(tmp_path)
    blob = b"%PDF-1.4\n" + b"y" * 50
    sha = store_pdf_bytes(root, blob)
    assert sha.startswith("sha256:")
    assert sha != "0" * 64
