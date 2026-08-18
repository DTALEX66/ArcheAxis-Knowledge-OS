"""Tests for Anki/Zotero adapters + long-term memory (包 E / Mem0 absorption)."""
from __future__ import annotations

import pytest

from app.adapters.anki_zotero import AdapterError, parse_zotero_json, to_anki_csv
from app.memory.long_term import (
    LongTermMemoryError,
    add,
    forget,
    search,
    update,
)


# ── anki / zotero ─────────────────────────────────────────────────────

def test_anki_csv_roundtrip():
    csv_text = to_anki_csv([
        {"front": "什么是 BKT？", "back": "贝叶斯知识追踪", "tags": ["learning", "bkt"]},
        {"front": "Q2", "back": "A2", "tags": []},
    ])
    assert '"什么是 BKT？"' in csv_text
    assert "learning bkt" in csv_text
    assert csv_text.count("\n") == 2


def test_anki_csv_rejects_bad_cards():
    with pytest.raises(AdapterError):
        to_anki_csv([])
    with pytest.raises(AdapterError):
        to_anki_csv([{"front": "only front"}])


def test_zotero_parse():
    units = parse_zotero_json([
        {"itemType": "journalArticle", "title": "BKT 论文", "creators": [
            {"firstName": "A", "lastName": "Corporaal"}, {"firstName": "B", "lastName": "Heffernan"}],
         "date": "2016-05-01", "DOI": "10.1145/2883851.2883913", "abstractNote": "摘要"},
        {"itemType": "note", "title": ""},  # skipped (no title)
    ])
    assert len(units) == 1
    assert units[0]["creators"] == ["A Corporaal", "B Heffernan"]
    assert units[0]["year"] == "2016"
    assert units[0]["doi"] == "10.1145/2883851.2883913"


# ── long-term memory ──────────────────────────────────────────────────

def test_add_dedup(tmp_path):
    db = tmp_path / "ltm.sqlite"
    first = add(db, content="用户偏好深色主题", importance=0.8)
    second = add(db, content="用户偏好深色主题", importance=0.8)
    assert first == second


def test_search_ranks_relevant(tmp_path):
    db = tmp_path / "ltm2.sqlite"
    add(db, content="用户在上午做设计工作", importance=0.7)
    add(db, content="印刷规范要求嵌入字体", importance=0.7)
    hits = search(db, "字体", top_k=5)
    assert hits and "字体" in hits[0].content


def test_update_creates_new_version(tmp_path):
    db = tmp_path / "ltm3.sqlite"
    mid = add(db, content="v1 内容", importance=0.5)
    new_id = update(db, mid, content="v2 内容")
    assert new_id != mid
    assert search(db, "v2", top_k=5) and search(db, "v2", top_k=5)[0].content == "v2 内容"


def test_forget_soft_delete(tmp_path):
    db = tmp_path / "ltm4.sqlite"
    mid = add(db, content="要忘记的", importance=0.5)
    forget(db, mid)
    assert search(db, "忘记", top_k=5) == []


def test_validation(tmp_path):
    db = tmp_path / "ltm5.sqlite"
    with pytest.raises(LongTermMemoryError):
        add(db, content="", importance=0.5)
    with pytest.raises(LongTermMemoryError):
        add(db, content="x", importance=2.0)
    with pytest.raises(LongTermMemoryError):
        search(db, "x", top_k=0)
