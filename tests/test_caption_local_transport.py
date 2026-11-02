"""Synthetic loopback servers prove image requests cannot follow redirects."""
import base64
import importlib.util
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest


def load_caption():
    path = Path(__file__).resolve().parents[1] / "services/python-workers/vision/worker_caption.py"
    spec = importlib.util.spec_from_file_location("caption_local_transport_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("base", ["http://example.com/v1", "https://127.0.0.1/v1", "http://user:password@127.0.0.1/v1", "http://127.0.0.1/v1#fragment", "http://127.0.0.1.evil.invalid/v1"])
def test_private_image_endpoint_refused_before_open(base, monkeypatch):
    caption = load_caption()
    calls = []
    monkeypatch.setattr(caption.urllib.request, "build_opener", lambda *args: calls.append(args))
    with pytest.raises(ValueError):
        caption._call({"base": base, "protocol": "openai"}, "synthetic-model", "c3ludGhldGlj", 2)
    assert calls == []


@pytest.mark.parametrize("status", [301, 302, 303, 307, 308])
@pytest.mark.parametrize("method", ["GET", "POST"])
def test_caption_redirect_and_inherited_proxy_never_receive_image(status, method, monkeypatch):
    caption = load_caption()
    counts = {"source": 0, "target": 0}

    class Target(BaseHTTPRequestHandler):
        def do_GET(self):
            counts["target"] += 1
            self.send_response(200); self.end_headers(); self.wfile.write(b"{}")
        do_POST = do_GET
        def log_message(self, *args):
            pass

    target = ThreadingHTTPServer(("127.0.0.1", 0), Target)

    class Source(BaseHTTPRequestHandler):
        def do_GET(self):
            counts["source"] += 1
            if self.command == "POST":
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                assert body["messages"][0]["content"][1]["image_url"]["url"].endswith("c3ludGhldGlj")
            self.send_response(status)
            self.send_header("Location", f"http://127.0.0.1:{target.server_port}/sink")
            self.end_headers()
        do_POST = do_GET
        def log_message(self, *args):
            pass

    source = ThreadingHTTPServer(("127.0.0.1", 0), Source)
    threads = [threading.Thread(target=s.serve_forever, daemon=True) for s in (source, target)]
    for thread in threads:
        thread.start()
    monkeypatch.setenv("HTTP_PROXY", "http://127.0.0.1:1")
    monkeypatch.setenv("ALL_PROXY", "http://127.0.0.1:1")
    monkeypatch.setenv("NO_PROXY", "")
    endpoint = {"base": f"http://127.0.0.1:{source.server_port}/v1", "protocol": "openai"}
    try:
        if method == "POST":
            with pytest.raises(ValueError, match="redirect"):
                caption._call(endpoint, "synthetic-model", "c3ludGhldGlj", 2)
        else:
            assert caption._installed_models(endpoint) == []
        assert counts == {"source": 1, "target": 0}
    finally:
        for server in (source, target):
            server.shutdown(); server.server_close()
        for thread in threads:
            thread.join(timeout=2)
            assert not thread.is_alive()


def test_reasoning_only_is_not_a_description(monkeypatch):
    caption = load_caption()

    class Response:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def read(self):
            return json.dumps({"choices": [{"message": {"content": "", "reasoning_content": "synthetic internal reasoning"}}]}).encode()

    monkeypatch.setattr(caption, "local_urlopen", lambda *args, **kwargs: Response())
    assert caption._call({"base": "http://127.0.0.1/v1", "protocol": "openai"}, "synthetic-model", "c3ludGhldGlj", 2) == ""


@pytest.mark.parametrize(
    ("suffix", "expected_mime", "raw"),
    [
        (".png", "image/png", b"\x89PNG\r\n\x1a\nSYNTHETIC"),
        (".jpg", "image/jpeg", b"\xff\xd8\xffSYNTHETIC"),
        (".jpeg", "image/jpeg", b"\xff\xd8\xffSYNTHETIC"),
        (".webp", "image/webp", b"RIFF\x00\x00\x00\x00WEBPSYNTHETIC"),
        (".bmp", "image/bmp", b"BMSYNTHETIC"),
        (".tiff", "image/tiff", b"II\x2a\x00SYNTHETIC"),
    ],
)
@pytest.mark.parametrize("require_identity", [False, True])
def test_openai_image_mime_matches_declared_suffix_and_preserves_bytes(
    tmp_path, monkeypatch, suffix, expected_mime, raw, require_identity
):
    # These are synthetic marker bytes, not valid images: this tests transport
    # labeling and exact bytes, not MIME sniffing or image decoding.
    caption = load_caption()
    image = tmp_path / ("synthetic" + suffix)
    image.write_bytes(raw)
    calls = []

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def read(self):
            return json.dumps({
                "model": "synthetic-model",
                "choices": [{"message": {"content": "synthetic description"}, "finish_reason": "stop"}],
            }).encode("utf-8")

    def capture(request, **kwargs):
        calls.append((request, kwargs))
        return Response()

    monkeypatch.setattr(caption, "local_urlopen", capture)
    endpoint = {"base": "http://127.0.0.1:1234/v1", "protocol": "openai", "model": "synthetic-model"}
    result = caption.describe(image, "synthetic-model", require_identity=require_identity, endpoint_override=endpoint)

    assert result["description"] == "synthetic description"
    assert len(calls) == 1
    request, _ = calls[0]
    assert request.full_url == "http://127.0.0.1:1234/v1/chat/completions"
    assert request.get_method() == "POST"
    body = json.loads(request.data)
    assert body["model"] == "synthetic-model"
    data_url = body["messages"][0]["content"][1]["image_url"]["url"]
    assert data_url == f"data:{expected_mime};base64,{base64.b64encode(raw).decode('ascii')}"
    if require_identity:
        assert result["engine_receipt"]["mime"] == expected_mime
        assert result["engine_receipt"]["actual_model"] == "synthetic-model"
        assert result["engine_receipt"]["completion_state"] == "complete"
    else:
        assert result["engine_receipt"] is None
