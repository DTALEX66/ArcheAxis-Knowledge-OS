"""Tests for the graph index shadow candidate lifecycle (I-001).

Covers: build_graph_candidate, verify, activate, rollback, source drift,
restart readback, and fail-closed edge cases.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from shared.graph_index import (
    build_graph_candidate,
)
from shared.index_manifest import IndexManifest

_ENTITY_TABLE = "graph_entities"
_RELATION_TABLE = "graph_relations"


def _seed_graph(db_path: str, entities: list[dict], relations: list[dict]) -> None:
    """Insert initial graph data."""
    with sqlite3.connect(db_path) as conn:
        for e in entities:
            conn.execute(
                f"INSERT OR REPLACE INTO {_ENTITY_TABLE} "
                f"(id, entity_type, properties, graph_name) VALUES (?, ?, ?, ?)",
                (e["id"], e.get("entity_type", "node"),
                 e.get("properties", "{}"), e.get("graph_name", "default")),
            )
        for r in relations:
            conn.execute(
                f"INSERT OR REPLACE INTO {_RELATION_TABLE} "
                f"(id, source_id, target_id, relation_type, weight, graph_name) "
                f"VALUES (?, ?, ?, ?, ?, ?)",
                (r["id"], r["source_id"], r["target_id"],
                 r.get("relation_type", "linked"),
                 r.get("weight", 1.0), r.get("graph_name", "default")),
            )
        conn.commit()


def _create_graph_tables(db_path: str) -> None:
    """Create empty graph tables."""
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            f"CREATE TABLE IF NOT EXISTS {_ENTITY_TABLE} ("
            "id TEXT PRIMARY KEY, entity_type TEXT, properties TEXT, graph_name TEXT)"
        )
        conn.execute(
            f"CREATE TABLE IF NOT EXISTS {_RELATION_TABLE} ("
            "id TEXT PRIMARY KEY, source_id TEXT, target_id TEXT, "
            "relation_type TEXT, weight REAL, graph_name TEXT)"
        )
        conn.commit()


@pytest.fixture
def db_path(tmp_path: Path) -> str:
    path = tmp_path / "test_graph.sqlite"
    _create_graph_tables(str(path))
    return str(path)


class TestGraphIndexCandidate:
    def test_build_candidate_keeps_active_tables_untouched(
        self, db_path: str
    ) -> None:
        """Candidate creation does not modify active tables."""
        _seed_graph(db_path,
            entities=[{"id": "e1", "entity_type": "person"}],
            relations=[{"id": "r1", "source_id": "e1", "target_id": "e2",
                        "relation_type": "knows"}],
        )

        candidate = build_graph_candidate(db_path)
        try:
            assert candidate.entity_count == 1
            assert candidate.relation_count == 1
            assert candidate.entity_ids == ("e1",)

            # Active tables are unchanged
            with sqlite3.connect(db_path) as conn:
                assert conn.execute(
                    f"SELECT COUNT(*) FROM {_ENTITY_TABLE}"
                ).fetchone()[0] == 1
                assert conn.execute(
                    f"SELECT COUNT(*) FROM {_RELATION_TABLE}"
                ).fetchone()[0] == 1
        finally:
            candidate.discard()

    def test_verify_succeeds_on_intact_candidate(
        self, db_path: str
    ) -> None:
        """verify() returns True on a valid candidate."""
        _seed_graph(db_path,
            entities=[{"id": "v1"}, {"id": "v2"}],
            relations=[{"id": "vr1", "source_id": "v1", "target_id": "v2"}],
        )
        candidate = build_graph_candidate(db_path)
        try:
            assert candidate.verify() is True
        finally:
            candidate.discard()

    def test_verify_fails_on_tampered_candidate(
        self, db_path: str
    ) -> None:
        """verify() fails when candidate is tampered with."""
        _seed_graph(db_path,
            entities=[{"id": "t1"}],
            relations=[],
        )
        candidate = build_graph_candidate(db_path)
        try:
            with sqlite3.connect(db_path) as conn:
                conn.execute(
                    f"DELETE FROM {candidate.entity_table} WHERE id='t1'"
                )
                conn.commit()

            with pytest.raises(RuntimeError, match="graph candidate verification failed"):
                candidate.verify()

            # Active tables untouched
            with sqlite3.connect(db_path) as conn:
                assert conn.execute(
                    f"SELECT COUNT(*) FROM {_ENTITY_TABLE}"
                ).fetchone()[0] == 1
        finally:
            candidate.discard()

    def test_activate_and_rollback_restores(
        self, db_path: str
    ) -> None:
        """Build candidate, activate swaps identical data, then add new data, then rollback removes it."""
        # Seed with entity a1 only
        _seed_graph(db_path,
            entities=[{"id": "a1", "entity_type": "original"}],
            relations=[{"id": "ar1", "source_id": "a1", "target_id": "a2",
                        "relation_type": "original_edge"}],
        )

        # Build candidate from this data (candidate == active)
        candidate = build_graph_candidate(db_path)

        try:
            # Activate immediately (no drift) — active replaced with candidate (same data)
            rollback = candidate.activate()

            with sqlite3.connect(db_path) as conn:
                assert conn.execute(
                    f"SELECT COUNT(*) FROM {_ENTITY_TABLE}"
                ).fetchone()[0] == 1

            # Now add new data to active (drifts from what rollback captured)
            _seed_graph(db_path,
                entities=[{"id": "b1", "entity_type": "new"}],
                relations=[{"id": "br1", "source_id": "b1", "target_id": "b2",
                            "relation_type": "new_edge"}],
            )

            with sqlite3.connect(db_path) as conn:
                assert conn.execute(
                    f"SELECT COUNT(*) FROM {_ENTITY_TABLE}"
                ).fetchone()[0] == 2

            # Rollback restores to what active was at activation time (a1 only)
            rollback.rollback()
            with sqlite3.connect(db_path) as conn:
                entity_types = {
                    r[0] for r in conn.execute(
                        f"SELECT entity_type FROM {_ENTITY_TABLE}"
                    ).fetchall()
                }
                assert entity_types == {"original"}
                assert conn.execute(
                    f"SELECT COUNT(*) FROM {_ENTITY_TABLE}"
                ).fetchone()[0] == 1
                assert conn.execute(
                    f"SELECT COUNT(*) FROM {_RELATION_TABLE}"
                ).fetchone()[0] == 1

            # Second rollback fails (sources cleaned up)
            with pytest.raises(ValueError, match="graph rollback source missing"):
                rollback.rollback()
        finally:
            candidate.discard()

    def test_activate_rejects_source_drift(
        self, db_path: str
    ) -> None:
        """activate() rejects candidate when canonical source has drifted after candidate was built."""
        _seed_graph(db_path,
            entities=[{"id": "d1"}, {"id": "d2"}],
            relations=[{"id": "dr1", "source_id": "d1", "target_id": "d2"}],
        )
        candidate = build_graph_candidate(db_path)
        try:
            # Add a new entity to active tables (drift — not in candidate)
            _seed_graph(db_path,
                entities=[{"id": "d3"}],
                relations=[],
            )

            with pytest.raises(RuntimeError, match="graph candidate verification failed"):
                candidate.activate()

            # Active tables unchanged (still has all 3 entities)
            with sqlite3.connect(db_path) as conn:
                assert conn.execute(
                    f"SELECT COUNT(*) FROM {_ENTITY_TABLE}"
                ).fetchone()[0] == 3
        finally:
            candidate.discard()

    def test_empty_graph_candidate(
        self, db_path: str
    ) -> None:
        """An empty graph can still produce a valid candidate."""
        candidate = build_graph_candidate(db_path)
        try:
            assert candidate.entity_count == 0
            assert candidate.relation_count == 0
            assert candidate.verify() is True

            rollback = candidate.activate()
            rollback.rollback()
        finally:
            candidate.discard()

    def test_discard_does_not_touch_active(
        self, db_path: str
    ) -> None:
        """discard() removes only shadow tables."""
        _seed_graph(db_path,
            entities=[{"id": "keep"}],
            relations=[],
        )
        candidate = build_graph_candidate(db_path)
        candidate.discard()

        with sqlite3.connect(db_path) as conn:
            # Candidate tables gone
            assert conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
                (candidate.entity_table,),
            ).fetchone() is None
            # Active tables intact
            assert conn.execute(
                f"SELECT 1 FROM sqlite_master WHERE type='table' AND name='{_ENTITY_TABLE}'"
            ).fetchone() is not None
            assert conn.execute(
                f"SELECT COUNT(*) FROM {_ENTITY_TABLE}"
            ).fetchone()[0] == 1


class TestGraphIndexManifestIntegration:
    """Integration: graph index lifecycle + manifest restart readback."""

    def test_graph_manifest_verify_after_activate_rollback(
        self, db_path: str
    ) -> None:
        """Graph activate/rollback recorded in manifest and readable at restart."""
        manifest = IndexManifest(db_path)
        manifest.ensure_table()

        # Seed 2 entities + 1 relation
        _seed_graph(db_path,
            entities=[{"id": "m1"}, {"id": "m2"}],
            relations=[{"id": "mr1", "source_id": "m1", "target_id": "m2"}],
        )

        fp_initial = manifest.compute_fingerprint("graph")
        manifest.record("graph", "graph", sha256=fp_initial["sha256"],
                         row_count=fp_initial["row_count"])

        # Build candidate from initial data
        candidate = build_graph_candidate(db_path)
        try:
            # Activate (no drift)
            rollback = candidate.activate()

            fp_after_activate = manifest.compute_fingerprint("graph")
            manifest.record("graph", "graph", sha256=fp_after_activate["sha256"],
                             row_count=fp_after_activate["row_count"])

            # Verify restart readback
            result = manifest.verify_restart_readback("graph")
            assert result["match"] is True
            assert result["row_count"] == fp_initial["row_count"]

            # Add data after activation (drift from rollback snapshot)
            _seed_graph(db_path,
                entities=[{"id": "m3"}],
                relations=[],
            )

            # Rollback restores pre-activation state (m1, m2 + mr1 only)
            rollback.rollback()
            fp_restored = manifest.compute_fingerprint("graph")
            manifest.record("graph", "graph", sha256=fp_restored["sha256"],
                             row_count=fp_restored["row_count"])

            result = manifest.verify_restart_readback("graph")
            assert result["match"] is True
            assert result["row_count"] == fp_initial["row_count"]  # back to initial
        finally:
            candidate.discard()

    def test_graph_manifest_detects_drift(
        self, db_path: str
    ) -> None:
        """Manifest detects graph drift after activation if data changes."""
        manifest = IndexManifest(db_path)
        manifest.ensure_table()

        _seed_graph(db_path,
            entities=[{"id": "gd1"}],
            relations=[],
        )

        candidate = build_graph_candidate(db_path)
        try:
            candidate.activate()
            fp = manifest.compute_fingerprint("graph")
            manifest.record("graph", "graph", sha256=fp["sha256"], row_count=1)

            # Manually add an entity (simulates concurrent write)
            with sqlite3.connect(db_path) as conn:
                conn.execute(
                    f"INSERT INTO {_ENTITY_TABLE}(id, entity_type, properties, graph_name) "
                    f"VALUES ('sneaky', 'node', '{{}}', 'default')"
                )
                conn.commit()

            result = manifest.verify_restart_readback("graph")
            assert result["match"] is False
        finally:
            candidate.discard()
