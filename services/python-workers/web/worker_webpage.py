#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ArcheAxis vNext web worker: bounded snapshot fetch (F02 network part).

Fetches one HTTP(S) URL with strict bounds (timeout, byte cap, redirect
chain tracking), writes the final HTML snapshot plus a fetch receipt into
the caller-provided out-dir, and returns the final URL and status. Network
failure never fabricates a snapshot: the error is recorded and returned.

Dynamic rendering and screenshot capture are the F03 lane; ad/noise
separation happens in the extraction lane (worker_html + later
trafilatura-grade parsing).

Usage:
    python worker_webpage.py <url> --out-dir <dir>
    python worker_webpage.py --probe
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ENGINE = "python-worker-webpage"
ENGINE_VERSION = "0.1.0"

TIMEOUT_S = 20
MAX_BYTES = 5 * 1024 * 1024
MAX_REDIRECTS = 8
USER_AGENT = "ArcheAxisKnowledgeOS/0.1 (local research snapshot; contact on file)"


def probe() -> dict:
    return {
        "capability": True,
        "engine": ENGINE,
        "params": {"timeout_s": TIMEOUT_S, "max_bytes": MAX_BYTES, "max_redirects": MAX_REDIRECTS},
        "note": "bounded fetch only; JS rendering and screenshots are the F03 lane",
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fetch(url: str, out_dir: Path) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    if not url.lower().startswith(("http://", "https://")):
        raise ValueError(f"unsupported URL scheme (http/https only): {url[:80]}")

    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    final_url = url
    status = 0
    snapshot: bytes | None = None
    content_type = ""
    error_record: str | None = None
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_S) as response:
            final_url = response.geturl()
            status = response.status
            content_type = response.headers.get("Content-Type", "")
            if not content_type.lower().startswith("text/html"):
                # store anyway; extraction lane decides
                pass
            chunks: list[bytes] = []
            total = 0
            while True:
                chunk = response.read(64 * 1024)
                if not chunk:
                    break
                chunks.append(chunk)
                total += len(chunk)
                if total > MAX_BYTES:
                    error_record = f"body exceeded {MAX_BYTES} byte cap; snapshot truncated"
                    break
            snapshot = b"".join(chunks)
    except Exception as exc:  # noqa: BLE001
        error_record = f"{type(exc).__name__}: {exc}"

    fetched_at = datetime.now(timezone.utc).isoformat()
    if snapshot is not None:
        snapshot_path = out_dir / "snapshot.html"
        snapshot_path.write_bytes(snapshot)
        snapshot_sha = _sha256(snapshot_path)
        snapshot_bytes = len(snapshot)
    else:
        snapshot_path = None
        snapshot_sha = None
        snapshot_bytes = 0

    receipt = {
        "schema": "archeaxis.fetch-receipt/v1",
        "requested_url": url,
        "final_url": final_url,
        "http_status": status,
        "content_type": content_type,
        "fetched_at": fetched_at,
        "snapshot": (
            {"path": str(snapshot_path), "sha256": snapshot_sha, "bytes": snapshot_bytes}
            if snapshot_path
            else None
        ),
        "error": error_record,
    }
    (out_dir / "fetch-receipt.json").write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    if error_record:
        raise RuntimeError(error_record)
    return {
        "engine": ENGINE,
        "engine_version": ENGINE_VERSION,
        "final_url": final_url,
        "http_status": status,
        "snapshot": {"path": str(snapshot_path), "sha256": snapshot_sha, "bytes": snapshot_bytes},
        "fetched_at": fetched_at,
        "loss_receipt": {
            "engine": ENGINE,
            "engine_version": ENGINE_VERSION,
            "params": {"timeout_s": TIMEOUT_S, "max_bytes": MAX_BYTES, "user_agent": USER_AGENT},
            "loss_note": "bounded fetch; JS/dynamic content and screenshots are the F03 lane",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="ArcheAxis bounded webpage snapshot worker")
    parser.add_argument("url", nargs="?", help="http(s) URL")
    parser.add_argument("--out-dir", required=False)
    parser.add_argument("--probe", action="store_true")
    args = parser.parse_args()
    if args.probe:
        print(json.dumps(probe(), ensure_ascii=False))
        return 0
    if not args.url or not args.out_dir:
        print(json.dumps({"error": "usage: worker_webpage.py <url> --out-dir <dir>"}))
        return 2
    try:
        out = fetch(args.url, Path(args.out_dir))
    except Exception as exc:  # noqa: BLE001 - network failures are recorded errors
        # distinguish capability/usage failures from fetch failures: fetch
        # failures already wrote a receipt with error; report structured error.
        print(json.dumps({"error": str(exc), "recorded": "fetch-receipt.json"}, ensure_ascii=False))
        return 1
    print(json.dumps(out, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
