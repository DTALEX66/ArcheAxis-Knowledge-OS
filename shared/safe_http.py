"""Fail-closed HTTP fetch primitive for user-influenced URLs.

The module intentionally owns only network policy and bounded transport. Callers
must provide an explicit content-type policy for their response format; domain
logic remains in the caller.
"""

from __future__ import annotations

import http.client
import ipaddress
import queue
import socket
import ssl
import threading
import time
from collections.abc import Mapping
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlsplit


class SafeHTTPError(ValueError):
    """Raised when a URL or response violates the Safe HTTP policy."""


@dataclass(frozen=True)
class SafeHTTPPolicy:
    """Bounded policy shared by all Safe HTTP callers."""

    timeout: float = 15.0
    max_bytes: int = 2_000_000
    max_redirects: int = 3
    allowed_ports: tuple[int, ...] = (80, 443)
    allowed_content_types: tuple[str, ...] = (
        "application/atom+xml",
        "application/json",
        "application/octet-stream",
        "application/rss+xml",
        "application/xml",
        "text/html",
        "text/plain",
        "text/xml",
    )
    allowed_hosts: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not 0 < self.timeout <= 60:
            raise ValueError("timeout must be between 0 and 60 seconds")
        if self.max_bytes <= 0:
            raise ValueError("max_bytes must be positive")
        if not 0 <= self.max_redirects <= 10:
            raise ValueError("max_redirects must be between 0 and 10")
        if not self.allowed_ports or any(port not in range(1, 65536) for port in self.allowed_ports):
            raise ValueError("allowed_ports must contain valid ports")


@dataclass(frozen=True)
class SafeHTTPResponse:
    """Bounded response returned after all response policies pass."""

    url: str
    status: int
    headers: Mapping[str, str]
    body: bytes


class _DeadlineSendMixin:
    _deadline: float

    def send(self, data):
        if self.sock is not None:
            remaining = self._deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("HTTP total timeout exceeded")
            self.sock.settimeout(remaining)
        return super().send(data)


class _PinnedHTTPConnection(_DeadlineSendMixin, http.client.HTTPConnection):
    def __init__(self, hostname: str, address: str, port: int, timeout: float, deadline: float) -> None:
        super().__init__(hostname, port=port, timeout=timeout)
        self._address = address
        self._deadline = deadline

    def connect(self) -> None:
        self.sock = socket.create_connection((self._address, self.port), self.timeout)


class _PinnedHTTPSConnection(_DeadlineSendMixin, http.client.HTTPSConnection):
    def __init__(self, hostname: str, address: str, port: int, timeout: float, deadline: float) -> None:
        super().__init__(hostname, port=port, timeout=timeout)
        self._address = address
        self._deadline = deadline

    def connect(self) -> None:
        remaining = self._deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("HTTP total timeout exceeded")
        self.sock = socket.create_connection((self._address, self.port), remaining)
        self.sock.settimeout(remaining)
        self.sock = self._context.wrap_socket(self.sock, server_hostname=self._tunnel_host or self.host)
        remaining = self._deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("HTTP total timeout exceeded")
        self.sock.settimeout(remaining)


def _resolve_addresses(hostname: str, timeout: float | None = None) -> list[str]:
    result: queue.Queue[tuple[list[tuple], BaseException | None]] = queue.Queue(maxsize=1)

    def resolve() -> None:
        try:
            result.put((socket.getaddrinfo(hostname, None, type=socket.SOCK_STREAM), None))
        except BaseException as exc:  # propagate resolver failures to caller
            result.put(([], exc))

    worker = threading.Thread(target=resolve, daemon=True)
    worker.start()
    worker.join(timeout)
    if worker.is_alive():
        raise SafeHTTPError(f"DNS resolution timed out for {hostname}")
    infos, error = result.get_nowait()
    if error is not None:
        if isinstance(error, OSError):
            raise SafeHTTPError(f"DNS resolution failed for {hostname}") from error
        raise error

    if not infos:
        raise SafeHTTPError(f"DNS resolution returned no addresses for {hostname}")
    addresses: list[str] = []
    for info in infos:
        address = info[4][0]
        if address not in addresses:
            addresses.append(address)
    if not addresses:
        raise SafeHTTPError(f"DNS resolution returned no addresses for {hostname}")
    return addresses


def _validate_address(address: str) -> None:
    try:
        parsed = ipaddress.ip_address(address)
    except ValueError as exc:
        raise SafeHTTPError(f"invalid resolved address: {address}") from exc

    # is_global excludes private, loopback, link-local, multicast, unspecified,
    # reserved and documentation-only ranges. Explicitly name metadata for the
    # security contract because it is a high-signal SSRF target.
    if address == "169.254.169.254" or not parsed.is_global:
        raise SafeHTTPError(f"blocked address: {address}")


def _validate_url(url: str, policy: SafeHTTPPolicy) -> tuple[object, str, int]:
    try:
        parsed = urlsplit(url)
        port = parsed.port
    except ValueError as exc:
        raise SafeHTTPError("invalid URL port") from exc

    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
        raise SafeHTTPError("URL must be an absolute http(s) URL without credentials")
    port = port or (443 if parsed.scheme == "https" else 80)
    if port not in policy.allowed_ports:
        raise SafeHTTPError(f"blocked port: {port}")
    hostname = parsed.hostname.rstrip(".").lower()
    if policy.allowed_hosts and hostname not in {host.lower().rstrip(".") for host in policy.allowed_hosts}:
        raise SafeHTTPError(f"host is not allowlisted: {hostname}")
    return parsed, hostname, port


def _read_bounded(response: http.client.HTTPResponse, max_bytes: int) -> bytes:
    body = response.read(max_bytes + 1)
    if len(body) > max_bytes:
        raise SafeHTTPError(f"response exceeds {max_bytes} bytes")
    return body


def _call_with_deadline(function, deadline: float):
    result: queue.Queue[tuple[object | None, BaseException | None]] = queue.Queue(maxsize=1)

    def invoke() -> None:
        try:
            result.put((function(), None))
        except BaseException as exc:
            result.put((None, exc))

    worker = threading.Thread(target=invoke, daemon=True)
    worker.start()
    worker.join(max(0.0, deadline - time.monotonic()))
    if worker.is_alive():
        raise SafeHTTPError("HTTP total timeout exceeded")
    value, error = result.get_nowait()
    if error is not None:
        raise error
    return value


def _open_once(
    url: str,
    *,
    method: str,
    body: bytes | None,
    resolved_ip: str,
    timeout: float,
    deadline: float,
    headers: Mapping[str, str],
    max_bytes: int,
) -> SafeHTTPResponse:
    parsed = urlsplit(url)
    hostname = parsed.hostname or ""
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    path = parsed.path or "/"
    if parsed.query:
        path += f"?{parsed.query}"

    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise SafeHTTPError("HTTP total timeout exceeded")
    connection_timeout = min(timeout, remaining)
    connection: http.client.HTTPConnection
    if parsed.scheme == "https":
        connection = _PinnedHTTPSConnection(hostname, resolved_ip, port, connection_timeout, deadline)
    else:
        connection = _PinnedHTTPConnection(hostname, resolved_ip, port, connection_timeout, deadline)
    try:
        _call_with_deadline(
            lambda: connection.request(method, path, body=body, headers=dict(headers)),
            deadline,
        )
        response = _call_with_deadline(connection.getresponse, deadline)
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise SafeHTTPError("HTTP total timeout exceeded")
        raw_socket = getattr(getattr(getattr(response, "fp", None), "raw", None), "_sock", None)
        if raw_socket is not None:
            raw_socket.settimeout(remaining)
        response_headers = {key.lower(): value for key, value in response.getheaders()}
        body = _call_with_deadline(lambda: _read_bounded(response, max_bytes), deadline)
        return SafeHTTPResponse(
            url=url,
            status=response.status,
            headers=response_headers,
            body=body,
        )
    except SafeHTTPError:
        raise
    except (OSError, http.client.HTTPException, ssl.SSLError) as exc:
        raise SafeHTTPError(f"HTTP request failed for {url}") from exc
    finally:
        connection.close()


def _content_type(headers: Mapping[str, str]) -> str:
    return headers.get("content-type", "").split(";", 1)[0].strip().lower()


def fetch(
    url: str,
    *,
    method: str = "GET",
    body: bytes | None = None,
    policy: SafeHTTPPolicy | None = None,
    headers: Mapping[str, str] | None = None,
) -> SafeHTTPResponse:
    """Fetch one bounded HTTP response with fail-closed SSRF protections."""
    active_policy = policy or SafeHTTPPolicy()
    method = method.upper()
    if method not in {"GET", "POST"}:
        raise SafeHTTPError(f"HTTP method not allowed: {method}")
    request_headers = {
        "Accept": ", ".join(active_policy.allowed_content_types),
        "User-Agent": "Cognitive-Loop-OS/SafeHTTP",
    }
    if headers:
        request_headers.update(headers)

    current_url = url
    deadline = time.monotonic() + active_policy.timeout
    for redirect_count in range(active_policy.max_redirects + 1):
        parsed, hostname, _port = _validate_url(current_url, active_policy)
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise SafeHTTPError("HTTP total timeout exceeded")
        addresses = _resolve_addresses(hostname, timeout=remaining)
        for address in addresses:
            _validate_address(address)

        response = _open_once(
            current_url,
            method=method,
            body=body,
            resolved_ip=addresses[0],
            timeout=active_policy.timeout,
            deadline=deadline,
            headers=request_headers,
            max_bytes=active_policy.max_bytes,
        )
        if len(response.body) > active_policy.max_bytes:
            raise SafeHTTPError(f"response exceeds {active_policy.max_bytes} bytes")
        if response.status in {301, 302, 303, 307, 308}:
            location = response.headers.get("location", "").strip()
            if not location:
                raise SafeHTTPError("redirect response has no Location")
            if redirect_count >= active_policy.max_redirects:
                raise SafeHTTPError("redirect limit exceeded")
            if response.status in {301, 302, 303} and method == "POST":
                method = "GET"
                body = None
            current_url = urljoin(current_url, location)
            continue

        if not 200 <= response.status < 300:
            raise SafeHTTPError(f"HTTP status {response.status}")
        media_type = _content_type(response.headers)
        if media_type not in {item.lower() for item in active_policy.allowed_content_types}:
            raise SafeHTTPError(f"Content-Type not allowed: {media_type or 'missing'}")
        return response

    raise SafeHTTPError("redirect limit exceeded")
