"""X01 real screenshot->OCR probe (C09: reproducible, in-repo copy).

Serves one local HTML page, captures it through app/ingestion/web_screenshot
(Chromium-family browser found by the product), then runs the OCR worker with
the public model profile. Prints a JSON summary; exit 0 when all ASCII markers
are recognized. Chromium-family browser + tesseract tessdata must exist on the
host (shared toolchain) - see EXECUTION.md X01 slices.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import socket
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def _load_module(name: str, rel: str):
    spec = importlib.util.spec_from_file_location(name, REPO / rel)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

HTML = (
    "<html><head><meta charset='utf-8'></head>"
    "<body style='background:#ffffff;font-size:56px;font-family:Arial,sans-serif;"
    "padding:48px'>ARCHEAXIS OCR PROBE 123<br>星环 OCR 探针 2026</body></html>"
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
    screenshot_web = _load_module("web_screenshot", "app/ingestion/web_screenshot.py").screenshot_web

    runtime = _load_module("runtime_screenshot_probe", "scripts/runtime/dev.py")
    if len(sys.argv) > 1:
        out_dir = runtime.safe_path(Path(sys.argv[1]))
        if not out_dir.is_relative_to(runtime.layout(REPO)["dev"]):
            raise ValueError("screenshot probe output must stay inside this project's .project-local")
    else:
        out_dir = runtime.artifact_directory(REPO, "screenshot-ocr")
    out_dir.mkdir(parents=True, exist_ok=True)
    png = out_dir / "page.png"
    if png.exists():
        raise FileExistsError("screenshot probe refuses to overwrite an existing page.png")

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{server.server_address[1]}/index.html"
    try:
        shot = screenshot_web(url, png, width=1200)
    except Exception as error:
        print(json.dumps({"ok": False, "phase": "screenshot", "error": str(error)}, ensure_ascii=False))
        return 2
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    if not shot.get("ok") or not png.is_file():
        print(json.dumps({"ok": False, "phase": "screenshot", "error": "no successful screenshot"}))
        return 2

    digest = hashlib.sha256(png.read_bytes()).hexdigest()
    ocr = subprocess.run(
        [sys.executable, "-B", str(REPO / "services/python-workers/vision/worker_ocr.py"),
         str(png), "--profile", str(REPO / "config/model-profiles/local-2026-09-05.yaml")],
        cwd=REPO, capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=120, creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    )
    try:
        payload = json.loads(ocr.stdout or "{}")
    except json.JSONDecodeError:
        payload = {}
    if not isinstance(payload, dict):
        payload = {}
    text = str(payload.get("text", ""))
    required = ("ARCHEAXIS", "OCR", "PROBE", "123")
    words = set(re.findall(r"\b[A-Za-z0-9]+\b", text))
    tokens = [token for token in required if token in words]
    missing = [token for token in required if token not in words]
    ok = bool(not missing and ocr.returncode == 0)
    print(json.dumps({
        "ok": ok,
        "png_sha256": digest, "png_bytes": png.stat().st_size,
        "browser": shot.get("engine"), "ocr_exit": ocr.returncode,
        "matched_tokens": tokens, "missing_tokens": missing, "text_head": text[:120].replace("\n", " "),
    }, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
