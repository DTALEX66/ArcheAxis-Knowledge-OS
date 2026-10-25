"""Public-research-only HTTP CONNECT via a validated loopback HTTP proxy.

An explicit setting wins; Windows may reuse its enabled current-user literal proxy.
No PAC execution, credentials, generic proxy environment, redirects, or TLS bypass.
This module accepts only the three fixed public GET endpoints owned by this worker.
"""
from __future__ import annotations

from http import client as http_client
import ipaddress
import re
import socket
import ssl
import sys
import time
from urllib.parse import urlsplit

TARGETS = {"en.wikipedia.org": "/w/api.php", "api.stackexchange.com": "/2.3/search/advanced",
           "api.openalex.org": "/works"}
CONNECT_LIMIT = 8192
HEADER_LIMIT = 16384


class ProxyFailure(ValueError):
    def __init__(self, code):
        super().__init__(code)
        self.code = code


def _proxy(value):
    try:
        if not isinstance(value, str) or not 1 <= len(value) <= 128 \
                or any(ord(c) < 33 or ord(c) > 126 for c in value):
            raise ValueError()
        parsed = urlsplit(value)
        if parsed.scheme != "http" or not parsed.hostname or parsed.username is not None \
                or parsed.password is not None or parsed.path or parsed.query or parsed.fragment \
                or parsed.port is None or not 1 <= parsed.port <= 65535 \
                or "?" in value or "#" in value or "%" in parsed.hostname:
            raise ValueError()
        address = ipaddress.ip_address(parsed.hostname)
        if not address.is_loopback:
            raise ValueError()
        return str(address), parsed.port
    except (ValueError, TypeError):
        raise ProxyFailure("proxy_config_invalid") from None


def _registered_proxy(value):
    """Parse only a literal WinINet proxy; HTTPS mappings do not inherit HTTP-only ones."""
    if not isinstance(value, str) or not 1 <= len(value) <= 2048 \
            or any(ord(c) < 33 or ord(c) > 126 for c in value):
        return None
    if "=" in value:
        mappings = {}
        for item in value.split(";"):
            parts = item.split("=")
            if len(parts) != 2 or parts[0].lower() not in {"http", "https", "ftp", "socks"} \
                    or parts[0].lower() in mappings or not parts[1]:
                return None
            mappings[parts[0].lower()] = parts[1]
        value = mappings.get("https")
        if value is None:
            return None
    candidate = value if "://" in value else "http://" + value
    try:
        _proxy(candidate)
        return candidate
    except ProxyFailure:
        return None


def _windows_proxy():
    """Read two exact network values, never run PAC or change Windows configuration."""
    if sys.platform != "win32":
        return None
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Internet Settings",
                0, winreg.KEY_QUERY_VALUE) as key:
            enabled, kind = winreg.QueryValueEx(key, "ProxyEnable")
            if kind != winreg.REG_DWORD or enabled != 1:
                return None
            value, kind = winreg.QueryValueEx(key, "ProxyServer")
            return _registered_proxy(value) if kind == winreg.REG_SZ else None
    except (ImportError, OSError, ValueError, TypeError, AttributeError):
        return None


def select_proxy(setting):
    """Resolve once per public request. Explicit invalid/empty settings fail closed."""
    if setting is not None:
        if setting == "direct":
            return None
        _proxy(setting)
        return setting
    return _windows_proxy()


def _remaining(deadline):
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise ProxyFailure("proxy_timeout")
    return remaining


def _connect_response(sock, deadline):
    # Read exactly through the header terminator. Never consume TLS bytes into a
    # buffered CONNECT parser; refuse unexpected body framing before TLS starts.
    raw = bytearray()
    while not raw.endswith(b"\r\n\r\n"):
        if len(raw) >= CONNECT_LIMIT:
            raise ProxyFailure("proxy_connect_limit")
        sock.settimeout(_remaining(deadline))
        byte = sock.recv(1)
        if not byte:
            raise ProxyFailure("proxy_connect_failed")
        raw.extend(byte)
    try:
        lines = bytes(raw).decode("ascii").split("\r\n")
        if not re.fullmatch(r"HTTP/1\.[01] 200(?: [\x20-\x7e]*)?", lines[0]):
            raise ValueError()
        seen = set()
        for line in lines[1:-2]:
            name, value = line.split(":", 1)
            if not re.fullmatch(r"[!#$%&'*+.^_`|~0-9A-Za-z-]+", name) or name.lower() in seen:
                raise ValueError()
            seen.add(name.lower())
            if any((ord(c) < 32 and c != "\t") or ord(c) == 127 for c in value):
                raise ValueError()
            if name.lower() == "transfer-encoding" or (name.lower() == "content-length" and value.strip() != "0"):
                raise ValueError()
    except (UnicodeError, ValueError):
        raise ProxyFailure("proxy_connect_failed") from None


class _LimitedHeaders:
    """Bound all HTTP header/chunk/trailer lines in aggregate as well as body bytes."""
    def __init__(self, stream, sock, deadline):
        self.stream, self.sock, self.deadline = stream, sock, deadline
        self.used = 0

    def readline(self, limit=-1):
        self.sock.settimeout(_remaining(self.deadline))
        available = HEADER_LIMIT - self.used + 1
        if available <= 0:
            raise ProxyFailure("proxy_response_limit")
        line = self.stream.readline(min(limit, available) if limit >= 0 else available)
        self.used += len(line)
        if self.used > HEADER_LIMIT:
            raise ProxyFailure("proxy_response_limit")
        return line

    def read(self, count=-1):
        self.sock.settimeout(_remaining(self.deadline))
        return self.stream.read(count)

    def close(self):
        self.stream.close()

    def flush(self):
        # HTTPResponse.close calls flush on its read-only stream. No writes exist.
        pass


class _ResponseSocket:
    def __init__(self, sock, deadline):
        self.sock, self.deadline = sock, deadline

    def makefile(self, mode):
        return _LimitedHeaders(self.sock.makefile(mode), self.sock, self.deadline)


def fetch(url, *, proxy_url, policy, headers, http):
    """One finite fixed-host HTTPS GET. Invalid proxy settings never fall back direct."""
    proxy_address = _proxy(proxy_url)
    try:
        target = urlsplit(url)
        host = target.hostname
        if len(url) > 12288 or target.scheme != "https" or host not in TARGETS or target.path != TARGETS[host] \
                or target.port not in (None, 443) or target.username is not None \
                or target.password is not None or target.fragment \
                or any(ord(c) < 33 or ord(c) > 126 for c in url) \
                or not 0 < policy.timeout <= 12 or not 0 < policy.max_bytes <= 131072 \
                or policy.max_redirects != 0 or policy.allowed_ports != (443,) \
                or policy.allowed_hosts != (host,) or policy.allowed_content_types != ("application/json",):
            raise ValueError()
        for name, value in headers.items():
            if name.lower() not in {"accept", "user-agent"} or not isinstance(value, str) \
                    or any(ord(c) < 32 or ord(c) > 126 for c in value) or len(value) > 512:
                raise ValueError()
    except (ValueError, TypeError, AttributeError):
        raise ProxyFailure("proxy_target_invalid") from None

    deadline = time.monotonic() + policy.timeout
    sock, tls, response = None, None, None
    try:
        sock = socket.create_connection(proxy_address, timeout=_remaining(deadline))
        sock.settimeout(_remaining(deadline))
        sock.sendall(f"CONNECT {host}:443 HTTP/1.1\r\nHost: {host}:443\r\n\r\n".encode("ascii"))
        _connect_response(sock, deadline)
        context = ssl.create_default_context()
        if context.verify_mode != ssl.CERT_REQUIRED or not context.check_hostname:
            raise ProxyFailure("proxy_tls_failed")
        sock.settimeout(_remaining(deadline))
        tls = context.wrap_socket(sock, server_hostname=host)
        tls.settimeout(_remaining(deadline))
        path = target.path + ("?" + target.query if target.query else "")
        request = f"GET {path} HTTP/1.1\r\nHost: {host}\r\nConnection: close\r\n"
        request += "".join(f"{name}: {value}\r\n" for name, value in headers.items()) + "\r\n"
        http._call_with_deadline(lambda: tls.sendall(request.encode("ascii")), deadline)
        response = http_client.HTTPResponse(_ResponseSocket(tls, deadline))
        http._call_with_deadline(response.begin, deadline)
        response_headers = {name.lower(): value for name, value in response.getheaders()}
        # Distinct/duplicate framing values must not select an ambiguous response body.
        if len(response.headers.get_all("content-length", [])) > 1 \
                or len(response.headers.get_all("transfer-encoding", [])) > 1 \
                or (response.headers.get("content-length") is not None and response.headers.get("transfer-encoding") is not None):
            raise ProxyFailure("proxy_response_invalid")
        body = http._call_with_deadline(lambda: response.read(policy.max_bytes + 1), deadline)
        if len(body) > policy.max_bytes:
            raise ProxyFailure("proxy_response_limit")
        if not 200 <= response.status < 300:
            raise http.SafeHTTPStatusError(response.status, response_headers)
        content_type = response_headers.get("content-type", "").split(";", 1)[0].strip().lower()
        if content_type not in policy.allowed_content_types:
            raise ProxyFailure("proxy_response_invalid")
        return http.SafeHTTPResponse(url=url, status=response.status, headers=response_headers, body=body)
    except ProxyFailure:
        raise
    except ssl.SSLError:
        raise ProxyFailure("proxy_tls_failed") from None
    except TimeoutError:
        raise ProxyFailure("proxy_timeout") from None
    except http.SafeHTTPStatusError:
        raise
    except http.SafeHTTPError:
        raise ProxyFailure("proxy_timeout") from None
    except (OSError, http_client.HTTPException, ValueError):
        raise ProxyFailure("proxy_transport_failed") from None
    finally:
        if response is not None:
            response.close()
        if tls is not None:
            tls.close()
        if sock is not None:
            sock.close()
