#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ArcheAxis vNext web worker: bounded snapshot fetch (F02 network part).

Fetches one HTTP(S) URL with strict bounds (timeout, byte cap, redirect
chain tracking), writes the final HTML snapshot plus a fetch receipt into
the caller-provided out-dir, and returns the final URL and status. Network
failure never fabricates a snapshot: the error is recorded and returned.

`--render` adds the F03 lane on top of that fetch: the same URL is opened in a
local browser, scrolled to the bottom within a stated budget, and the DOM and
text the scripts produced are written beside the served bytes. A missing
browser is a named refusal - the fetch is never reported as if it had rendered.
Screenshot capture is still not here; ad/noise separation happens in the
extraction lane (worker_html + later trafilatura-grade parsing).

Usage:
    python worker_webpage.py <url> --out-dir <dir>
    python worker_webpage.py <url> --out-dir <dir> --render [--scroll-limit 40]
    python worker_webpage.py --probe
"""

from __future__ import annotations

import argparse
import hashlib
import ipaddress
import json
import os
import socket
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

ENGINE = "python-worker-webpage"
ENGINE_VERSION = "0.2.0"

TIMEOUT_S = 20
MAX_BYTES = 5 * 1024 * 1024
MAX_REDIRECTS = 8
RENDER_SCROLL_LIMIT = 40
RENDER_SETTLE_MS = 250
RENDER_NAV_TIMEOUT_MS = 30_000
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
    try:
        import playwright  # noqa: F401 - presence is the question
        driver = "installed"
    except ImportError:
        driver = "missing"
    return {
        "capability": True,
        "engine": ENGINE,
        "params": {
            "timeout_s": TIMEOUT_S,
            "max_bytes": MAX_BYTES,
            "max_redirects": MAX_REDIRECTS,
            "scroll_limit": RENDER_SCROLL_LIMIT,
        },
        "engines": {"playwright": driver == "installed"},
        "note": (
            "bounded fetch always; the render lane needs playwright (here: "
            f"{driver}) and a chromium build it can launch, which is only established by an actual "
            "render; screenshots are not taken by this worker"
        ),
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


def _browser():
    """Start the local browser the render lane needs, or name the missing part.

    Playwright and the browser it drives are both host-side: the package may not be installed and
    the browser may never have been downloaded. Either way this is a stated refusal, and the caller
    must not quietly be handed the served-bytes snapshot instead, because "what the page looks like
    after its scripts ran" and "what the server sent" are different facts.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError(
            f"render engine missing: playwright could not be imported ({exc}). "
            "The bounded fetch still works and is not a render."
        ) from exc
    try:
        session = sync_playwright().start()
    except Exception as exc:  # noqa: BLE001 - the driver's own startup error is the message
        raise RuntimeError(f"render engine missing: playwright could not start ({str(exc)[:200]})") from exc
    launch_options: dict = {"headless": True}
    configured = os.environ.get("ARCHEAXIS_CHROMIUM_CMD", "").strip()
    if configured:
        # a browser build elsewhere on this host, named rather than guessed: Playwright only looks
        # under its own registry, and a project-local cache that never ran `playwright install`
        # has nothing in it
        if not Path(configured).is_file():
            session.stop()
            raise RuntimeError(
                f"render engine missing: ARCHEAXIS_CHROMIUM_CMD names a file that does not exist "
                f"({configured})"
            )
        launch_options["executable_path"] = configured
    try:
        browser = session.chromium.launch(**launch_options)
    except Exception as exc:  # noqa: BLE001 - a browser that will not launch is the finding
        session.stop()
        raise RuntimeError(
            "render engine missing: chromium could not be launched ("
            f"{str(exc)[:200]}; PLAYWRIGHT_BROWSERS_PATH="
            f"{os.environ.get('PLAYWRIGHT_BROWSERS_PATH', 'unset')}, "
            f"ARCHEAXIS_CHROMIUM_CMD={configured or 'unset'})"
        ) from exc
    return session, browser


def scroll_to_bottom(page, scroll_limit: int) -> dict:
    """Scroll a page by viewports until its height stops growing, or the budget runs out.

    A lazy-loading list grows as it is scrolled, so "the height no longer changed" is the only
    in-page signal that the whole document has been reached. Running out of budget is reported
    rather than presented as a complete page.
    """
    height = page.evaluate("document.body ? document.body.scrollHeight : 0")
    scrolls = 0
    stabilized = False
    for _ in range(max(0, scroll_limit)):
        page.evaluate("window.scrollBy(0, window.innerHeight)")
        page.wait_for_timeout(RENDER_SETTLE_MS)
        scrolls += 1
        grown = page.evaluate("document.body ? document.body.scrollHeight : 0")
        if grown == height:
            stabilized = True
            break
        height = grown
    return {
        "scrolls": scrolls,
        "scroll_limit": scroll_limit,
        "final_scroll_height": height,
        "height_stabilized": stabilized,
        "budget_exhausted": not stabilized,
    }


def render(url: str, out_dir: Path, *, scroll_limit: int = RENDER_SCROLL_LIMIT) -> dict:
    """Fetch the served bytes, then read the page again through a local browser.

    The address policy runs three times on purpose: before the fetch, before the browser
    navigates, and on the URL the browser actually landed on. A redirect can move a page from an
    allowed host to a forbidden one, and a browser follows redirects without asking this worker.
    """
    served = fetch(url, out_dir)
    parts = urlparse(url)
    public_addresses(parts.hostname or "")
    landing = urlparse(served["final_url"])
    public_addresses(landing.hostname or "")

    session, browser = _browser()
    try:
        page = browser.new_page(user_agent=USER_AGENT)
        page.goto(url, timeout=RENDER_NAV_TIMEOUT_MS, wait_until="load")
        landed = urlparse(page.url)
        if landed.hostname != landing.hostname:
            public_addresses(landed.hostname or "")
        coverage = scroll_to_bottom(page, scroll_limit)
        title = page.title()
        text = page.inner_text("body")
        dom = page.content()
        browser_version = browser.version
    finally:
        browser.close()
        session.stop()

    body = dom.encode("utf-8")
    if len(body) > MAX_BYTES:
        raise ValueError(
            f"rendered DOM exceeded the {MAX_BYTES} byte cap; nothing was written from the render")

    rendered_path = out_dir / "rendered.html"
    text_path = out_dir / "rendered-text.txt"
    rendered_path.write_bytes(body)
    text_path.write_text(text, encoding="utf-8")
    rendered_sha = _sha256(rendered_path)
    rendered_at = datetime.now(timezone.utc).isoformat()
    difference = {
        "served_bytes": served["snapshot"]["bytes"],
        "rendered_bytes": len(body),
        "same_digest": served["snapshot"]["sha256"] == rendered_sha,
    }

    losses = [
        "the render is what this browser build read of the page at this moment: content behind a "
        "click, a login, or an interaction the scroll budget did not reach is not captured, and a "
        "feed that reloads older items would have moved rather than been collected",
        "screenshot capture is not part of this lane, so nothing here is a picture of the page",
        "the served document and the rendered document are reported separately; the render does "
        "not replace the bytes that were actually sent",
    ]
    return {
        "engine": ENGINE,
        "engine_version": ENGINE_VERSION,
        "final_url": served["final_url"],
        "http_status": served["http_status"],
        "title": title,
        "snapshot": served["snapshot"],
        "rendered": {
            "path": str(rendered_path),
            "text_path": str(text_path),
            "sha256": rendered_sha,
            "bytes": len(body),
            "text_chars": len(text),
            "rendered_at": rendered_at,
        },
        "fetched_at": served["fetched_at"],
        "loss_receipt": {
            "engine": ENGINE,
            "engine_version": ENGINE_VERSION,
            "params": {
                "browser": f"chromium {browser_version}",
                "headless": True,
                "scroll": coverage,
                "timeout_s": TIMEOUT_S,
                "max_bytes": MAX_BYTES,
                "served_sha256": served["snapshot"]["sha256"],
                "served_vs_rendered": difference,
            },
            "losses": losses,
            "loss_note": "; ".join(losses),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="ArcheAxis bounded webpage snapshot worker")
    parser.add_argument("url", nargs="?", help="http(s) URL")
    parser.add_argument("--out-dir", required=False)
    parser.add_argument("--probe", action="store_true")
    parser.add_argument("--render", action="store_true",
                        help="render the page in a local browser after the bounded fetch")
    parser.add_argument("--scroll-limit", type=int, default=RENDER_SCROLL_LIMIT)
    args = parser.parse_args()
    if args.probe:
        print(json.dumps(probe(), ensure_ascii=False))
        return 0
    if not args.url or not args.out_dir:
        print(json.dumps({"error": "usage: worker_webpage.py <url> --out-dir <dir>"}))
        return 2
    try:
        out = render(args.url, Path(args.out_dir), scroll_limit=args.scroll_limit) if args.render \
            else fetch(args.url, Path(args.out_dir))
    except Exception as exc:  # noqa: BLE001 - network failures are recorded errors
        # distinguish capability/usage failures from fetch failures: fetch
        # failures already wrote a receipt with error; report structured error.
        print(json.dumps({"error": str(exc), "recorded": "fetch-receipt.json"}, ensure_ascii=False))
        return 1
    print(json.dumps(out, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
