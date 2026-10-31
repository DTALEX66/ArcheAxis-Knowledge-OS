"""Synthetic route selection; no registry writes, PAC execution or network calls."""
import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]


def load(name):
    path = ROOT / "services/python-workers/machine" / (name + ".py")
    spec = importlib.util.spec_from_file_location(name + "_route_fixture", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def proxy():
    return load("public_research_proxy")


def registry(monkeypatch, proxy, *, enabled=1, server="127.0.0.1:7890", kind=1, error=None):
    calls = []
    handle = object()
    class Key:
        def __enter__(self):
            return handle
        def __exit__(self, *args):
            calls.append("closed")
    def open_key(root, path, reserved, access):
        assert (root, path, reserved, access) == ("HKCU",
            r"Software\Microsoft\Windows\CurrentVersion\Internet Settings", 0, 1)
        calls.append("opened-read-only")
        if error:
            raise error
        return Key()
    def query(key, name):
        assert key is handle and name in {"ProxyEnable", "ProxyServer"}
        calls.append(name)
        return (enabled, 4) if name == "ProxyEnable" else (server, kind)
    # Deliberately provides no write, enumeration, PAC or other settings API.
    fake = SimpleNamespace(HKEY_CURRENT_USER="HKCU", KEY_QUERY_VALUE=1,
        REG_DWORD=4, REG_SZ=1, OpenKey=open_key, QueryValueEx=query)
    monkeypatch.setitem(sys.modules, "winreg", fake)
    monkeypatch.setattr(proxy, "sys", SimpleNamespace(platform="win32"))
    return calls


@pytest.mark.parametrize("value,expected", [
    ("127.0.0.1:7890", "http://127.0.0.1:7890"),
    ("http://127.0.0.1:7890", "http://127.0.0.1:7890"),
    ("[::1]:7890", "http://[::1]:7890"),
    ("http=remote.invalid:80;https=127.0.0.1:7890;socks=remote.invalid:1080", "http://127.0.0.1:7890"),
    ("HTTPS=[::1]:7890;http=127.0.0.1:7891", "http://[::1]:7890"),
])
def test_enabled_literal_https_route_reads_only_two_values(proxy, monkeypatch, value, expected):
    calls = registry(monkeypatch, proxy, server=value)
    assert proxy.select_proxy(None) == expected
    assert calls == ["opened-read-only", "ProxyEnable", "ProxyServer", "closed"]


@pytest.mark.parametrize("value", ["", "proxy.example:7890", "192.168.1.1:7890",
    "user:secret@127.0.0.1:7890", "localhost:7890", "socks5://127.0.0.1:7890",
    "https://127.0.0.1:7890", "http://127.0.0.1:7890/", "127.0.0.1:0",
    "http=127.0.0.1:7890", "https=remote.invalid:7890;http=127.0.0.1:7890",
    "https=127.0.0.1:7890;https=127.0.0.1:7891", "https=127.0.0.1:7890;",
    "https=127.0.0.1:7890\r\n", "https=127.0.0.1:7890;pac=http://private.invalid/config.pac",
    "http://private.invalid/config.pac", "%PROXY%:7890", "x"*2049])
def test_unsupported_registered_values_keep_original_direct_route(proxy, monkeypatch, value):
    calls = registry(monkeypatch, proxy, server=value)
    assert proxy.select_proxy(None) is None
    assert set(calls) == {"opened-read-only", "ProxyEnable", "ProxyServer", "closed"}


def test_disabled_proxy_does_not_read_server_or_pac(proxy, monkeypatch):
    calls = registry(monkeypatch, proxy, enabled=0)
    assert proxy.select_proxy(None) is None
    assert calls == ["opened-read-only", "ProxyEnable", "closed"]


@pytest.mark.parametrize("error", [FileNotFoundError(), PermissionError()])
def test_missing_or_unreadable_registry_keeps_direct(proxy, monkeypatch, error):
    calls = registry(monkeypatch, proxy, error=error)
    assert proxy.select_proxy(None) is None and calls == ["opened-read-only"]


def test_expandable_registry_strings_are_not_expanded(proxy, monkeypatch):
    registry(monkeypatch, proxy, kind=2)
    assert proxy.select_proxy(None) is None


def test_other_platform_never_opens_windows_configuration(proxy, monkeypatch):
    calls = registry(monkeypatch, proxy)
    monkeypatch.setattr(proxy, "sys", SimpleNamespace(platform="linux"))
    assert proxy.select_proxy(None) is None and calls == []


@pytest.mark.parametrize("value,expected", [("direct", None),
    ("http://127.0.0.1:7891", "http://127.0.0.1:7891")])
def test_explicit_setting_precedes_registered_route(proxy, monkeypatch, value, expected):
    monkeypatch.setattr(proxy, "_windows_proxy", lambda: pytest.fail("explicit setting must not discover"))
    assert proxy.select_proxy(value) == expected


@pytest.mark.parametrize("value", ["", "DIRECT", " direct", "http://user:secret@127.0.0.1:7890",
    "http://remote.invalid:7890"])
def test_invalid_explicit_setting_never_discovers_or_silently_uses_direct(proxy, monkeypatch, value):
    monkeypatch.setattr(proxy, "_windows_proxy", lambda: pytest.fail("no discovery fallback"))
    with pytest.raises(proxy.ProxyFailure, match="^proxy_config_invalid$"):
        proxy.select_proxy(value)


def test_worker_resolves_once_and_preserves_each_channel_on_proxy_failure(monkeypatch):
    worker = load("public_research")
    monkeypatch.delenv("ARCHEAXIS_PUBLIC_RESEARCH_PROXY", raising=False)
    discovery, urls = [], []
    def route():
        discovery.append(True)
        return "http://127.0.0.1:7890"
    def fetch(url, *, proxy_url, **kwargs):
        assert proxy_url == "http://127.0.0.1:7890"
        urls.append(url)
        if "en.wikipedia.org" in url:
            raise worker.proxy_transport.ProxyFailure("proxy_timeout")
        payload = {"items": [], "quota_remaining": 1} if "stackexchange" in url else {"results": []}
        return SimpleNamespace(body=json.dumps(payload).encode(), headers={}, status=200)
    monkeypatch.setattr(worker.proxy_transport, "_windows_proxy", route)
    monkeypatch.setattr(worker.proxy_transport, "fetch", fetch)
    monkeypatch.setattr(worker.http, "fetch", lambda *a, **k: pytest.fail("no direct fallback"))
    result = worker.execute({"schema": worker.SCHEMA, "query": "synthetic",
        "families": ["encyclopedia", "community", "research"]})
    assert len(discovery) == 1 and len(urls) == 3
    assert [c["status"] for c in result["channels"]] == ["offline", "complete", "complete"]
    assert result["channels"][0]["error_code"] == "proxy_timeout"
    assert all(c["raw_response_base64"] for c in result["channels"][1:])


def test_direct_control_is_not_a_valid_transport_proxy(proxy):
    with pytest.raises(proxy.ProxyFailure, match="^proxy_config_invalid$"):
        proxy._proxy("direct")
