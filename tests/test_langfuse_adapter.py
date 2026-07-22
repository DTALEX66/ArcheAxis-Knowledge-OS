from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


def _load_adapter():
    path = (
        Path(__file__).resolve().parents[1]
        / "shared-contracts"
        / "adapters"
        / "observability"
        / "langfuse_adapter.py"
    )
    spec = importlib.util.spec_from_file_location("test_langfuse_adapter", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class _Observation:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False


class _Client:
    def __init__(self):
        self.calls: list[dict] = []

    def start_as_current_observation(self, **kwargs):
        self.calls.append(kwargs)
        return _Observation()


def test_langfuse_adapter_queues_only_allowlisted_metadata() -> None:
    adapter = _load_adapter()
    client = _Client()

    result = adapter.queue_event(
        "research.completed",
        {
            "component": "workspace",
            "operation": "research",
            "outcome": "succeeded",
            "duration_ms": 12,
        },
        client=client,
    )

    assert result.name == "research.completed"
    assert result.status == "queued"
    assert client.calls == [
        {
            "name": "research.completed",
            "as_type": "event",
            "metadata": {
                "component": "workspace",
                "operation": "research",
                "outcome": "succeeded",
                "duration_ms": 12,
            },
            "level": "DEFAULT",
        }
    ]
    assert "input" not in client.calls[0]
    assert "output" not in client.calls[0]


def test_langfuse_adapter_rejects_payload_like_metadata_and_missing_client_configuration() -> None:
    adapter = _load_adapter()

    with pytest.raises(ValueError, match="not allowed"):
        adapter.queue_event("research.completed", {"input": "secret"}, client=_Client())
    with pytest.raises(ValueError, match="explicit client"):
        adapter.queue_event("research.completed", {"component": "workspace"})
