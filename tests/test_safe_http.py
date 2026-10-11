from __future__ import annotations

from types import SimpleNamespace

import pytest

from shared.safe_http import SafeHTTPError, SafeHTTPPolicy, fetch


def test_rejects_private_and_loopback_targets_before_open(monkeypatch):
    opened = False

    def fail_open(*args, **kwargs):
        nonlocal opened
        opened = True
        raise AssertionError("network must not open")

    monkeypatch.setattr("shared.safe_http._open_once", fail_open)

    for url in (
        "http://127.0.0.1/health",
        "http://10.0.0.8/internal",
        "http://192.168.1.10/router",
        "http://169.254.169.254/latest/meta-data",
        "http://224.0.0.1/",
        "http://239.255.255.250/",
        "http://[ff02::1]/",
    ):
        with pytest.raises(SafeHTTPError, match="blocked address"):
            fetch(url)

    assert not opened


def test_rejects_non_http_credentials_and_unsafe_ports():
    for url in (
        "file:///etc/passwd",
        "ftp://example.com/file",
        "https://user:pass@example.com/private",
        "https://example.com:8443/api",
    ):
        with pytest.raises(SafeHTTPError):
            fetch(url)


def test_rejects_dns_resolution_with_any_blocked_result(monkeypatch):
    monkeypatch.setattr(
        "shared.safe_http._resolve_addresses",
        lambda hostname, **kwargs: ["93.184.216.34", "192.168.1.4"],
    )

    with pytest.raises(SafeHTTPError, match="blocked address"):
        fetch("https://example.com/")


def test_dns_resolution_has_total_timeout(monkeypatch):
    import time

    def slow_getaddrinfo(*args, **kwargs):
        time.sleep(0.05)
        return []

    monkeypatch.setattr("shared.safe_http.socket.getaddrinfo", slow_getaddrinfo)
    with pytest.raises(SafeHTTPError, match="DNS resolution timed out"):
        fetch("https://example.com/", policy=SafeHTTPPolicy(timeout=0.01))


def test_revalidates_each_redirect(monkeypatch):
    monkeypatch.setattr(
        "shared.safe_http._resolve_addresses",
        lambda hostname, **kwargs: ["93.184.216.34"] if hostname == "example.com" else ["127.0.0.1"],
    )
    monkeypatch.setattr(
        "shared.safe_http._open_once",
        lambda *args, **kwargs: SimpleNamespace(
            status=302,
            headers={"location": "https://internal.example/secret"},
            body=b"",
        ),
    )

    with pytest.raises(SafeHTTPError, match="blocked address"):
        fetch("https://example.com/start")


def test_stops_stream_when_response_exceeds_byte_limit(monkeypatch):
    monkeypatch.setattr("shared.safe_http._resolve_addresses", lambda hostname, **kwargs: ["93.184.216.34"])
    monkeypatch.setattr(
        "shared.safe_http._open_once",
        lambda *args, **kwargs: SimpleNamespace(
            status=200,
            headers={"content-type": "text/plain"},
            body=b"0123456789",
        ),
    )

    with pytest.raises(SafeHTTPError, match="response exceeds"):
        fetch("https://example.com/data", policy=SafeHTTPPolicy(max_bytes=5))


def test_rejects_content_type_not_in_explicit_allowlist(monkeypatch):
    monkeypatch.setattr("shared.safe_http._resolve_addresses", lambda hostname, **kwargs: ["93.184.216.34"])
    monkeypatch.setattr(
        "shared.safe_http._open_once",
        lambda *args, **kwargs: SimpleNamespace(
            status=200,
            headers={"content-type": "text/html; charset=utf-8"},
            body=b"<html />",
        ),
    )

    with pytest.raises(SafeHTTPError, match="Content-Type"):
        fetch(
            "https://example.com/data",
            policy=SafeHTTPPolicy(allowed_content_types=("application/json",)),
        )


def test_passes_bounded_timeout_to_transport(monkeypatch):
    monkeypatch.setattr("shared.safe_http._resolve_addresses", lambda hostname, **kwargs: ["93.184.216.34"])
    captured = {}

    def fake_open(*args, **kwargs):
        captured.update(kwargs)
        return SimpleNamespace(
            status=200,
            headers={"content-type": "application/json"},
            body=b"{}",
        )

    monkeypatch.setattr("shared.safe_http._open_once", fake_open)
    result = fetch(
        "https://example.com/data",
        policy=SafeHTTPPolicy(timeout=3.5, allowed_content_types=("application/json",)),
    )

    assert result.status == 200
    assert captured["timeout"] == 3.5


def test_post_redirect_303_switches_to_get_and_drops_body(monkeypatch):
    monkeypatch.setattr("shared.safe_http._resolve_addresses", lambda hostname, **kwargs: ["93.184.216.34"])
    requests = []
    responses = iter(
        [
            SimpleNamespace(status=303, headers={"location": "/next"}, body=b""),
            SimpleNamespace(status=200, headers={"content-type": "text/plain"}, body=b"ok"),
        ]
    )

    def fake_open(url, **kwargs):
        requests.append((url, kwargs["method"], kwargs["body"], kwargs["deadline"]))
        return next(responses)

    monkeypatch.setattr("shared.safe_http._open_once", fake_open)
    result = fetch(
        "https://example.com/start",
        method="POST",
        body=b"payload",
        policy=SafeHTTPPolicy(allowed_content_types=("text/plain",)),
    )

    assert result.body == b"ok"
    assert [(method, body) for _, method, body, _ in requests] == [
        ("POST", b"payload"),
        ("GET", None),
    ]
    assert requests[0][3] == requests[1][3]


def test_transport_receives_total_deadline(monkeypatch):
    monkeypatch.setattr("shared.safe_http._resolve_addresses", lambda hostname, **kwargs: ["93.184.216.34"])
    captured = {}

    def fake_open(*args, **kwargs):
        captured.update(kwargs)
        return SimpleNamespace(
            status=200,
            headers={"content-type": "text/plain"},
            body=b"ok",
        )

    monkeypatch.setattr("shared.safe_http._open_once", fake_open)
    fetch(
        "https://example.com/data",
        policy=SafeHTTPPolicy(timeout=3.5, allowed_content_types=("text/plain",)),
    )

    assert captured["deadline"] > captured["timeout"]


def test_bounded_reader_rejects_body_without_loading_more_than_limit():
    from shared.safe_http import _read_bounded

    class FakeResponse:
        def __init__(self):
            self.requested = []

        def read(self, size):
            self.requested.append(size)
            return b"x" * size

    response = FakeResponse()
    with pytest.raises(SafeHTTPError, match="response exceeds"):
        _read_bounded(response, 5)
    assert response.requested == [6]


@pytest.mark.parametrize("location,method,body,headers", [
    ("https://other.example/", "POST", b"synthetic-private-material", {}),
    ("https://other.example/", "GET", None, {"Authorization": "synthetic-token"}),
    ("https://other.example/", "GET", None, {"Cookie": "synthetic-session"}),
    ("https://other.example/", "GET", None, {"X-Api-Key": "synthetic-key"}),
    ("http://example.com/", "GET", None, {}),
])
def test_redirect_cannot_expand_sensitive_destination(monkeypatch, location, method, body, headers):
    monkeypatch.setattr("shared.safe_http._resolve_addresses", lambda hostname, **kwargs: ["93.184.216.34"])
    opened = []

    def fake_open(url, **kwargs):
        opened.append(url)
        return SimpleNamespace(status=307, headers={"location": location}, body=b"")

    monkeypatch.setattr("shared.safe_http._open_once", fake_open)
    with pytest.raises(SafeHTTPError, match="redirect"):
        fetch("https://example.com/start", method=method, body=body, headers=headers)
    assert opened == ["https://example.com/start"]


@pytest.mark.parametrize("location,headers", [
    ("https://other.example/public", {}),
    ("/next", {"Authorization": "synthetic-token"}),
])
def test_safe_public_or_same_origin_redirect_remains_available(monkeypatch, location, headers):
    monkeypatch.setattr("shared.safe_http._resolve_addresses", lambda hostname, **kwargs: ["93.184.216.34"])
    opened = []

    def fake_open(url, **kwargs):
        opened.append((url, kwargs["headers"]))
        return SimpleNamespace(status=302, headers={"location": location}, body=b"") if len(opened)==1 else SimpleNamespace(status=200, headers={"content-type": "text/plain"}, body=b"ok")

    monkeypatch.setattr("shared.safe_http._open_once", fake_open)
    assert fetch("https://example.com/start", headers=headers).body == b"ok"
    assert len(opened) == 2
    if headers:
        assert opened[1][1]["Authorization"] == "synthetic-token"
