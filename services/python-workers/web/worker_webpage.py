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
import ipaddress
import json
import socket
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

ENGINE = "python-worker-webpage"
ENGINE_VERSION = "0.1.0"

TIMEOUT_S = 20
MAX_BYTES = 5 * 1024 * 1024
MAX_REDIRECTS = 8
USER_AGENT = "ArcheAxisKnowledgeOS/0.1 (local research snapshot; contact on file)"


def _is_public(address: str) -> bool:
    """True only for an address a public host could actually be reached at."""
    try:
        ip = ipaddress.ip_address(address)
    except ValueError:
        return False
    if ip.version == 6 and (ip.ipv4_mapped is not None or ip.sixtofour is not None):
        # ::ffff:127.0.0.1 and 6to4 forms are the same host wearing another address family
        inner = ip.ipv4_mapped or ip.sixtofour
        return inner is not None and _is_public(str(inner))
    return not (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved
                or ip.is_multicast or ip.is_unspecified
                or (ip.version == 6 and ip.is_site_local))


def public_addresses(host: str, resolver=None) -> list[str]:
    """Every address this hostname resolves to, or a refusal.

    A hostname that resolves partly to an internal address is refused as well: picking the
    convenient answer would be the same mistake with extra steps. A literal IP address is
    judged directly. Note the limit honestly - the address is checked when it is resolved, so
    an authoritative name that answers differently between the check and the connection
    (DNS rebinding) is not defeated here; egress policy at the network layer is that boundary.
    """
    if not host:
        raise ValueError("a URL without a host cannot be checked")
    # bound here rather than in the signature: a default captured at import time cannot be
    # substituted by a caller or a test, which would leave this decision untestable
    resolve = resolver or socket.getaddrinfo
    bare = host.strip("[]")
    try:
        literal = ipaddress.ip_address(bare)
    except ValueError:
        literal = None
    if literal is not None:
        if not _is_public(str(literal)):
            raise ValueError(f"refused {host}: it is not a public address")
        return [str(literal)]
    try:
        answers = sorted({entry[4][0] for entry in resolve(host, None)})
    except OSError as exc:
        raise ValueError(f"refused {host}: it does not resolve ({exc})") from exc
    if not answers:
        raise ValueError(f"refused {host}: it resolves to nothing")
    for address in answers:
        if not _is_public(address.split("%", 1)[0]):
            raise ValueError(f"refused {host}: it resolves to the non-public address {address}")
    return answers


class _GuardedRedirects(urllib.request.HTTPRedirectHandler):
    """Re-apply the address policy to every redirect target.

    urllib follows redirects by itself, so without this a public page could hand the worker an
    internal URL and the policy would have inspected only the first one.
    """

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        target = urlparse(newurl)
        if target.scheme.lower() not in ("http", "https"):
            raise ValueError(f"refused redirect to unsupported scheme: {newurl[:120]}")
        public_addresses(target.hostname or "")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


OPENER = urllib.request.build_opener(_GuardedRedirects)


def checked_open(request, timeout: float):
    """Open a prepared request through the guarded opener."""
    return OPENER.open(request, timeout=timeout)


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

    parts = urlparse(url)
    if parts.scheme.lower() not in ("http", "https"):
        raise ValueError(f"unsupported URL scheme (http/https only): {url[:80]}")
    # the policy runs before any packet leaves: an internal host is refused by address, not by name
    public_addresses(parts.hostname or "")
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    final_url = url
    status = 0
    snapshot: bytes | None = None
    content_type = ""
    error_record: str | None = None
    try:
        with checked_open(request, TIMEOUT_S) as response:
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
                    # a half-read body is not a snapshot: nothing is written and the caller
                    # is told the size it exceeded
                    raise ValueError(
                        f"body exceeded the {MAX_BYTES} byte cap; nothing was snapshotted")
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
