"""Synthetic proxy transport tests; these never contact a real proxy."""
import importlib.util
import io
import ssl
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]


def load(name):
    path = ROOT / "services/python-workers/machine" / (name + ".py")
    spec = importlib.util.spec_from_file_location(name + "_proxy_fixture", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def modules():
    return load("public_research_proxy"), load("public_research")


class Socket:
    def __init__(self, connect=b"HTTP/1.1 200 Connection established\r\n\r\n", origin=b'HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: 14\r\n\r\n{"results":[]}'):
        self.connect = io.BytesIO(connect)
        self.origin = origin
        self.writes = []
        self.closed = False

    def settimeout(self, value):
        assert 0 < value <= 12

    def recv(self, count):
        return self.connect.read(count)

    def sendall(self, value):
        self.writes.append(value)

    def makefile(self, mode):
        assert mode == "rb"
        return io.BytesIO(self.origin)

    def close(self):
        self.closed = True


def wire(monkeypatch, proxy, sock, *, tls_error=None, check_hostname=True):
    calls = []
    def connect(address, timeout):
        calls.append((address, timeout))
        return sock
    def wrap_socket(value, server_hostname):
        assert value is sock and server_hostname == "api.openalex.org"
        if tls_error:
            raise tls_error
        return sock
    monkeypatch.setattr(proxy.socket, "create_connection", connect)
    monkeypatch.setattr(proxy.ssl, "create_default_context", lambda: SimpleNamespace(
        check_hostname=check_hostname, verify_mode=ssl.CERT_REQUIRED, wrap_socket=wrap_socket))
    return calls


def invoke(modules, **changes):
    proxy, worker = modules
    args = dict(proxy_url="http://127.0.0.1:7890", http=worker.http,
        policy=worker.http.SafeHTTPPolicy(timeout=12, max_bytes=131072, max_redirects=0,
            allowed_ports=(443,), allowed_hosts=("api.openalex.org",), allowed_content_types=("application/json",)),
        headers={"Accept": "application/json", "User-Agent": worker.USER_AGENT})
    args.update(changes)
    return proxy.fetch("https://api.openalex.org/works?search=synthetic&per_page=1", **args)


@pytest.mark.parametrize("value", ["http://proxy.example:7890", "http://192.168.1.1:7890",
    "http://user:secret@127.0.0.1:7890", "https://127.0.0.1:7890", "socks5://127.0.0.1:7890",
    "http://localhost:7890", "http://127.0.0.1:7890/", "http://127.0.0.1:7890?q=1",
    "http://127.0.0.1:7890#x", "http://127.0.0.1:0", "http://127.0.0.1", ""])
def test_invalid_proxy_never_connects(modules, monkeypatch, value):
    proxy, _ = modules
    monkeypatch.setattr(proxy.socket, "create_connection", lambda *a, **k: pytest.fail("must not connect"))
    with pytest.raises(proxy.ProxyFailure) as caught:
        invoke(modules, proxy_url=value)
    assert caught.value.code == "proxy_config_invalid"
    assert "secret" not in str(caught.value)


@pytest.mark.parametrize("connect,code", [(b"HTTP/1.1 407 Proxy Authentication Required\r\n\r\n", "proxy_connect_failed"),
    (b"HTTP/1.1 302 Redirect\r\nLocation: http://private\r\n\r\n", "proxy_connect_failed"),
    (b"HTTP/1.1 200 OK\r\nX-Long: " + b"x"*8192 + b"\r\n\r\n", "proxy_connect_limit"),
    (b"HTTP/1.1 200 OK\r\nContent-Length: 3\r\n\r\nBAD", "proxy_connect_failed")])
def test_connect_refusals_are_bounded_and_closed(modules, monkeypatch, connect, code):
    proxy, _ = modules
    sock = Socket(connect=connect)
    wire(monkeypatch, proxy, sock)
    with pytest.raises(proxy.ProxyFailure) as caught:
        invoke(modules)
    assert caught.value.code == code and sock.closed
    assert len(sock.writes) == 1 and sock.writes[0].startswith(b"CONNECT api.openalex.org:443 ")


@pytest.mark.parametrize("error,code", [(ssl.SSLCertVerificationError("wrong origin identity"), "proxy_tls_failed"),
    (TimeoutError("slow handshake"), "proxy_timeout")])
def test_tls_identity_or_timeout_is_never_downgraded(modules, monkeypatch, error, code):
    proxy, _ = modules
    sock = Socket()
    wire(monkeypatch, proxy, sock, tls_error=error)
    with pytest.raises(proxy.ProxyFailure) as caught:
        invoke(modules)
    assert caught.value.code == code and sock.closed and len(sock.writes) == 1


def test_secure_connect_and_tls_origin_keep_raw_body(modules, monkeypatch):
    proxy, _ = modules
    sock = Socket()
    calls = wire(monkeypatch, proxy, sock)
    response = invoke(modules)
    assert calls[0][0] == ("127.0.0.1", 7890)
    assert response.body == b'{"results":[]}' and response.status == 200 and sock.closed
    assert sock.writes[1].startswith(b"GET /works?search=synthetic&per_page=1 HTTP/1.1\r\n")
    assert b"Host: api.openalex.org\r\n" in sock.writes[1]
    assert b"Authorization" not in b"".join(sock.writes)


def test_insecure_tls_context_is_refused(modules, monkeypatch):
    proxy, _ = modules
    sock = Socket()
    wire(monkeypatch, proxy, sock, check_hostname=False)
    with pytest.raises(proxy.ProxyFailure) as caught:
        invoke(modules)
    assert caught.value.code == "proxy_tls_failed"


def test_body_and_origin_headers_have_independent_bounds(modules, monkeypatch):
    proxy, _ = modules
    for origin, code in [(b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n" + b"x"*131073, "proxy_response_limit"),
        (b"HTTP/1.1 200 OK\r\nX-Long: " + b"x"*17000 + b"\r\n\r\n", "proxy_response_limit")]:
        sock = Socket(origin=origin)
        wire(monkeypatch, proxy, sock)
        with pytest.raises(proxy.ProxyFailure) as caught:
            invoke(modules)
        assert caught.value.code == code and sock.closed


def test_origin_redirect_is_not_followed_and_429_retains_retry(modules, monkeypatch):
    proxy, worker = modules
    for status in (302, 429):
        sock = Socket(origin=f"HTTP/1.1 {status} Response\r\nRetry-After: 9\r\nContent-Length: 0\r\n\r\n".encode())
        wire(monkeypatch, proxy, sock)
        with pytest.raises(worker.http.SafeHTTPStatusError) as caught:
            invoke(modules)
        assert caught.value.status_code == status and caught.value.retry_after_seconds == 9
        assert len(sock.writes) == 2 and sock.closed


def test_worker_proxy_is_explicit_and_invalid_config_never_falls_back(modules, monkeypatch):
    proxy, worker = modules
    monkeypatch.setenv("ARCHEAXIS_PUBLIC_RESEARCH_PROXY", "http://user:secret@127.0.0.1:7890")
    monkeypatch.setattr(worker.http, "fetch", lambda *a, **k: pytest.fail("no direct fallback"))
    result = worker.execute({"schema":worker.SCHEMA,"query":"synthetic","families":["research"]})
    assert result["channels"][0]["error_code"] == "proxy_config_invalid"
    assert "secret" not in str(result)


@pytest.mark.parametrize("url", ["https://private.example/works", "https://127.0.0.1/works",
    "http://api.openalex.org/works", "https://api.openalex.org:8443/works",
    "https://api.openalex.org/private", "https://user:secret@api.openalex.org/works"])
def test_arbitrary_target_is_rejected_before_connect(modules, monkeypatch, url):
    proxy, worker = modules
    monkeypatch.setattr(proxy.socket, "create_connection", lambda *a, **k: pytest.fail("must not connect"))
    with pytest.raises(proxy.ProxyFailure) as caught:
        proxy.fetch(url, proxy_url="http://127.0.0.1:7890", http=worker.http,
            policy=worker.http.SafeHTTPPolicy(timeout=12,max_bytes=131072,max_redirects=0,
                allowed_ports=(443,),allowed_hosts=("api.openalex.org",),allowed_content_types=("application/json",)),
            headers={})
    assert caught.value.code == "proxy_target_invalid"


def test_connect_uses_total_deadline_against_slow_drip(modules, monkeypatch):
    import time
    proxy, worker = modules
    sock = Socket()
    wire(monkeypatch, proxy, sock)
    original = sock.recv
    def slow(count):
        time.sleep(.02)
        return original(count)
    monkeypatch.setattr(sock, "recv", slow)
    with pytest.raises(proxy.ProxyFailure) as caught:
        invoke(modules, policy=worker.http.SafeHTTPPolicy(timeout=.01,max_bytes=131072,max_redirects=0,
            allowed_ports=(443,),allowed_hosts=("api.openalex.org",),allowed_content_types=("application/json",)))
    assert caught.value.code == "proxy_timeout" and sock.closed


def test_default_direct_ignores_generic_proxy_environment(modules, monkeypatch):
    _, worker = modules
    monkeypatch.delenv("ARCHEAXIS_PUBLIC_RESEARCH_PROXY", raising=False)
    monkeypatch.setenv("HTTPS_PROXY", "http://user:secret@external.invalid")
    monkeypatch.setattr(worker.proxy_transport, "_windows_proxy", lambda: None)
    monkeypatch.setattr(worker.http, "fetch", lambda *a, **k: SimpleNamespace(body=b'{"results":[]}',headers={},status=200))
    monkeypatch.setattr(worker.proxy_transport, "fetch", lambda *a, **k: pytest.fail("opt-in absent"))
    result = worker.execute({"schema":worker.SCHEMA,"query":"synthetic","families":["research"]})
    assert result["channels"][0]["status"] == "complete"


def test_request_headers_cannot_send_authentication_or_inject(modules, monkeypatch):
    proxy, _ = modules
    monkeypatch.setattr(proxy.socket, "create_connection", lambda *a, **k: pytest.fail("must not connect"))
    for headers in ({"Authorization":"secret"}, {"Proxy-Authorization":"secret"}, {"User-Agent":"x\r\nCookie: secret"}):
        with pytest.raises(proxy.ProxyFailure) as caught:
            invoke(modules, headers=headers)
        assert caught.value.code == "proxy_target_invalid"
