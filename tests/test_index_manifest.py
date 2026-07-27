"""Tests for the unified index version manifest (I-001)."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from shared.index_manifest import IndexManifest


@pytest.fixture
def manifest(tmp_path: Path) -> IndexManifest:
    db = tmp_path / "test_manifest.sqlite"
    m = IndexManifest(str(db))
    m.ensure_table()
    return m


class TestIndexManifest:
    def test_table_creation(self, manifest: IndexManifest) -> None:
        """Manifest table is created on first use."""
        with manifest._conn() as conn:
            row = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='index_manifest'"
            ).fetchone()
            assert row is not None

    def test_record_and_get(self, manifest: IndexManifest) -> None:
        """Record an entry and retrieve it."""
        entry = manifest.record("fts", "kb_documents_fts", sha256="abc123", row_count=5)
        assert entry.kind == "fts"
        assert entry.name == "kb_documents_fts"
        assert entry.sha256 == "abc123"
        assert entry.row_count == 5
        assert entry.version == 1

        retrieved = manifest.get("fts", "kb_documents_fts")
        assert retrieved is not None
        assert retrieved.sha256 == "abc123"
        assert retrieved.row_count == 5

    def test_get_nonexistent_returns_none(self, manifest: IndexManifest) -> None:
        """Getting a non-existent entry returns None."""
        assert manifest.get("vector", "nonexistent") is None

    def test_version_increments(self, manifest: IndexManifest) -> None:
        """Each record() call for the same key increments version."""
        e1 = manifest.record("fts", "test", sha256="v1", row_count=1)
        e2 = manifest.record("fts", "test", sha256="v2", row_count=2)
        assert e1.version == 1
        assert e2.version == 2
        assert manifest.get("fts", "test").version == 2

    def test_list_entries(self, manifest: IndexManifest) -> None:
        """List all recorded entries."""
        manifest.record("fts", "a", sha256="s1", row_count=5)
        manifest.record("vector", "b", sha256="s2", row_count=10)
        entries = manifest.list_entries()
        assert len(entries) == 2
        kinds = [e.kind for e in entries]
        assert "fts" in kinds
        assert "vector" in kinds

    def test_delete(self, manifest: IndexManifest) -> None:
        """Delete removes the entry."""
        manifest.record("fts", "del", sha256="x", row_count=0)
        assert manifest.get("fts", "del") is not None
        assert manifest.delete("fts", "del") is True
        assert manifest.get("fts", "del") is None
        assert manifest.delete("fts", "del") is False

    def test_rejects_unsupported_kind(self, manifest: IndexManifest) -> None:
        """record() rejects an unsupported index kind."""
        with pytest.raises(ValueError, match="unsupported index kind"):
            manifest.record("unsupported", "x", sha256="s", row_count=0)

    def test_compute_fingerprint_rejects_unsupported_kind(
        self, manifest: IndexManifest
    ) -> None:
        """compute_fingerprint rejects unsupported kind."""
        with pytest.raises(ValueError, match="unsupported index kind"):
            manifest.compute_fingerprint("unknown")

    def test_compute_fingerprint_rejects_missing_table(
        self, manifest: IndexManifest
    ) -> None:
        """compute_fingerprint raises ValueError for a missing table."""
        with pytest.raises(ValueError, match="table not found"):
            manifest.compute_fingerprint("fts", "nonexistent_table")

    def test_verify_restart_readback_no_entry(
        self, manifest: IndexManifest
    ) -> None:
        """Restart readback reports no_entry when no manifest exists."""
        result = manifest.verify_restart_readback("vector", "vec_test")
        assert result["match"] is False
        assert result["reason"] == "no_manifest_entry"

    def test_verify_restart_readback_match(
        self, manifest: IndexManifest
    ) -> None:
        """Create a table, record its fingerprint, verify match."""
        db = manifest.db_path
        with sqlite3.connect(db) as conn:
            conn.execute("CREATE TABLE test_table (id TEXT PRIMARY KEY, value TEXT)")
            conn.execute("INSERT INTO test_table VALUES ('a', 'hello')")
            conn.commit()

        fp = manifest.compute_fingerprint("evidence", "test_table")
        manifest.record("evidence", "test_table", sha256=fp["sha256"], row_count=fp["row_count"])

        result = manifest.verify_restart_readback("evidence", "test_table")
        assert result["match"] is True
        assert result["row_count"] == 1

    def test_verify_restart_readback_drift(
        self, manifest: IndexManifest
    ) -> None:
        """After data changes, restart readback detects drift."""
        db = manifest.db_path
        with sqlite3.connect(db) as conn:
            conn.execute("CREATE TABLE drift (id TEXT PRIMARY KEY)")
            conn.execute("INSERT INTO drift VALUES ('orig')")
            conn.commit()

        fp = manifest.compute_fingerprint("evidence", "drift")
        manifest.record("evidence", "drift", sha256=fp["sha256"], row_count=1)

        # Change data
        with sqlite3.connect(db) as conn:
            conn.execute("DELETE FROM drift")
            conn.execute("INSERT INTO drift VALUES ('changed')")
            conn.commit()

        result = manifest.verify_restart_readback("evidence", "drift")
        assert result["match"] is False

    def test_fingerprint_determinism(self, manifest: IndexManifest) -> None:
        """Same table content produces same fingerprint."""
        db = manifest.db_path
        with sqlite3.connect(db) as conn:
            conn.execute("CREATE TABLE det (k TEXT PRIMARY KEY)")
            conn.execute("INSERT INTO det VALUES ('x')")
            conn.commit()

        fp1 = manifest.compute_fingerprint("evidence", "det")
        fp2 = manifest.compute_fingerprint("evidence", "det")
        assert fp1["sha256"] == fp2["sha256"]

    def test_metadata_json(self, manifest: IndexManifest) -> None:
        """record() stores and retrieves metadata."""
        meta = {"engine": "fts5", "tokenizer": "porter"}
        entry = manifest.record(
            "fts", "test_meta", sha256="s", row_count=0, metadata=meta
        )
        assert json.loads(entry.metadata_json) == meta

        retrieved = manifest.get("fts", "test_meta")
        assert json.loads(retrieved.metadata_json) == meta
