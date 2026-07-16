"""n8n webhook integration with explicit network execution semantics."""

from __future__ import annotations

import json
from typing import Any
from urllib.parse import urlparse

from shared.safe_http import SafeHTTPPolicy, fetch


def trigger_n8n(
    webhook_url: str,
    payload: dict[str, Any],
    timeout: float = 30,
    *,
    allowed_hosts: tuple[str, ...] = (),
) -> dict[str, Any]:
    """POST a workflow payload and return bounded, non-secret execution evidence."""
    parsed = urlparse(webhook_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("n8n webhook_url must be an absolute http(s) URL")
    if not allowed_hosts:
        raise ValueError("n8n webhook allowlist is required")
    response = fetch(
        webhook_url,
        method="POST",
        body=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        policy=SafeHTTPPolicy(
            timeout=min(timeout, 60),
            allowed_hosts=allowed_hosts,
            allowed_content_types=("application/json", "text/plain"),
        ),
    )
    try:
        body = json.loads(response.body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        body = {}
    response_id = body.get("id") or body.get("executionId") or body.get("execution_id")
    return {
        "status": "executed",
        "status_code": response.status,
        "response_id": str(response_id) if response_id is not None else "",
    }
