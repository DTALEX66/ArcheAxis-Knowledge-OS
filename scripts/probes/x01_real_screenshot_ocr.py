"""X01 real screenshot->OCR probe (C09: reproducible, in-repo copy).

Serves one local HTML page, captures it through app/ingestion/web_screenshot
(Chromium-family browser found by the product), then runs the OCR worker with
the public model profile. Prints a JSON summary; exit 0 when all ASCII markers
are recognized. Chromium-family browser + tesseract tessdata must exist on the
host (shared toolchain) - see EXECUTION.md X01 slices.
"""

from __future__ import annotations

import hashlib
import json
import socket
import subprocess
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

HTML = (
    "<html><head><meta charset='utf-8'></head>"
    "<body style='background:#ffffff;font-size:56px;font-family:Arial,sans-serif;"
    "padding:48px'>ARCHEAXIS OCR PROBE 123<br>鏄熺幆 OCR 鎺㈤拡 2026</body></html>"
)


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        body = HTML.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):  # quiet
        pass


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def main() -> int:
    from app.ingestion.web_screenshot import screenshot_web

    out_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(tempfile.gettempdir())
    out_dir.mkdir(parents=True, exist_ok=True)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{server.server_address[1]}/index.html"
    png = out_dir / "page.png"
    try:
        shot = screenshot_web(url, png, width=1200)
    finally:
        server.shutdown()

    digest = hashlib.sha256(png.read_bytes()).hexdigest()
    ocr = subprocess.run(
        [sys.executable, "-B", str(REPO / "services/python-workers/vision/worker_ocr.py"),
         str(png), "--profile", str(REPO / "config/model-profiles/local-2026-09-05.yaml")],
        cwd=REPO, capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    try:
        payload = json.loads(ocr.stdout or "{}")
    except json.JSONDecodeError:
        payload = {}
    text = str(payload.get("text", ""))
    tokens = [t for t in ("ARCHEAXIS", "OCR", "PROBE", "123") if t in text]
    print(json.dumps({
        "png_sha256": digest, "png_bytes": png.stat().st_size,
        "browser": shot.get("engine"), "ocr_exit": ocr.returncode,
        "matched_tokens": tokens, "text_head": text[:120].replace("\n", " "),
    }, ensure_ascii=False))
    return 0 if shot.get("ok") and tokens and ocr.returncode == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
