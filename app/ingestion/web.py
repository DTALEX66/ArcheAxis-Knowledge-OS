"""Raw-first web capture — AXW-WEB-CAPTURE core (replaces the stub).

Raw-first: the original HTML is preserved before any extraction, so evidence
and re-conversion stay possible. Flow:

    validate(url) → fetch raw via SafeHTTP (bounded) → save raw asset
        → convert_url (existing engine chain) for text
        → {url, status, raw_bytes, text, engine, policy}

PolicyGate (C2): scheme http/https, SafeHTTP bounds (ports/bytes/redirects),
content-type text/html, optional host allowlist. Fail-closed.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable
from urllib.parse import urlsplit

from shared.safe_http import SafeHTTPError, SafeHTTPPolicy, SafeHTTPResponse, fetch

RawFetcher = Callable[[str, SafeHTTPPolicy], SafeHTTPResponse]


class WebCaptureError(ValueError):
    """Raised when web capture is invalid or blocked by policy."""


@dataclass(frozen=True)
class CaptureReceipt:
    url: str
    status: int
    raw_bytes: int
    text_chars: int
    engine: str
    raw_hash: str

    def as_dict(self) -> dict[str, Any]:
        return {"url": self.url, "status": self.status, "raw_bytes": self.raw_bytes,
                "text_chars": self.text_chars, "engine": self.engine,
                "raw_hash": self.raw_hash}


def _validate(url: str, policy: SafeHTTPPolicy) -> str:
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"}:
        raise WebCaptureError(f"unsupported scheme: {parsed.scheme or 'none'}")
    hostname = (parsed.hostname or "").casefold()
    if not hostname:
        raise WebCaptureError("URL requires a hostname")
    if policy.allowed_hosts and hostname not in policy.allowed_hosts:
        raise WebCaptureError(f"host not allowed: {hostname}")
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    if policy.allowed_ports and port not in policy.allowed_ports:
        raise WebCaptureError(f"port not allowed: {port}")
    return url


def capture_web(
    url: str,
    *,
    policy: SafeHTTPPolicy | None = None,
    raw_fetcher: RawFetcher | None = None,
) -> dict[str, Any]:
    """Raw-first web capture: validate → fetch → save raw → extract text.

    Args:
        url: http(s) URL.
        policy: SafeHTTP bounds (default: 2 MB, 15s, ports 80/443).
        raw_fetcher: injectable fetcher for tests (default: safe_http.fetch).

    Returns:
        {"receipt": CaptureReceipt.as_dict(), "raw": base64 raw HTML,
         "text": extracted text, "policy": {...}}
    """
    if not url.strip():
        raise WebCaptureError("url is required")
    policy = policy or SafeHTTPPolicy()
    target = _validate(url.strip(), policy)
    fetcher = raw_fetcher or (lambda u, p: fetch(u, policy=p))
    try:
        response: SafeHTTPResponse = fetcher(target, policy)
    except SafeHTTPError as exc:
        raise WebCaptureError(f"fetch blocked by policy: {exc}") from exc
    except Exception as exc:  # noqa: BLE001 — network failures are capture failures
        raise WebCaptureError(f"fetch failed: {exc}") from exc

    raw = bytes(response.body)
    if not raw:
        raise WebCaptureError("empty response body")
    content_type = (response.headers.get("Content-Type") or "").split(";")[0].strip().lower()
    if policy.allowed_content_types and content_type not in policy.allowed_content_types:
        raise WebCaptureError(f"content type not allowed: {content_type}")

    from hashlib import sha256
    raw_hash = sha256(raw).hexdigest()[:16]

    # text extraction reuses the existing engine chain (raw-first, not raw-only)
    from app.ingestion.multi_format import convert_url
    text, engine = convert_url(target)

    import base64
    return {
        "receipt": CaptureReceipt(
            url=target, status=response.status, raw_bytes=len(raw),
            text_chars=len(text), engine=engine, raw_hash=raw_hash,
        ).as_dict(),
        "raw": base64.b64encode(raw).decode("ascii"),
        "text": text,
        "policy": {"max_bytes": policy.max_bytes, "timeout": policy.timeout},
    }


def ingest_web(url: str) -> dict[str, Any]:
    """Compatibility entry: raw-first capture with default policy."""
    return capture_web(url)
