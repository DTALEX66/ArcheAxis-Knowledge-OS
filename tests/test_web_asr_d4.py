"""Tests for web capture, ASR adapter, D4 memory completions."""
from __future__ import annotations

import base64

import pytest

from app.ingestion.web import WebCaptureError, capture_web, ingest_web
from app.ingestion.asr_adapter import AsrError, resolve_model_dir, transcribe
from app.memory.long_term import add_from_conversation, classify_kind, LongTermMemoryError
from app.memory.memory_layers import MemoryLayer, WORKING_MEMORY_CAPACITY, check_memory_pressure, store


class _FakeResponse:
    def __init__(self, body: bytes, status: int = 200, headers=None):
        self.body = body
        self.status = status
        self.headers = headers or {"Content-Type": "text/html; charset=utf-8"}


# ── web capture ──────────────────────────────────────────────────────

def test_capture_rejects_bad_scheme():
    with pytest.raises(WebCaptureError, match="scheme"):
        capture_web("ftp://example.com/x")


def test_capture_requires_url():
    with pytest.raises(WebCaptureError, match="url is required"):
        capture_web("")


def test_capture_raw_first_with_injected_fetcher(monkeypatch):
    raw = "<html><body>测试内容</body></html>".encode("utf-8")

    def fake_fetch(url, policy):
        return _FakeResponse(raw)

    # patch convert_url to avoid network
    monkeypatch.setattr("app.ingestion.multi_format.convert_url",
                        lambda url: ("提取出的文本", "trafilatura"))
    result = capture_web("https://example.com/page", raw_fetcher=fake_fetch)
    assert result["receipt"]["raw_bytes"] == len(raw)
    assert result["receipt"]["text_chars"] == len("提取出的文本")
    assert result["receipt"]["engine"] == "trafilatura"
    assert result["receipt"]["raw_hash"]
    assert base64.b64decode(result["raw"]) == raw
    assert result["text"] == "提取出的文本"


def test_capture_blocks_content_type(monkeypatch):
    def fake_fetch(url, policy):
        return _FakeResponse(b"x", headers={"Content-Type": "image/png"})
    with pytest.raises(WebCaptureError, match="content type"):
        capture_web("https://example.com/f", raw_fetcher=fake_fetch)


def test_ingest_web_keeps_compat_signature():
    assert callable(ingest_web)


# ── asr adapter ──────────────────────────────────────────────────────

def test_asr_fail_closed_missing_model(monkeypatch, tmp_path):
    monkeypatch.setenv("ARCHEAXIS_ASR_MODEL_DIR", str(tmp_path / "absent"))
    audio = tmp_path / "sample.mp3"
    audio.write_bytes(b"fake audio")
    with pytest.raises(AsrError, match="model missing"):
        transcribe(str(audio))


def test_asr_missing_file():
    with pytest.raises(AsrError, match="not found"):
        transcribe("C:/definitely/missing.mp3")


def test_resolve_model_dir_default():
    assert resolve_model_dir().name == "whisper"


# ── D4: long_term conversation + memory layers pressure ─────────────

def test_classify_kinds():
    assert classify_kind("我偏好深色主题") == "preference"
    assert classify_kind("部署步骤：先构建再上传") == "procedure"
    assert classify_kind("WORK-LAB 项目状态") == "project"
    assert classify_kind("普通事实陈述") == "fact"


def test_add_from_conversation(tmp_path):
    db = tmp_path / "c.sqlite"
    ids = add_from_conversation(db, [
        {"role": "user", "content": "我偏好双屏工作"},
        {"role": "assistant", "content": "印前步骤：先嵌入字体再导出"},
    ])
    assert len(ids) == 2
    with pytest.raises(LongTermMemoryError):
        add_from_conversation(db, [])


def test_memory_pressure_triggers_distill(tmp_path):
    db = tmp_path / "p.sqlite"
    for i in range(WORKING_MEMORY_CAPACITY):
        store(db, content=f"w-{i}", layer=MemoryLayer.L1_WORKING)
    result = check_memory_pressure(db)
    assert result["l1_count"] == WORKING_MEMORY_CAPACITY
    assert result["distill_suggested"] is True
    assert result["pressure"] >= 0.8
