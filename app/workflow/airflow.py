"""Apache Airflow REST integration."""

from __future__ import annotations

import json
from typing import Any
from urllib.parse import quote, urlparse

from shared.safe_http import SafeHTTPPolicy, fetch


def trigger_airflow(
    dag_id: str,
    *,
    base_url: str,
    token: str = "",
    conf: dict[str, Any] | None = None,
    timeout: float = 30,
    allowed_hosts: tuple[str, ...] = (),
) -> dict[str, Any]:
    """Trigger one Airflow DAG run through the stable REST API."""
    parsed = urlparse(base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("Airflow base_url must be an absolute http(s) URL")
    if not dag_id.strip():
        raise ValueError("dag_id is required")
    if not allowed_hosts:
        raise ValueError("Airflow host allowlist is required")

    endpoint = f"{base_url.rstrip('/')}/api/v1/dags/{quote(dag_id, safe='')}/dagRuns"
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    headers["Content-Type"] = "application/json"
    response = fetch(
        endpoint,
        method="POST",
        body=json.dumps({"conf": conf or {}}).encode("utf-8"),
        headers=headers,
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
    run_id = body.get("dag_run_id") or body.get("id")
    return {
        "status": "executed",
        "status_code": response.status,
        "dag_id": dag_id,
        "run_id": str(run_id) if run_id is not None else "",
    }
