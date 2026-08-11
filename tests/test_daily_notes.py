"""Tests for shared.daily_notes (time-based knowledge capture)."""

from __future__ import annotations

import shared.daily_notes as dn


def _patch_storage(monkeypatch) -> dict:
    """Replace module-level storage fns with in-memory fakes."""
    state = {"notes": {}, "inserted": []}

    def fake_select_one(table, sid):
        return state["notes"].get(sid)

    def fake_select_all(table, limit=500, order=""):
        rows = list(state["notes"].values())
        if order == "date DESC":
            rows.sort(key=lambda r: r["date"], reverse=True)
        return rows[:limit]

    def fake_insert(table, row):
        state["notes"][row["id"]] = row
        state["inserted"].append((table, row))

    monkeypatch.setattr(dn, "select_one", fake_select_one)
    monkeypatch.setattr(dn, "select_all", fake_select_all)
    monkeypatch.setattr(dn, "insert", fake_insert)
    return state


def test_get_daily_missing_returns_none(monkeypatch) -> None:
    _patch_storage(monkeypatch)
    assert dn.get_daily("2026-08-12") is None


def test_get_or_create_daily_creates(monkeypatch) -> None:
    state = _patch_storage(monkeypatch)
    note = dn.get_or_create_daily("2026-08-12")
    assert note["id"] == "2026-08-12"
    assert note["tags"] == ["daily-note"]
    assert "2026-08-12" in note["content"]
    assert state["inserted"][0][0] == "daily_notes"


def test_get_or_create_daily_returns_existing(monkeypatch) -> None:
    state = _patch_storage(monkeypatch)
    first = dn.get_or_create_daily("2026-08-12")
    state["inserted"].clear()
    second = dn.get_or_create_daily("2026-08-12")
    assert second is first
    assert state["inserted"] == []  # no second insert


def test_append_to_daily_adds_content(monkeypatch) -> None:
    _patch_storage(monkeypatch)
    note = dn.append_to_daily("learned something", day="2026-08-12", heading="Notes")
    assert "learned something" in note["content"]
    assert "## Notes" in note["content"]
    assert note["updated_at"]


def test_timeline_filters_by_cutoff(monkeypatch) -> None:
    state = _patch_storage(monkeypatch)
    # 3 days back + 10 days back (outside 7-day window)
    dn.get_or_create_daily("2026-08-10")
    dn.get_or_create_daily("2026-08-02")
    rows = dn.timeline(days=7)
    dates = [r["date"] for r in rows]
    assert "2026-08-10" in dates
    assert "2026-08-02" not in dates
    assert rows[0]["preview"] != ""
    assert rows[0]["tag_count"] == 1


def test_link_to_daily_adds_wikilink(monkeypatch) -> None:
    _patch_storage(monkeypatch)
    indexed = {}

    def fake_index_document_links(note_id, content):
        indexed[note_id] = content

    monkeypatch.setattr("shared.backlinks.index_document_links", fake_index_document_links)
    note = dn.link_to_daily("doc_123", day="2026-08-12", context="related")
    assert "[[doc_123]]" in note["content"]
    assert "related" in note["content"]
    assert "2026-08-12" in indexed  # backlink indexed by note id
