"""Tests for the FTS5 inactive candidate rebuild boundary."""

from __future__ import annotations

import pytest

from knowledge_base.search import keyword_search
from shared import storage


def test_build_fts_candidate_keeps_active_index_untouched() -> None:
    document = {
        "id": "fts_candidate_doc",
        "title": "Candidate source",
        "content": "migration boundary verification",
        "source": "test",
    }
    storage.insert("kb_documents", document)
    storage.fts5_sync("kb_documents", document)

    candidate = storage.build_fts_candidate("kb_documents")
    try:
        assert candidate.active_table == "kb_documents_fts"
        assert candidate.table_name != candidate.active_table
        assert candidate.object_ids == (document["id"],)
        assert candidate.count == 1
        assert candidate.verify() is True
        assert any(item["id"] == document["id"] for item in keyword_search("migration boundary"))
    finally:
        candidate.discard()
        with storage._conn() as connection:
            connection.execute("DELETE FROM kb_documents_fts WHERE id=?", (document["id"],))
            connection.execute("DELETE FROM kb_documents WHERE id=?", (document["id"],))
            connection.commit()


def test_fts_candidate_verification_fails_closed_without_touching_active_index() -> None:
    document = {
        "id": "fts_candidate_tampered",
        "title": "Candidate source",
        "content": "tamper detection proof",
        "source": "test",
    }
    storage.insert("kb_documents", document)
    storage.fts5_sync("kb_documents", document)
    candidate = storage.build_fts_candidate("kb_documents")
    try:
        with storage._conn() as connection:
            connection.execute(f'DELETE FROM "{candidate.table_name}" WHERE id=?', (document["id"],))
            connection.commit()

        with pytest.raises(RuntimeError, match="FTS candidate verification failed"):
            candidate.verify()
        assert any(item["id"] == document["id"] for item in keyword_search("tamper detection"))
    finally:
        candidate.discard()
        with storage._conn() as connection:
            connection.execute("DELETE FROM kb_documents_fts WHERE id=?", (document["id"],))
            connection.execute("DELETE FROM kb_documents WHERE id=?", (document["id"],))
            connection.commit()


def test_build_fts_candidate_rejects_unsupported_source_table() -> None:
    with pytest.raises(ValueError, match="unsupported FTS source table"):
        storage.build_fts_candidate("kb_taskpacks")


def test_activate_fts_candidate_and_rollback_restore_active_index() -> None:
    original = {
        "id": "fts_switch_original",
        "title": "Original active source",
        "content": "rollback boundary original",
        "source": "test",
    }
    added = {
        "id": "fts_switch_added",
        "title": "Added candidate source",
        "content": "shadow candidate switch",
        "source": "test",
    }
    storage.insert("kb_documents", original)
    storage.fts5_sync("kb_documents", original)
    storage.insert("kb_documents", added)
    candidate = storage.build_fts_candidate("kb_documents")
    try:
        rollback = candidate.activate()
        with storage._conn() as connection:
            active_ids = {
                row[0]
                for row in connection.execute(
                    "SELECT id FROM kb_documents_fts WHERE kb_documents_fts MATCH ?", ("shadow",)
                )
            }
        assert active_ids == {added["id"]}
        rollback.rollback()
        with storage._conn() as connection:
            active_ids = {
                row[0]
                for row in connection.execute(
                    "SELECT id FROM kb_documents_fts WHERE kb_documents_fts MATCH ?", ("rollback",)
                )
            }
            assert active_ids == {original["id"]}
            assert connection.execute(
                "SELECT COUNT(*) FROM kb_documents_fts WHERE kb_documents_fts MATCH ?", ("shadow",)
            ).fetchone()[0] == 0
        with pytest.raises(ValueError, match="FTS rollback source missing"):
            rollback.rollback()
    finally:
        with storage._conn() as connection:
            connection.execute("DELETE FROM kb_documents_fts WHERE id IN (?, ?)", (original["id"], added["id"]))
            connection.execute("DELETE FROM kb_documents WHERE id IN (?, ?)", (original["id"], added["id"]))
            connection.commit()


def test_fts_activation_rejects_source_drift_without_touching_active_index() -> None:
    original = {
        "id": "fts_source_drift_original",
        "title": "Original source",
        "content": "source drift original",
        "source": "test",
    }
    changed = {
        "id": "fts_source_drift_changed",
        "title": "Changed source",
        "content": "source drift changed",
        "source": "test",
    }
    storage.insert("kb_documents", original)
    storage.fts5_sync("kb_documents", original)
    candidate = storage.build_fts_candidate("kb_documents")
    try:
        storage.insert("kb_documents", changed)
        with pytest.raises(RuntimeError, match="FTS candidate verification failed"):
            candidate.activate()
        with storage._conn() as connection:
            assert connection.execute(
                "SELECT COUNT(*) FROM kb_documents_fts WHERE kb_documents_fts MATCH ?",
                ("source drift original",),
            ).fetchone()[0] == 1
            assert connection.execute(
                "SELECT COUNT(*) FROM kb_documents_fts WHERE kb_documents_fts MATCH ?",
                ("source drift changed",),
            ).fetchone()[0] == 0
    finally:
        candidate.discard()
        with storage._conn() as connection:
            connection.execute("DELETE FROM kb_documents_fts WHERE id IN (?, ?)", (original["id"], changed["id"]))
            connection.execute("DELETE FROM kb_documents WHERE id IN (?, ?)", (original["id"], changed["id"]))
            connection.commit()
