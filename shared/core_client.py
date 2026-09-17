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
import hashlib
import json
import time
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


def call(
    base_url: str,
    method: str,
    path: str,
    launch_token: str | None,
    body: dict | str | None = None,
    timeout: float = 30.0,
    extra_headers: dict[str, str] | None = None,
):
    """Issue one Core call and return (status, decoded_json_or_text)."""
    data = None
    if body is not None:
        data = (body if isinstance(body, str) else json.dumps(body)).encode("utf-8")
    request = urllib.request.Request(
        base_url.rstrip("/") + path,
        data=data,
        method=method.upper(),
        headers={**headers(launch_token), **(extra_headers or {})},
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


def run_journey(
    call,
    base_url: str,
    launch_token: str | None,
    sample_name: str,
    sample_bytes: bytes,
    query: str,
    item_key: str,
    client_event_id: str,
) -> dict:
    """Probe reachability, source storage and existing search results only.

    Kept under its historical name for callers. This is not a cold-start learning
    journey: it neither parses the imported source nor proves that search hits
    derive from it. Never invent an answer or write learner progress. The legacy
    item/event arguments remain accepted for compatibility, but are unused.
    """
    steps: list[dict] = []

    def step(name: str, method: str, path: str, body=None) -> tuple[int, object]:
        status, payload = call(base_url, method, path, launch_token, body)
        steps.append({"step": name, "method": method, "path": path, "status": status})
        return status, payload

    status, version = step("reachability", "GET", f"{BASE}/system/version")
    if status != 200:
        return {"ok": False, "failed_step": "reachability", "steps": steps, "payload": version}

    status, imported = step("import", "POST", f"{BASE}/imports", import_request(sample_name, sample_bytes))
    if not 200 <= status < 300:
        return {"ok": False, "failed_step": "import", "steps": steps, "payload": imported}
    source_id = imported.get("source_id") if isinstance(imported, dict) else None

    search_url = search_path(query, active_only=True)
    found: object = None
    hits: list | None = None
    transforms: list | None = None
    search_attempts = 0
    # Imports are accepted asynchronously (202).  Give the Core's indexer a
    # short bounded window to publish a real hit; never turn an empty result
    # into success and never wait forever on a broken indexer.
    for search_attempts in range(1, 11):
        status, found = step("search", "GET", search_url)
        if status != 200:
            return {"ok": False, "failed_step": "search", "steps": steps, "payload": found,
                    "search_attempts": search_attempts}
        hits = found.get("items") if isinstance(found, dict) else None
        transforms = found.get("transforms") if isinstance(found, dict) else None
        has_knowledge = isinstance(hits, list) and any(
            isinstance(hit, dict) and hit.get("knowledge_id") for hit in hits
        )
        has_transform = isinstance(transforms, list) and any(
            isinstance(item, dict) and item.get("transform_id") and item.get("source_id")
            for item in transforms
        )
        if has_knowledge or has_transform:
            break
        if search_attempts < 10:
            time.sleep(0.2)
    knowledge_count = sum(
        1 for hit in (hits if isinstance(hits, list) else [])
        if isinstance(hit, dict) and hit.get("knowledge_id")
    )
    transform_count = sum(
        1 for item in (transforms if isinstance(transforms, list) else [])
        if isinstance(item, dict) and item.get("transform_id") and item.get("source_id")
    )
    if knowledge_count == 0 and transform_count == 0:
        return {"ok": False, "failed_step": "search_results", "steps": steps,
                "source_id": source_id, "scope": "adapter_probe",
                "closed_loop_verified": False, "payload": found,
                "search_attempts": search_attempts}
    return {
        "ok": True,
        "scope": "adapter_probe",
        "closed_loop_verified": False,
        "steps": steps,
        "source_id": source_id,
        "search_count": knowledge_count,
        "knowledge_count": knowledge_count,
        "transform_count": transform_count,
        "search_attempts": search_attempts,
        "referenced_revision": None,
        "note": "adapter probe only; source-to-knowledge conversion is unverified; learning and review require a human action",
    }


def job_kind_for_name(name: str) -> str:
    """Map a source filename to the Core's declared route kind."""
    suffix = name.rsplit(".", 1)[-1].casefold() if "." in name else ""
    return {
        "pdf": "pdf",
        "png": "image", "jpg": "image", "jpeg": "image", "tif": "image",
        "tiff": "image", "webp": "image", "bmp": "image",
        "zip": "archive", "mp4": "media", "wav": "media",
        "docx": "office", "pptx": "office", "xlsx": "office",
        "canvas": "canvas", "srt": "subtitles", "vtt": "subtitles",
        "html": "html", "htm": "html",
    }.get(suffix, "text")


def run_conversion_journey(
    call,
    base_url: str,
    launch_token: str | None,
    sample_name: str,
    sample_bytes: bytes,
    query: str,
    *,
    poll_attempts: int = 30,
) -> dict:
    """Run a real import, worker execution, transform readback and search.

    This is an execution probe, not a knowledge promotion path: extracted text
    remains a transform and still requires human review before becoming knowledge.
    """
    steps: list[dict] = []

    def step(name: str, method: str, path: str, body=None, extra_headers=None):
        status, payload = call(base_url, method, path, launch_token, body, extra_headers=extra_headers)
        steps.append({"step": name, "method": method, "path": path, "status": status})
        return status, payload

    status, version = step("reachability", "GET", f"{BASE}/system/version")
    if status != 200:
        return {"ok": False, "failed_step": "reachability", "steps": steps, "payload": version}
    status, imported = step("import", "POST", f"{BASE}/imports", import_request(sample_name, sample_bytes))
    source_id = imported.get("source_id") if isinstance(imported, dict) else None
    if not 200 <= status < 300 or not source_id:
        return {"ok": False, "failed_step": "import", "steps": steps, "payload": imported}

    digest = hashlib.sha256(f"{sample_name}\0{source_id}".encode()).hexdigest()[:24]
    job_id = f"host-probe-{digest}"
    status, queued = step(
        "enqueue", "POST", f"{BASE}/jobs",
        {"job_id": job_id, "kind": job_kind_for_name(sample_name), "input_ref": source_id},
    )
    if not 200 <= status < 300:
        return {"ok": False, "failed_step": "enqueue", "steps": steps, "source_id": source_id, "payload": queued}
    status, started = step(
        "execute", "POST", f"{BASE}/jobs/{urllib.parse.quote(job_id, safe='')}/executions",
        {"deadline_ms": 300000}, {"idempotency-key": job_id},
    )
    if not 200 <= status < 300:
        return {"ok": False, "failed_step": "execute", "steps": steps, "source_id": source_id, "job_id": job_id, "payload": started}

    final: object = None
    for attempt in range(1, poll_attempts + 1):
        status, final = step("job_status", "GET", f"{BASE}/jobs/{urllib.parse.quote(job_id, safe='')}")
        state = final.get("state") if isinstance(final, dict) else None
        if state == "succeeded":
            break
        if state in {"failed", "cancelled"} or status != 200:
            return {"ok": False, "failed_step": "job_status", "steps": steps, "source_id": source_id,
                    "job_id": job_id, "job_state": state, "payload": final, "poll_attempts": attempt}
        time.sleep(0.2)
    else:
        return {"ok": False, "failed_step": "job_timeout", "steps": steps, "source_id": source_id,
                "job_id": job_id, "job_state": final.get("state") if isinstance(final, dict) else None,
                "poll_attempts": poll_attempts}

    status, output = step("output", "GET", f"{BASE}/jobs/{urllib.parse.quote(job_id, safe='')}/outputs/text")
    if status != 200:
        return {"ok": False, "failed_step": "output", "steps": steps, "source_id": source_id,
                "job_id": job_id, "payload": output}
    status, found = step("search", "GET", search_path(query, active_only=False))
    transforms = found.get("transforms", []) if isinstance(found, dict) else []
    knowledge = found.get("items", []) if isinstance(found, dict) else []
    valid_transforms = [item for item in transforms if isinstance(item, dict) and item.get("transform_id") and item.get("source_id")]
    valid_knowledge = [item for item in knowledge if isinstance(item, dict) and item.get("knowledge_id")]
    return {
        "ok": status == 200 and bool(valid_transforms or valid_knowledge),
        "failed_step": None if status == 200 and (valid_transforms or valid_knowledge) else "search_results",
        "scope": "real_conversion_probe",
        "closed_loop_verified": False,
        "steps": steps,
        "source_id": source_id,
        "job_id": job_id,
        "output_status": "readable" if isinstance(output, dict) else "returned",
        "knowledge_count": len(valid_knowledge),
        "transform_count": len(valid_transforms),
    }
