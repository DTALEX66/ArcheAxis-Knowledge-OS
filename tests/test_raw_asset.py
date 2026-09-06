"""AXW-012A: RawAsset-first minimal implementation tests.

Contract: the original bytes must be stored immutably (content-addressed by
SHA-256) BEFORE any conversion runs; a failed conversion must still retain the
original and a failure record; failure injection must prove no original loss.
"""
from __future__ import annotations

import hashlib

import pytest

from app.ingestion.raw_asset import (
    RawAssetStore,
    RawAssetStoreError,
    preserve_then_convert,
)


def _sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def test_store_original_immutably_and_hash(tmp_path) -> None:
    store = RawAssetStore(root=tmp_path / "raw")
    blob = b"# original markdown\nfirst line"
    record = store.store_original(blob, source_name="a.md")

    assert record.sha256 == _sha256(blob)
    assert record.size_bytes == len(blob)
    # Content-addressed path is derived from the digest and exists on disk.
    stored = store.resolve(record.sha256)
    assert stored.exists()
    assert stored.read_bytes() == blob
    assert not record.converted


def test_original_is_stored_before_conversion(tmp_path, monkeypatch) -> None:
    """The original must be persisted before the converter is invoked."""
    store = RawAssetStore(root=tmp_path / "raw")
    blob = b"# converted later\nbody"
    seen = {"original_sha": None, "stored_before": False}

    def fake_convert(raw: bytes) -> str:
        seen["stored_before"] = store.has(seen["original_sha"])
        return "# converted"

    seen["original_sha"] = _sha256(blob)
    result = preserve_then_convert(store, blob, "b.md", fake_convert)
    assert result.converted == "# converted"
    assert seen["stored_before"] is True
    assert store.has(_sha256(blob))


def test_failed_conversion_keeps_original_and_records_failure(tmp_path) -> None:
    store = RawAssetStore(root=tmp_path / "raw")
    blob = b"# fragile content"

    def broken_convert(raw: bytes) -> str:
        raise RuntimeError("converter exploded")

    result = preserve_then_convert(store, blob, "c.md", broken_convert)
    assert result.converted is None
    assert result.error == "converter exploded"
    assert result.original_sha == _sha256(blob)
    # Original must still be on disk after the failure.
    assert store.has(_sha256(blob))
    # Failure must be recorded.
    assert store.has_failure(result.original_sha)


def test_failure_injection_proves_no_original_loss(tmp_path) -> None:
    """Inject failure at multiple points; the original must survive every one."""
    store = RawAssetStore(root=tmp_path / "raw")
    blob = b"\x00\x01\x02 binary-ish original"

    for attempt in range(5):
        if attempt == 0:
            conv = lambda raw: (_ for _ in ()).throw(ValueError("boom A"))  # noqa: E731
        elif attempt == 1:
            def conv1(raw):
                raise OSError("disk hiccup")
            conv = conv1
        elif attempt == 2:
            def conv2(raw):
                raise RawAssetStoreError("store rejected")
            conv = conv2
        elif attempt == 3:
            def conv3(raw):
                raise KeyboardInterrupt("interrupted")
            conv = conv3
        else:
            def conv4(raw):
                raise Exception("generic")  # noqa: BLE001
            conv = conv4

        result = preserve_then_convert(store, blob, f"f{attempt}.bin", conv)
        assert result.converted is None
        assert store.has(_sha256(blob)), f"original lost on attempt {attempt}"
        assert store.has_failure(result.original_sha)


def test_store_rejects_empty_source_and_empty_blob(tmp_path) -> None:
    store = RawAssetStore(root=tmp_path / "raw")
    with pytest.raises(RawAssetStoreError):
        store.store_original(b"", source_name="x.md")
    with pytest.raises(RawAssetStoreError):
        store.store_original(b"data", source_name="")


def test_store_defaults_to_project_ignored_runtime_root() -> None:
    store = RawAssetStore()
    # Default root must live under the project's ignored runtime directory,
    # never under the user home or a repo-tracked path.
    root = str(store.root).replace("\\", "/")
    assert "/.project-local/" in root
    assert root.endswith("/raw-assets")


def test_store_captures_full_asset_contract(tmp_path) -> None:
    """AXW-020A: the stored record must capture source, MIME, size, save
    state and retention policy so the RawAsset contract is complete and stable.
    """
    store = RawAssetStore(root=tmp_path / "raw")
    blob = b"%PDF-1.4 fake pdf bytes"
    record = store.store_original(
        blob,
        source_name="a.pdf",
        mime_type="application/pdf",
        retention_policy="permanent",
    )
    assert record.sha256 == _sha256(blob)
    assert record.size_bytes == len(blob)
    assert record.source_name == "a.pdf"
    assert record.mime_type == "application/pdf"
    assert record.retention_policy == "permanent"
    assert record.save_state == "saved"
    assert store.resolve(record.sha256).exists()


def test_store_defaults_mime_and_retention(tmp_path) -> None:
    """AXW-020A: MIME and retention must have sane defaults when omitted."""
    store = RawAssetStore(root=tmp_path / "raw")
    record = store.store_original(b"hello", source_name="note.txt")
    assert record.mime_type == "application/octet-stream"
    assert record.retention_policy == "retained"
