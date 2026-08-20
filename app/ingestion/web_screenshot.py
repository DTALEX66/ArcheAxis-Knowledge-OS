"""Web screenshot through a locally installed Chromium-family browser.

Covers the capture->screenshot step of the web full chain: raw HTML +
extracted text + visual screenshot (PNG) which can feed OCR / VLM.
"""

from __future__ import annotations

import subprocess
import os
import shutil
from pathlib import Path
from typing import Any

def _edge_candidates() -> tuple[Path, ...]:
    roots = (os.environ.get("PROGRAMFILES(X86)", ""), os.environ.get("PROGRAMFILES", ""))
    return tuple(
        Path(root) / "Microsoft" / "Edge" / "Application" / "msedge.exe"
        for root in roots
        if root
    )


class WebScreenshotError(ValueError):
    """Raised when screenshot fails."""


_BROWSER_COMMANDS = (
    "msedge",
    "google-chrome",
    "google-chrome-stable",
    "chromium",
    "chromium-browser",
)


def find_browser() -> str:
    """Find a Chromium-family browser without depending on one OS vendor."""
    for command in _BROWSER_COMMANDS:
        from_path = shutil.which(command)
        if from_path:
            return from_path
    for candidate in _edge_candidates():
        if candidate.is_file():
            return str(candidate)
    raise WebScreenshotError("no supported Chromium-family browser was found")


def find_edge() -> str:
    """Compatibility alias for callers that used the original Edge-only API."""
    return find_browser()


def _browser_environment(out: Path) -> dict[str, str]:
    """Keep Chromium's Unix singleton socket below its path-length limit."""
    temp_root = out.parent
    for parent in out.parents:
        if parent.name == ".hermes":
            temp_root = parent
            break
    temp_root.mkdir(parents=True, exist_ok=True)
    environment = os.environ.copy()
    for name in ("TMP", "TEMP", "TMPDIR"):
        environment[name] = str(temp_root)
    return environment


def screenshot_web(url: str, out_path: str | Path, *, width: int = 1280) -> dict[str, Any]:
    """Headless screenshot of a URL into a PNG file.

    Returns: {"ok", "path", "bytes", "engine": "<browser>-headless"}
    """
    browser = find_browser()
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(
        [browser, "--headless", "--disable-gpu", "--no-sandbox",
         f"--window-size={width},800", f"--screenshot={out}", url],
        capture_output=True, timeout=60,
        env=_browser_environment(out),
    )
    if not out.is_file() or out.stat().st_size == 0:
        raise WebScreenshotError(f"screenshot failed: {proc.stderr.decode(errors='ignore')[:200]}")
    return {
        "ok": True,
        "path": str(out),
        "bytes": out.stat().st_size,
        "engine": f"{Path(browser).name}-headless",
    }
