"""Tests for web capture, ASR adapter, D4 memory completions."""
from __future__ import annotations

import base64
from datetime import datetime
from hashlib import sha256
import sys

import pytest

from app.ingestion.web import WebCaptureError, capture_web, ingest_web
from app.ingestion.raw_asset import RawAssetStore
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


def test_capture_raw_first_with_injected_fetcher(tmp_path):
    raw = b"<html><body>original document</body></html>"

    def fake_fetch(url, policy):
        return _FakeResponse(raw)

    result = capture_web(
        "https://example.com/page",
        raw_fetcher=fake_fetch,
        raw_store=RawAssetStore(root=tmp_path / "raw-assets"),
    )
    assert result["receipt"]["raw_bytes"] == len(raw)
    assert result["receipt"]["text_chars"] == len(result["text"])
    assert result["receipt"]["engine"] in {"safe-http+trafilatura", "safe-http+raw"}
    assert result["receipt"]["raw_hash"]
    assert base64.b64decode(result["raw"]) == raw
    assert "original document" in result["text"]


def test_capture_extracts_the_saved_raw_snapshot_without_a_second_fetch(monkeypatch, tmp_path):
    raw = b"<html><body>raw snapshot only</body></html>"

    def fake_fetch(url, policy):
        return _FakeResponse(raw)

    def second_fetch_is_forbidden(url):
        raise AssertionError("web capture must not fetch the URL a second time")

    monkeypatch.setattr("app.ingestion.multi_format.convert_url", second_fetch_is_forbidden)

    result = capture_web(
        "https://example.com/page",
        raw_fetcher=fake_fetch,
        raw_store=RawAssetStore(root=tmp_path / "raw-assets"),
    )

    assert "raw snapshot only" in result["text"]


def test_capture_receipt_binds_full_raw_hash_and_response_metadata(tmp_path):
    raw = b"<html><body>immutable web response</body></html>"
    response = _FakeResponse(
        raw,
        headers={
            "content-type": "text/html; charset=utf-8",
            "etag": '"revision-1"',
            "last-modified": "Wed, 21 Oct 2015 07:28:00 GMT",
        },
    )
    response.url = "https://example.com/final"

    result = capture_web(
        "https://example.com/original",
        raw_fetcher=lambda _url, _policy: response,
        raw_store=RawAssetStore(root=tmp_path / "raw-assets"),
    )
    receipt = result["receipt"]

    assert receipt["raw_hash"] == sha256(raw).hexdigest()
    assert receipt["final_url"] == "https://example.com/final"
    assert receipt["content_type"] == "text/html"
    assert receipt["etag"] == '"revision-1"'
    assert receipt["last_modified"] == "Wed, 21 Oct 2015 07:28:00 GMT"
    assert datetime.fromisoformat(receipt["captured_at"].replace("Z", "+00:00")).tzinfo is not None


def test_capture_persists_raw_response_before_local_extraction(tmp_path):
    raw = b"<html><body>persisted before conversion</body></html>"
    store = RawAssetStore(root=tmp_path / "raw-assets")

    result = capture_web(
        "https://example.com/persist",
        raw_fetcher=lambda _url, _policy: _FakeResponse(raw),
        raw_store=store,
    )

    assert store.resolve(result["receipt"]["raw_hash"]).read_bytes() == raw


def test_capture_marks_raw_html_fallback_as_degraded_loss(monkeypatch, tmp_path):
    raw = b"<html><body>source retained</body></html>"
    monkeypatch.setattr(
        "app.ingestion.web._extract_saved_html",
        lambda _raw: (raw.decode("utf-8"), "safe-http+raw"),
    )

    result = capture_web(
        "https://example.com/raw",
        raw_fetcher=lambda _url, _policy: _FakeResponse(raw),
        raw_store=RawAssetStore(root=tmp_path / "raw-assets"),
    )

    assert result["loss_report"] == {
        "status": "degraded",
        "warnings": ["content extraction unavailable; raw HTML retained"],
    }


def test_capture_marks_successful_html_extraction_loss_as_not_assessed(monkeypatch, tmp_path):
    raw = b"<html><body>text-focused extraction</body></html>"
    monkeypatch.setattr(
        "app.ingestion.web._extract_saved_html",
        lambda _raw: ("text-focused extraction", "safe-http+trafilatura"),
    )

    result = capture_web(
        "https://example.com/extracted",
        raw_fetcher=lambda _url, _policy: _FakeResponse(raw),
        raw_store=RawAssetStore(root=tmp_path / "raw-assets"),
    )

    assert result["loss_report"] == {
        "status": "not_assessed",
        "warnings": ["HTML extraction loss has not been structurally assessed"],
    }


def test_capture_keeps_raw_snapshot_when_optional_html_extractor_crashes(monkeypatch, tmp_path):
    raw = b"<html><body>recoverable response</body></html>"

    class BrokenTrafilatura:
        @staticmethod
        def extract(*_args, **_kwargs):
            raise RuntimeError("extractor crashed")

    monkeypatch.setitem(sys.modules, "trafilatura", BrokenTrafilatura)

    result = capture_web(
        "https://example.com/recover",
        raw_fetcher=lambda _url, _policy: _FakeResponse(raw),
        raw_store=RawAssetStore(root=tmp_path / "raw-assets"),
    )

    assert result["receipt"]["engine"] == "safe-http+raw"
    assert result["loss_report"]["status"] == "degraded"
    assert base64.b64decode(result["raw"]) == raw


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
