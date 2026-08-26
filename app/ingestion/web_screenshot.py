"""Web screenshot through a locally installed Chromium-family browser.

Covers the capture->screenshot step of the web full chain: raw HTML +
extracted text + visual screenshot (PNG) which can feed OCR / VLM.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
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


def _browser_environment(out: Path, profile: str) -> dict[str, str]:
    """Keep Chromium's singleton socket + temp below its path-length limit.

    GitHub-hosted runner workspaces are ~70 chars long; Chromium's
    process-singleton socket lives under the user-data dir / TMPDIR and
    FATALs once the path exceeds ~108 chars (Unix). Point TMP/TEMP/TMPDIR
    at the system temp root (short: /tmp on Linux) and hand Chrome a
    short, unique --user-data-dir profile. Both are process-lifetime
    transients; the screenshot output itself stays under the project's
    task-runtime (out_path).
    """
    environment = os.environ.copy()
    sys_temp = tempfile.gettempdir()
    for name in ("TMP", "TEMP", "TMPDIR"):
        environment[name] = sys_temp
    return environment


def screenshot_web(url: str, out_path: str | Path, *, width: int = 1280) -> dict[str, Any]:
    """Headless screenshot of a URL into a PNG file.

    Returns: {"ok", "path", "bytes", "engine": "<browser>-headless"}
    """
    browser = find_browser()
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    profile = tempfile.mkdtemp(prefix="archeaxis-shot-")
    try:
        proc = subprocess.run(
            [browser, "--headless", "--disable-gpu", "--no-sandbox",
             f"--user-data-dir={profile}",
             f"--window-size={width},800", f"--screenshot={out}", url],
            capture_output=True, timeout=60,
            env=_browser_environment(out, profile),
        )
        if not out.is_file() or out.stat().st_size == 0:
            raise WebScreenshotError(f"screenshot failed: {proc.stderr.decode(errors='ignore')[:200]}")
    finally:
        shutil.rmtree(profile, ignore_errors=True)
    return {
        "ok": True,
        "path": str(out),
        "bytes": out.stat().st_size,
        "engine": f"{Path(browser).name}-headless",
    }
