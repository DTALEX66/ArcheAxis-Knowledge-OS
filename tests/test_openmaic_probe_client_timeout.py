"""The local staged probe must wait for multi-stage generation requests."""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import threading
import time

import pytest

from scripts.probes import aaos_openmaic_generation_staged_loop as probe


def test_generation_clients_wait_longer_than_ordinary_requests(monkeypatch):
    class SlowResponse(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def do_POST(self):
            self.rfile.read(int(self.headers.get("Content-Length", "0")))
            time.sleep(0.2)
            try:
                self.send_response(200)
                self.send_header("Content-Length", "2")
                self.end_headers()
                self.wfile.write(b"{}")
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), SlowResponse)
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    monkeypatch.setattr(probe, "DEFAULT_HTTP_TIMEOUT_SECONDS", 0.05)
    monkeypatch.setattr(probe, "OUTLINE_HTTP_TIMEOUT_SECONDS", 1.0)
    monkeypatch.setattr(probe, "SCENE_HTTP_TIMEOUT_SECONDS", 1.0)
    core = probe.Core(None, Path("synthetic"))
    core.port = server.server_address[1]
    core.token = "synthetic"
    try:
        with pytest.raises(TimeoutError):
            core.request("POST", "/api/v1/documents", {})
        assert core.request("POST", "/api/v1/courses/openmaic/outlines/generate", {}) == (200, {})
        assert core.request("POST", "/api/v1/courses/openmaic/outlines/generate-interactive", {}) == (200, {})
        assert core.request("POST", "/api/v1/courses/openmaic/scenes/generate", {}) == (200, {})
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
