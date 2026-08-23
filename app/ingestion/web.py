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
from datetime import datetime, timezone
from typing import Any, Callable
from urllib.parse import urlsplit

from app.ingestion.raw_asset import RawAssetStore, RawAssetStoreError
from shared.safe_http import SafeHTTPError, SafeHTTPPolicy, SafeHTTPResponse, fetch

RawFetcher = Callable[[str, SafeHTTPPolicy], SafeHTTPResponse]


class WebCaptureError(ValueError):
    """Raised when web capture is invalid or blocked by policy."""


@dataclass(frozen=True)
class CaptureReceipt:
    url: str
    final_url: str
    status: int
    raw_bytes: int
    text_chars: int
    engine: str
    raw_hash: str
    captured_at: str
    content_type: str
    etag: str | None
    last_modified: str | None

    def as_dict(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "final_url": self.final_url,
            "status": self.status,
            "raw_bytes": self.raw_bytes,
            "text_chars": self.text_chars,
            "engine": self.engine,
            "raw_hash": self.raw_hash,
            "captured_at": self.captured_at,
            "content_type": self.content_type,
            "etag": self.etag,
            "last_modified": self.last_modified,
        }


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


def _extract_saved_html(raw: bytes) -> tuple[str, str]:
    """Extract from an already captured response without another network call."""
    html = raw.decode("utf-8", errors="replace")
    try:
        import trafilatura

        text = trafilatura.extract(html, output_format="markdown")
        if text:
            return text, "safe-http+trafilatura"
    except Exception:  # noqa: BLE001 - optional extractor must degrade to retained raw HTML
        # Optional extraction must not make a successfully captured original
        # disappear or turn the intake into a false success claim.
        pass
    return html, "safe-http+raw"


def capture_web(
    url: str,
    *,
    policy: SafeHTTPPolicy | None = None,
    raw_fetcher: RawFetcher | None = None,
    raw_store: RawAssetStore | None = None,
) -> dict[str, Any]:
    """Raw-first web capture: validate → fetch → save raw → extract text.

    Args:
        url: http(s) URL.
        policy: SafeHTTP bounds (default: 2 MB, 15s, ports 80/443).
        raw_fetcher: injectable fetcher for tests (default: safe_http.fetch).
        raw_store: content-addressed original store (default: project runtime store).

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
    response_headers = {str(key).lower(): str(value) for key, value in response.headers.items()}
    content_type = response_headers.get("content-type", "").split(";", 1)[0].strip().lower()
    if policy.allowed_content_types and content_type not in policy.allowed_content_types:
        raise WebCaptureError(f"content type not allowed: {content_type}")

    from hashlib import sha256
    raw_hash = sha256(raw).hexdigest()
    final_url = str(getattr(response, "url", target))
    try:
        original = (raw_store or RawAssetStore()).store_original(
            raw,
            final_url,
            mime_type=content_type,
        )
    except RawAssetStoreError as exc:
        raise WebCaptureError(f"could not preserve raw response: {exc}") from exc
    if original.sha256 != raw_hash:
        raise WebCaptureError("raw response hash mismatch after preservation")

    text, engine = _extract_saved_html(raw)
    loss_report = (
        {
            "status": "degraded",
            "warnings": ["content extraction unavailable; raw HTML retained"],
        }
        if engine == "safe-http+raw"
        else {
            "status": "not_assessed",
            "warnings": ["HTML extraction loss has not been structurally assessed"],
        }
    )

    import base64
    return {
        "receipt": CaptureReceipt(
            url=target,
            final_url=final_url,
            status=response.status,
            raw_bytes=len(raw),
            text_chars=len(text),
            engine=engine,
            raw_hash=raw_hash,
            captured_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            content_type=content_type,
            etag=response_headers.get("etag"),
            last_modified=response_headers.get("last-modified"),
        ).as_dict(),
        "raw": base64.b64encode(raw).decode("ascii"),
        "text": text,
        "loss_report": loss_report,
        "policy": {"max_bytes": policy.max_bytes, "timeout": policy.timeout},
    }


def ingest_web(url: str) -> dict[str, Any]:
    """Compatibility entry: raw-first capture with default policy."""
    return capture_web(url)
