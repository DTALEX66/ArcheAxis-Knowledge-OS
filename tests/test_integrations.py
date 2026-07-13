from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.workflow.airflow import trigger_airflow
from app.workflow.n8n import trigger_n8n
from knowledge_base.routers.composite import evidence_add


class _Response:
    status_code = 201

    def raise_for_status(self):
        return None

    def json(self):
        return {"id": "run-1", "secret": "must-not-be-forwarded"}


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

    def fake_post(url, **kwargs):
        calls.append((url, kwargs))
        return _Response()

    monkeypatch.setattr("app.workflow.n8n.requests.post", fake_post)
    result = trigger_n8n("https://automation.example/webhook/test", {"token": "private"})
    assert result == {"status": "executed", "status_code": 201, "response_id": "run-1"}
    assert calls[0][1]["json"] == {"token": "private"}


def test_n8n_rejects_non_http_webhook():
    with pytest.raises(ValueError, match="http"):
        trigger_n8n("file:///tmp/secret", {})


def test_airflow_triggers_dag_run_with_optional_bearer(monkeypatch):
    calls = []

    def fake_post(url, **kwargs):
        calls.append((url, kwargs))
        return _Response()

    monkeypatch.setattr("app.workflow.airflow.requests.post", fake_post)
    result = trigger_airflow(
        "course-quality",
        base_url="https://airflow.example",
        token="top-secret",
        conf={"course": "C01"},
    )
    assert result["status"] == "executed"
    assert result["dag_id"] == "course-quality"
    assert calls[0][1]["headers"] == {"Authorization": "Bearer top-secret"}
    assert "top-secret" not in str(result)


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
        choices=[SimpleNamespace(message=SimpleNamespace(content="real answer"), finish_reason="stop")],
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
