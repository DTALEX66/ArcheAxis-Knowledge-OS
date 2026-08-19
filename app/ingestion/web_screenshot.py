"""Web screenshot — msedge headless (zero-dependency on Windows).

Covers the capture->screenshot step of the web full chain: raw HTML +
extracted text + visual screenshot (PNG) which can feed OCR / VLM.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

_EDGE_CANDIDATES = (
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
)


class WebScreenshotError(ValueError):
    """Raised when screenshot fails."""


def find_edge() -> str:
    for cand in _EDGE_CANDIDATES:
        if Path(cand).is_file():
            return cand
    raise WebScreenshotError("msedge not found (Windows Edge required for screenshots)")


def screenshot_web(url: str, out_path: str | Path, *, width: int = 1280) -> dict[str, Any]:
    """Headless screenshot of a URL into a PNG file.

    Returns: {"ok", "path", "bytes", "engine": "msedge-headless"}
    """
    edge = find_edge()
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(
        [edge, "--headless", "--disable-gpu", "--no-sandbox",
         f"--window-size={width},800", f"--screenshot={out}", url],
        capture_output=True, timeout=60,
    )
    if not out.is_file() or out.stat().st_size == 0:
        raise WebScreenshotError(f"screenshot failed: {proc.stderr.decode(errors='ignore')[:200]}")
    return {"ok": True, "path": str(out), "bytes": out.stat().st_size, "engine": "msedge-headless"}
