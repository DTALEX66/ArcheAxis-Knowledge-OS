from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.ingestion.multi_format import convert_url
from app.workflow.airflow import trigger_airflow
from app.workflow.n8n import trigger_n8n
from knowledge_base.routers.composite import evidence_add


class _Response:
    status = 201
    headers = {"content-type": "application/json"}
    body = b'{"id": "run-1", "secret": "must-not-be-forwarded"}'


def test_evidence_caption_is_not_written_as_status(monkeypatch):
    from shared import evidence_index

    captured = {}

    def fake_index(*args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        return {"ok": True}

    monkeypatch.setattr(evidence_index, "index_evidence", fake_index)
    evidence_add("doc-1", "pdf", "lesson.pdf", "high", "page three")
    assert captured["args"] == ("doc-1", "pdf", "lesson.pdf", "high")
    assert captured["kwargs"] == {"caption": "page three"}


def test_n8n_executes_real_webhook_without_returning_payload_secret(monkeypatch):
    calls = []

    def fake_fetch(url, **kwargs):
        calls.append((url, kwargs))
        return _Response()

    monkeypatch.setattr("app.workflow.n8n.fetch", fake_fetch)
    result = trigger_n8n(
        "https://automation.example/webhook/test",
        {"token": "private"},
        allowed_hosts=("automation.example",),
    )
    assert result == {"status": "executed", "status_code": 201, "response_id": "run-1"}
    assert calls[0][1]["method"] == "POST"
    assert b'"token": "private"' in calls[0][1]["body"]


def test_n8n_rejects_non_http_webhook():
    with pytest.raises(ValueError, match="http"):
        trigger_n8n("file:///tmp/secret", {})


def test_airflow_triggers_dag_run_with_optional_bearer(monkeypatch):
    calls = []

    def fake_fetch(url, **kwargs):
        calls.append((url, kwargs))
        return _Response()

    monkeypatch.setattr("app.workflow.airflow.fetch", fake_fetch)
    result = trigger_airflow(
        "course-quality",
        base_url="https://airflow.example",
        token="top-secret",
        conf={"course": "C01"},
        allowed_hosts=("airflow.example",),
    )
    assert result["status"] == "executed"
    assert result["dag_id"] == "course-quality"
    assert calls[0][1]["headers"]["Authorization"] == "Bearer top-secret"
    assert calls[0][1]["method"] == "POST"
    assert "top-secret" not in str(result)


def test_airflow_requires_explicit_host_allowlist():
    with pytest.raises(ValueError, match="allowlist"):
        trigger_airflow("course-quality", base_url="https://airflow.example")


def _load_adapter(relative: str, module_name: str):
    path = Path(__file__).resolve().parents[1] / "shared-contracts" / "adapters" / relative
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_litellm_adapter_returns_real_provider_response(monkeypatch):
    fake_response = SimpleNamespace(
        model="provider/model",
        choices=[
            SimpleNamespace(message=SimpleNamespace(content="real answer"), finish_reason="stop")
        ],
        usage=SimpleNamespace(total_tokens=12),
    )
    monkeypatch.setitem(
        sys.modules,
        "litellm",
        SimpleNamespace(completion=lambda **kwargs: fake_response),
    )
    adapter = _load_adapter("llm/litellm_adapter.py", "test_litellm_adapter")
    result = adapter.complete("question")
    assert result.content == "real answer"
    assert result.tokens_used == 12


def test_crawl_adapter_uses_real_conversion_result(monkeypatch):
    monkeypatch.setattr(
        "app.ingestion.multi_format.convert_url",
        lambda url: ("# Extracted page", "test-engine"),
    )
    adapter = _load_adapter("crawlers/crawl4ai_adapter.py", "test_crawl_adapter")
    page = adapter.crawl_url("https://example.com/page")
    assert page.markdown == "# Extracted page"
    assert page.metadata["engine"] == "test-engine"
    assert not page.errors


def test_url_conversion_fetches_html_through_safe_http(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "app.ingestion.multi_format.fetch",
        lambda url, **kwargs: (
            calls.append((url, kwargs))
            or SimpleNamespace(body=b"<html><article>safe page</article></html>")
        ),
    )

    result = convert_url("https://example.com/page")

    # Without network: newspaper4k fails (real HTTP), readabilipy fails
    # (shared.safe_http.fetch not mocked), trafilatura succeeds on the
    # already-fetched HTML string (installed in venv).
    assert result == (
        "safe page",
        "safe-http+trafilatura",
    )
    assert calls[0][1]["policy"].max_bytes == 5_000_000


def test_feed_fetch_uses_safe_http(monkeypatch):
    from shared.feed_collector import _fetch_url

    monkeypatch.setattr(
        "shared.feed_collector.fetch",
        lambda url, **kwargs: SimpleNamespace(body=b"<rss />"),
    )

    assert _fetch_url("https://example.com/feed.xml") == b"<rss />"


def test_github_registry_search_is_retired() -> None:
    from inspiration_research.project_radar.collectors.github_trending import _search_github

    with pytest.raises(RuntimeError, match="legacy GitHub search is disabled"):
        _search_github("safe query")


def test_youtube_oembed_uses_safe_http(monkeypatch):
    from shared.youtube_extractor import get_video_info

    monkeypatch.setattr(
        "shared.youtube_extractor.fetch",
        lambda url, **kwargs: SimpleNamespace(
            body=b'{"title": "Safe video", "author_name": "Author"}'
        ),
    )

    result = get_video_info("abcdefghijk")

    assert result["title"] == "Safe video"
    assert result["author"] == "Author"


def test_duckduckgo_search_uses_safe_http(monkeypatch):
    from shared.web_search import _ddg_html_search

    html = (
        b'<a href="https://example.com" class="result-link">Title</a>'
        b'<td class="result-snippet">Description</td>'
    )
    monkeypatch.setattr(
        "shared.web_search.fetch",
        lambda url, **kwargs: SimpleNamespace(body=html),
    )

    assert _ddg_html_search("safe query", limit=1) == [
        {"title": "Title", "url": "https://example.com", "description": "Description"}
    ]


def test_feed_collection_skips_hostile_xml(monkeypatch):
    from shared.feed_collector import collect_feeds

    monkeypatch.setattr(
        "shared.feed_collector._fetch_url",
        lambda url: b"<!DOCTYPE foo [<!ENTITY xxe SYSTEM 'file:///secret'>]><rss>&xxe;</rss>",
    )

    assert collect_feeds(["https://example.com/feed.xml"]) == []
