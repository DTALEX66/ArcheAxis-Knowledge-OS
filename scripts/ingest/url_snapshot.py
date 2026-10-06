#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R15/F02: fetch one public URL, import the snapshot, and queue the job its kind calls for.

The format family asked for a capture time and there was nothing to capture with: only a saved
snapshot could be read, and `received_at` had to be left NULL because a clock value must not be
invented. This is the piece that makes the receipt true - it fetches, records the moment the body
arrived, and hands that to the Core as the origin's `received_at`.

It is a driver, not a Core route: the route table stays without a network-holding capability, so a
job can never reach out by itself. The address policy that keeps this from being a way to poke
internal services lives in the worker it calls (`services/python-workers/web/worker_webpage.py`).

Usage:
    python scripts/ingest/url_snapshot.py <url> [--core-base URL] [--token-env NAME]
                                          [--manifest FILE] [--dry-run] [--json]
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import importlib.util
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

REPO = Path(__file__).resolve().parents[2]
USER_AGENT = "ArcheAxisKnowledgeOS/0.1 (local research snapshot; contact on file)"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"{path} is not loadable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def snapshot_name(url: str) -> str:
    """A file name for the snapshot that still says which page it came from.

    A URL path is not a file name: it may be empty, may carry separators, and may try to escape
    the name it is given, so only the last plain segment survives, and a bare host is enough.
    """
    parts = urlparse(url)
    tail = Path(parts.path).name if parts.path not in ("", "/") else ""
    safe = "".join(char if char.isalnum() or char in "._-" else "_" for char in tail)[:80]
    if not safe or not safe.lower().endswith((".html", ".htm", ".xhtml")):
        safe = f"{(safe or 'index')}.html"
    return f"{(parts.hostname or 'host').strip('[]')}-{safe}"[:120]


def run_snapshot(url: str, core_call, *, workspace: Path, dry_run: bool = False,
                 render: bool = False, scroll_limit: int | None = None) -> dict:
    """Fetch one URL and import the result as a source whose origin carries the capture time.

    With `render`, the served body is still fetched and kept, and what gets imported is the DOM the
    browser produced after the page's own scripts ran - a page that only builds its text in the
    browser is otherwise unreadable here. A render that cannot happen is a failure, never a silent
    fall back to the served bytes.
    """
    webpage = _load("url_snapshot_webpage", REPO / "services/python-workers/web/worker_webpage.py")
    out_dir = workspace / "fetch" / hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]
    record = {
        "schema": "archeaxis.url-snapshot/v1",
        "url": url,
        "at": datetime.now(timezone.utc).isoformat(),
        "name": snapshot_name(url),
        "mode": "rendered" if render else "served",
    }
    try:
        if render:
            capture = (webpage.render(url, out_dir, scroll_limit=scroll_limit)
                       if scroll_limit is not None else webpage.render(url, out_dir))
        else:
            capture = webpage.fetch(url, out_dir)
    except Exception as exc:  # noqa: BLE001 - a capture that did not happen is recorded, not faked
        record.update(status="failed", error=f"{type(exc).__name__}: {exc}", source_id=None, job_id=None)
        return record
    body_source = capture["rendered"] if render else capture["snapshot"]
    body = Path(body_source["path"]).read_bytes()
    received_at = capture["fetched_at"]
    record.update(
        final_url=capture["final_url"],
        http_status=capture["http_status"],
        sha256=body_source["sha256"],
        bytes=body_source["bytes"],
        received_at=received_at,
    )
    if render:
        record.update(
            served_sha256=capture["snapshot"]["sha256"],
            served_bytes=capture["snapshot"]["bytes"],
            title=capture["title"],
            scroll=capture["loss_receipt"]["params"]["scroll"],
        )
    if dry_run:
        record.update(status="dry_run", source_id=None, job_id=None)
        return record

    status, imported = core_call("POST", "/api/v1/imports", {
        "name": record["name"],
        "content_base64": base64.b64encode(body).decode("ascii"),
        "origin_kind": "url",
        "origin_ref": capture["final_url"],
        "origin_name": record["name"],
        "received_at": received_at,
    })
    if status not in (200, 201) or not isinstance(imported, dict) or not imported.get("source_id"):
        record.update(status="failed", error=f"import returned {status}: {str(imported)[:200]}",
                      source_id=None, job_id=None)
        return record
    source_id = imported["source_id"]
    kind = "html"  # the worker keeps an HTML body; the media type says so in the receipt
    job_id = f"url-{record['sha256'][:16]}"
    job_status, job_body = core_call("POST", "/api/v1/jobs", {
        "job_id": job_id, "kind": kind, "input_ref": source_id,
    })
    record.update(
        status="enqueued" if job_status in (200, 201) else "imported_job_failed",
        source_id=source_id,
        job_id=job_id if job_status in (200, 201) else None,
        error=None if job_status in (200, 201) else f"job enqueue returned {job_status}: {str(job_body)[:200]}",
    )
    return record


def append_record(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record, ensure_ascii=False) + "\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("url")
    parser.add_argument("--core-base", default=os.environ.get("ARCHEAXIS_CORE_BASE", "http://127.0.0.1:8777"))
    parser.add_argument("--token-env", default="ARCHEAXIS_CORE_TOKEN")
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--workspace", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--render", action="store_true",
                        help="import the browser-rendered DOM instead of the served bytes")
    parser.add_argument("--scroll-limit", type=int)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    core = _load("url_snapshot_core_client", REPO / "shared/core_client.py")
    token = os.environ.get(args.token_env) or None
    workspace = args.workspace or REPO / ".project-local" / "url-snapshots"
    manifest = args.manifest or workspace / "receipts.jsonl"
    record = run_snapshot(
        args.url,
        lambda method, path, body: core.call(args.core_base, method, path, token, body),
        workspace=workspace,
        dry_run=args.dry_run,
        render=args.render,
        scroll_limit=args.scroll_limit,
    )
    if not args.dry_run:
        append_record(manifest, record)
    if args.json:
        print(json.dumps(record, ensure_ascii=False))
    else:
        print(f"{record['status']} {record['url']} -> {record.get('source_id') or record.get('error')}")
    return 0 if record["status"] in ("enqueued", "dry_run") else 1


if __name__ == "__main__":
    sys.exit(main())
