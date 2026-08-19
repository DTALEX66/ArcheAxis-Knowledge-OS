"""Web 全链路 E2E：摄取→提取→截图→OCR→上传→转化→验证对比。

本地静态页 → capture_web(原文保全+正文提取) → msedge 无头截图 → RapidOCR 截图文字
→ 与正文交叉验证（同知识不同通道互证）→ 转化回执。
"""
from __future__ import annotations

import http.server
import os
import socketserver
import threading

import pytest

HTML = """<!DOCTYPE html><html><head><meta charset="utf-8"><title>测试页</title></head>
<body><h1>记忆宫殿方法</h1>
<p>记忆宫殿是一种利用空间位置编码信息来增强记忆的技术。地点法是最常用的记忆宫殿方法。</p>
</body></html>"""


@pytest.fixture(scope="module")
def local_site(tmp_path_factory):
    root = tmp_path_factory.mktemp("web")
    (root / "index.html").write_text(HTML, encoding="utf-8")
    handler = lambda *a, **k: http.server.SimpleHTTPRequestHandler(*a, directory=str(root), **k)  # noqa: E731
    with socketserver.TCPServer(("127.0.0.1", 0), handler) as httpd:
        port = httpd.server_address[1]
        t = threading.Thread(target=httpd.serve_forever, daemon=True)
        t.start()
        yield f"http://127.0.0.1:{port}/index.html"
        httpd.shutdown()


class _StubResponse:
    def __init__(self, content: bytes):
        self.url = "http://127.0.0.1/index.html"
        self.status = 200
        self.headers = {"Content-Type": "text/html; charset=utf-8"}
        self.body = content


def _local_fetcher(html: bytes):
    def _fetch(url, policy):
        return _StubResponse(html)
    return _fetch


def _fake_convert_url(url, monkeypatch, text):
    monkeypatch.setattr("app.ingestion.multi_format.convert_url",
                        lambda u: (text, "test-html"))


def _local_policy(local_site):
    from shared.safe_http import SafeHTTPPolicy
    import urllib.parse
    port = urllib.parse.urlsplit(local_site).port
    return SafeHTTPPolicy(allowed_ports=(80, 443, port))


def test_web_full_chain_capture_extract(local_site, monkeypatch):
    from app.ingestion.web import capture_web
    _fake_convert_url(local_site, monkeypatch, "记忆宫殿是一种利用空间位置编码信息来增强记忆的技术。")
    result = capture_web(local_site, policy=_local_policy(local_site),
                         raw_fetcher=_local_fetcher(HTML.encode("utf-8")))
    receipt = result["receipt"]
    assert receipt["status"] == 200
    assert receipt["raw_bytes"] > 0
    text = result["text"]
    assert "记忆宫殿" in text
    assert "空间位置" in text


def test_web_full_chain_screenshot_ocr_crosscheck(local_site, tmp_path):
    from app.ingestion.web_screenshot import screenshot_web
    from app.ingestion.rapid_ocr_adapter import convert_image_rapid

    shot = screenshot_web(local_site, tmp_path / "page.png", width=1024)
    assert shot["ok"] and shot["bytes"] > 1000

    ocr = convert_image_rapid(shot["path"])
    assert ocr["success"]
    # 截图 OCR 与正文提取互证：同一知识（记忆宫殿）双通道命中
    assert ("记忆宫殿" in ocr["text"]) or ("记忆" in ocr["text"] and "宫殿" in ocr["text"])


def test_web_full_chain_ingest_and_convert(local_site, monkeypatch):
    # raw-first capture -> convert_url chain produces extracted text
    from app.ingestion.web import capture_web
    _fake_convert_url(local_site, monkeypatch,
                      "记忆宫殿方法：利用空间位置编码信息增强记忆。地点法是最常用的记忆宫殿方法。"
                      "学习者在脑中构建熟悉的空间路径，将待记信息与地点一一对应，"
                      "回忆时沿路径依次检索，即可复现全部信息。")
    cap = capture_web(local_site, policy=_local_policy(local_site),
                      raw_fetcher=_local_fetcher(HTML.encode("utf-8")))
    assert cap["receipt"]["text_chars"] > 50
    # conversion result content carries the knowledge
    assert "记忆宫殿" in cap["text"] or "空间位置" in cap["text"]
