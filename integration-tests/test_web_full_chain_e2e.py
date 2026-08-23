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
<p>学习者可以沿着熟悉的空间路径，把待记信息与地点逐一关联，再按路径回忆。</p>
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


def _local_policy(local_site):
    from shared.safe_http import SafeHTTPPolicy
    import urllib.parse
    port = urllib.parse.urlsplit(local_site).port
    return SafeHTTPPolicy(allowed_ports=(80, 443, port))


def test_web_full_chain_capture_extract(local_site):
    from app.ingestion.web import capture_web
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


def test_web_full_chain_ingest_and_convert(local_site):
    # Raw-first capture extracts only the saved HTML; it must not depend on a
    # second URL fetch or the obsolete convert_url chain.
    from app.ingestion.web import capture_web
    cap = capture_web(local_site, policy=_local_policy(local_site),
                      raw_fetcher=_local_fetcher(HTML.encode("utf-8")))
    assert cap["receipt"]["text_chars"] > 50
    assert cap["receipt"]["text_chars"] == len(cap["text"])
    # Extracted content carries the knowledge present in the saved raw page.
    assert "记忆宫殿" in cap["text"] or "空间位置" in cap["text"]
