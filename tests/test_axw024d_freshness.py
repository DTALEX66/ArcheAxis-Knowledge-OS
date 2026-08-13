"""AXW-024D: freshness / scope / revoke projection tests.

Verifies append-only event semantics, freshness status resolution, scope
filtering, expiry, and the fail-closed projection (unknown governance is
excluded from retrieval).
"""

from __future__ import annotations

from app.knowledge.freshness import (
    FreshnessError,
    freshness_status,
    project_active,
    record_event,
)


def _mkdb(tmp_path) -> str:
    return str(tmp_path / "freshness.sqlite")


def test_activate_then_revoke_status_resolution(tmp_path) -> None:
    db = _mkdb(tmp_path)
    record_event(db, unit_id="u1", event_type="activate", actor="sys")
    assert freshness_status(db, unit_id="u1")["status"] == "active"
    record_event(db, unit_id="u1", event_type="revoke", actor="human", note="wrong content")
    status = freshness_status(db, unit_id="u1")
    assert status["status"] == "revoked"
    # Revalidation restores active status (history preserved).
    record_event(db, unit_id="u1", event_type="revalidate", actor="human2")
    assert freshness_status(db, unit_id="u1")["status"] == "active"
    assert len(record_event(db, unit_id="u1", event_type="revoke", actor="h").event_id) > 0


def test_supersede_is_terminal_until_revalidation(tmp_path) -> None:
    db = _mkdb(tmp_path)
    record_event(db, unit_id="u1", event_type="activate", actor="sys")
    record_event(db, unit_id="u1", event_type="supersede", actor="human", note="replaced by u2")
    assert freshness_status(db, unit_id="u1")["status"] == "superseded"


def test_expiry_via_effective_until(tmp_path) -> None:
    db = _mkdb(tmp_path)
    past = "2020-01-01T00:00:00+00:00"
    record_event(db, unit_id="u1", event_type="activate", actor="sys", effective_until=past)
    assert freshness_status(db, unit_id="u1")["status"] == "expired"
    future = "2999-01-01T00:00:00+00:00"
    record_event(db, unit_id="u2", event_type="activate", actor="sys", effective_until=future)
    assert freshness_status(db, unit_id="u2")["status"] == "active"


def test_project_active_filters_unknown_revoked_expired_scope(tmp_path) -> None:
    db = _mkdb(tmp_path)
    record_event(db, unit_id="ok", event_type="activate", actor="sys", scope="math")
    record_event(db, unit_id="revoked", event_type="activate", actor="sys")
    record_event(db, unit_id="revoked", event_type="revoke", actor="human")
    record_event(db, unit_id="expired", event_type="activate", actor="sys", effective_until="2020-01-01T00:00:00+00:00")
    record_event(db, unit_id="scoped", event_type="activate", actor="sys", scope="history")

    # Fail-closed: unknown governance (never activated) is excluded.
    projected = project_active(db, unit_ids=["ok", "revoked", "expired", "scoped", "ghost"], scope=None)
    assert projected == ["ok", "scoped"]

    # Scope-restricted projection only returns the matching unit.
    scoped = project_active(db, unit_ids=["ok", "scoped", "revoked"], scope="history")
    assert scoped == ["scoped"]

    math = project_active(db, unit_ids=["ok", "scoped"], scope="math")
    assert math == ["ok"]


def test_invalid_event_fails_closed(tmp_path) -> None:
    db = _mkdb(tmp_path)
    try:
        record_event(db, unit_id="u1", event_type="banana", actor="a")
        raise AssertionError("expected FreshnessError")
    except FreshnessError as exc:
        assert "invalid event type" in str(exc)
    try:
        record_event(db, unit_id="", event_type="activate", actor="a")
        raise AssertionError("expected FreshnessError")
    except FreshnessError as exc:
        assert "unit_id" in str(exc)
