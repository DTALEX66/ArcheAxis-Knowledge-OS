"""n8n webhook integration with explicit network execution semantics."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

import requests


def trigger_n8n(webhook_url: str, payload: dict[str, Any], timeout: float = 30) -> dict[str, Any]:
    """POST a workflow payload and return bounded, non-secret execution evidence."""
    parsed = urlparse(webhook_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("n8n webhook_url must be an absolute http(s) URL")
    response = requests.post(webhook_url, json=payload, timeout=timeout)
    response.raise_for_status()
    try:
        body = response.json()
    except ValueError:
        body = {}
    response_id = body.get("id") or body.get("executionId") or body.get("execution_id")
    return {
        "status": "executed",
        "status_code": response.status_code,
        "response_id": str(response_id) if response_id is not None else "",
    }
