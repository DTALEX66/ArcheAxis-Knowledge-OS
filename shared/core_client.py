"""ArcheAxis Core HTTP client (R10 host adapter, first slice).

The DeepTutor host side talks to the Core only through this module: it builds and
issues Core API calls and never touches the Core database, so the host cannot
write around the Core's authority. Requests are pure functions so their shape can
be asserted without a running Core.

Authentication follows the Core's launch-session model: the launch token issued on
the Core's stdin is presented as `x-archeaxis-launch-token`. The caller's identity
(actor) is a server-side claim, so request bodies never carry an actor field.
"""

from __future__ import annotations

import base64
import json
import urllib.error
import urllib.parse
import urllib.request

BASE = "/api/v1"
TOKEN_HEADER = "x-archeaxis-launch-token"


def headers(launch_token: str | None = None) -> dict[str, str]:
    """Headers for a Core call. The token is never logged or echoed."""
    result = {"Content-Type": "application/json"}
    if launch_token:
        result[TOKEN_HEADER] = launch_token
    return result


def import_request(name: str, content: bytes) -> dict:
    """Import a file's bytes as a Core source."""
    if not name.strip():
        raise ValueError("an imported source needs a name")
    if not content:
        raise ValueError("an imported source must not be empty")
    return {"name": name, "content_base64": base64.b64encode(content).decode("ascii")}


def search_path(query: str, active_only: bool = False) -> str:
    """Search path. `active_only` asks the Core for current revisions only."""
    if not query.strip():
        raise ValueError("a search needs a query")
    suffix = "&active_only=true" if active_only else ""
    return f"{BASE}/search?q={urllib.parse.quote(query)}{suffix}"


def learning_event_request(
    item_key: str,
    correct: bool,
    client_event_id: str,
    schedule_state: dict | None = None,
    now: str | None = None,
) -> dict:
    """A learning outcome. A persistent client event id is mandatory (retries
    replay the original receipt). The scheduler state travels as data, so the
    Core's reused FSRS worker decides the interval."""
    if not item_key.strip():
        raise ValueError("a learning event needs an item_key")
    if not client_event_id.strip():
        raise ValueError("a learning event needs a persistent client_event_id")
    body: dict = {"item_key": item_key, "correct": correct, "client_event_id": client_event_id}
    if schedule_state is not None:
        body["schedule_state"] = schedule_state
    if now is not None:
        body["now"] = now
    return body


def reference_request(item_key: str, knowledge_id: str) -> dict:
    """Record the revision a learning item was built from (immutable once set)."""
    if not item_key.strip() or not knowledge_id.strip():
        raise ValueError("a reference needs both an item_key and a knowledge_id")
    return {"knowledge_id": knowledge_id}


def review_request(action: str, reviewer: str, new_body: str | None = None, note: str | None = None) -> dict:
    """A human review action. `modified` carries the corrected content that
    becomes the successor revision; acceptance never rewrites body bytes."""
    if action not in {"accepted", "rejected", "deprecated", "modified"}:
        raise ValueError(f"unknown review action {action!r}")
    if not reviewer.strip():
        raise ValueError("a review needs a reviewer")
    body: dict = {"action": action, "reviewer": reviewer}
    if new_body is not None:
        body["new_body"] = new_body
    if note is not None:
        body["note"] = note
    return body


def call(base_url: str, method: str, path: str, launch_token: str | None, body: dict | str | None = None, timeout: float = 30.0):
    """Issue one Core call and return (status, decoded_json_or_text)."""
    data = None
    if body is not None:
        data = (body if isinstance(body, str) else json.dumps(body)).encode("utf-8")
    request = urllib.request.Request(
        base_url.rstrip("/") + path, data=data, method=method.upper(), headers=headers(launch_token)
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8", "replace")
            status = response.status
    except urllib.error.HTTPError as error:  # an error status is a result, not a crash
        raw = error.read().decode("utf-8", "replace")
        status = error.code
    except (urllib.error.URLError, OSError) as error:
        # The Core being unreachable is reported as an explicit non-200 result so a
        # host caller can surface it instead of crashing mid-journey.
        return 0, {"error": f"core unreachable: {error}"}
    try:
        return status, json.loads(raw)
    except json.JSONDecodeError:
        return status, raw
