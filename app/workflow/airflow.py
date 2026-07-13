"""Apache Airflow REST integration."""

from __future__ import annotations

from typing import Any
from urllib.parse import quote, urlparse

import requests


def trigger_airflow(
    dag_id: str,
    *,
    base_url: str,
    token: str = "",
    conf: dict[str, Any] | None = None,
    timeout: float = 30,
) -> dict[str, Any]:
    """Trigger one Airflow DAG run through the stable REST API."""
    parsed = urlparse(base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("Airflow base_url must be an absolute http(s) URL")
    if not dag_id.strip():
        raise ValueError("dag_id is required")

    endpoint = f"{base_url.rstrip('/')}/api/v1/dags/{quote(dag_id, safe='')}/dagRuns"
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    response = requests.post(
        endpoint,
        json={"conf": conf or {}},
        headers=headers,
        timeout=timeout,
    )
    response.raise_for_status()
    try:
        body = response.json()
    except ValueError:
        body = {}
    run_id = body.get("dag_run_id") or body.get("id")
    return {
        "status": "executed",
        "status_code": response.status_code,
        "dag_id": dag_id,
        "run_id": str(run_id) if run_id is not None else "",
    }
