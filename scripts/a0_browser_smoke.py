#!/usr/bin/env python3
"""Real-browser geometry and theme gate for the formal Tauri/React desktop UI (SUP-022).

This proves the rendered shell in Chromium at desktop viewports; it does not prove the
installed WebView2 host, physical IME, or Owner acceptance, which stay separate Q14 tiers.
"""
from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import time
from hashlib import sha256
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import urlopen

from playwright.sync_api import Route, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
RUN_ROOT = Path(os.environ.get("ARCHEAXIS_RUN_ROOT", ROOT / ".project-local" / "task-runtime"))
RUNTIME = RUN_ROOT / ("runtime" if os.environ.get("ARCHEAXIS_RUN_ROOT") else "")
ARTIFACTS = (RUN_ROOT / "artifacts" / "browser-smoke") if os.environ.get("ARCHEAXIS_RUN_ROOT") else (RUN_ROOT / "browser-smoke")
def browser_smoke_port() -> int:
    """Allocate an ephemeral loopback port so parallel/retry runs cannot collide."""
    configured = os.environ.get("ARCHEAXIS_BROWSER_SMOKE_PORT")
    if configured:
        return int(configured)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


PORT = browser_smoke_port()
URL = f"http://127.0.0.1:{PORT}"
API_PREFIX = "/" + "api"
WORKSPACE_PREFIX = "/" + "workspace"

# The owner scoped the formal UI to the desktop host on 2026-10-07 and retired the phone
# end, so this matrix is Windows desktop resolutions plus the CSS viewports that
# 125/150/200% display scaling leaves behind them (physical pixels / scale).
DESKTOP_MATRIX: tuple[tuple[str, int, int, float], ...] = (
    ("1920x1080@100", 1920, 1080, 1.0),
    ("2560x1440@100", 2560, 1440, 1.0),
    ("1440x1000@100", 1440, 1000, 1.0),
    ("1280x800@100", 1280, 800, 1.0),
    ("1024x768@100", 1024, 768, 1.0),
    ("1920x1080@125", 1536, 864, 1.25),
    ("1920x1080@150", 1280, 720, 1.5),
    ("1920x1080@200", 960, 540, 2.0),
)
AAOS_THEME_IDS = ("black", "white", "cosmic")

HANDSHAKE = {
    "product_id": "archeaxis-workspace",
    "product_name": "ArcheAxis Knowledge",
    "api_contract": "1.x",
    "backend_version": "browser-smoke",
    "source_commit": os.environ.get("GITHUB_SHA", "worktree"),
    "schema_version": 15,
    "runtime_mode": "browser-smoke",
    "workspace_id": "browser-smoke",
    "capabilities": [],
    "migration_state": "ready",
}


def api_payload(url: str) -> dict[str, object]:
    path = urlsplit(url).path
    if path == f"{API_PREFIX}/v1/system/handshake":
        return HANDSHAKE
    if path == f"{WORKSPACE_PREFIX}/api/v1/home":
        return {
            "release": {"version": "candidate", "status": "candidate", "public": False},
            "counts": {"research": {"candidate": 0}, "jobs": {"succeeded": 0}},
            "components": {"api": "available", "database": "available"},
            "capabilities": {"local_url_file_github_intake": "available"},
            "recent_activity": [],
        }
    if path == f"{WORKSPACE_PREFIX}/api/v1/activity":
        return {"items": [], "next_cursor": None}
    if path == f"{WORKSPACE_PREFIX}/api/delivery":
        return {"summary": {"jobs": 0, "outbox": {}, "receipts": {}}}
    if path == f"{WORKSPACE_PREFIX}/api/library":
        return {"items": []}
    if path == f"{WORKSPACE_PREFIX}/api/evidence/anchors":
        return {"count": 0, "items": [], "next_cursor": None}
    if path == f"{WORKSPACE_PREFIX}/api/evidence/bundles":
        return {"items": []}
    if path == f"{WORKSPACE_PREFIX}/api/research":
        return {"items": []}
    if path in {
        f"{WORKSPACE_PREFIX}/api/runtime/knowledge",
        f"{WORKSPACE_PREFIX}/api/runtime/candidates",
    }:
        return {"items": []}
    if path == f"{API_PREFIX}/v1/setup/status":
        return {
            "schema_version": "v1",
            "ready": True,
            "workspace_id": "browser-smoke",
            "workspace_root": "browser-smoke",
            "steps": [{"id": "paths_writable", "state": "ready", "message": "ready", "action_hint": ""}],
        }
    if path == f"{API_PREFIX}/v1/learning/review-queue":
        return {"due_count": 0, "due": []}
    if path == f"{WORKSPACE_PREFIX}/api/status":
        return {
            "schema_version": "v1",
            "observed_at": "2026-08-29T00:00:00Z",
            "release": {"version": "candidate", "status": "candidate", "public": False},
            "components": {},
            "migrations": {},
            "counts": {},
            "capabilities": {},
        }
    return {}


def start_vite(log_path: Path) -> tuple[subprocess.Popen[bytes], object]:
    log = log_path.open("wb")
    if os.name == "nt":
        node = shutil.which("node")
        vite = ROOT / "frontend" / "node_modules" / "vite" / "bin" / "vite.js"
        if not node or not vite.is_file():
            log.close()
            raise RuntimeError("Vite requires Node and frontend/node_modules/vite/bin/vite.js")
        # Running Vite through cmd/npm can orphan the actual Node server when
        # cmd.exe exits. Start the server process itself so taskkill /T can
        # deterministically reclaim the smoke-run process tree.
        command = [node, str(vite), "--host", "127.0.0.1", "--port", str(PORT)]
        cwd = ROOT / "frontend"
    else:
        command = [
            "npm", "--prefix", "frontend", "run", "dev", "--",
            "--host", "127.0.0.1", "--port", str(PORT),
        ]
        cwd = ROOT
    process = subprocess.Popen(
        command,
        cwd=cwd,
        stdout=log,
        stderr=subprocess.STDOUT,
    )
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        if process.poll() is not None:
            log.flush()
            stop_vite(process, log)
            raise RuntimeError(f"Vite exited before readiness; inspect {log_path}")
        try:
            with urlopen(URL, timeout=1) as response:  # noqa: S310 - fixed loopback URL
                if response.status == 200:
                    return process, log
        except OSError:
            time.sleep(0.2)
    stop_vite(process, log)
    raise RuntimeError(f"Vite readiness timed out; inspect {log_path}")


def stop_vite(process: subprocess.Popen[bytes], log: object) -> None:
    if os.name == "nt":
        # The smoke runner starts Vite's Node process directly.  Prefer its
        # handle over taskkill, which can be blocked by an execution sandbox.
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            subprocess.run(
                ["taskkill.exe", "/PID", str(process.pid), "/T", "/F"],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            process.wait(timeout=5)
    else:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
    log.close()


def source_revision() -> dict[str, object]:
    """Identify the tested tree without writing the Git index."""
    base_commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()
    diff = subprocess.check_output(
        ["git", "diff", "--no-ext-diff", "--binary"], cwd=ROOT
    )
    return {
        "base_commit": base_commit,
        "worktree_dirty": bool(diff),
        "worktree_diff_sha256": sha256(diff).hexdigest() if diff else None,
    }


def main() -> None:
    RUNTIME.mkdir(parents=True, exist_ok=True)
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    process, log = start_vite(RUNTIME / "a0-canonical-vite.log")
    errors: list[str] = []
    viewports: dict[str, object] = {}
    themes: dict[str, object] = {}
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            for label, width, height, scale in DESKTOP_MATRIX:
                context = browser.new_context(
                    viewport={"width": width, "height": height},
                    device_scale_factor=scale,
                    reduced_motion="reduce",
                )
                page = context.new_page()
                page.on("pageerror", lambda error: errors.append(f"pageerror:{error}"))
                page.on(
                    "console",
                    lambda message: errors.append(f"console:{message.text}")
                    if message.type == "error" else None,
                )

                def route_api(route: Route) -> None:
                    path = urlsplit(route.request.url).path
                    if path.startswith(f"{API_PREFIX}/") or path.startswith(
                        f"{WORKSPACE_PREFIX}/api/"
                    ):
                        route.fulfill(
                            status=200,
                            content_type="application/json",
                            body=json.dumps(api_payload(route.request.url)),
                        )
                    else:
                        route.continue_()

                page.route("**/*", route_api)
                page.goto(URL, wait_until="networkidle")
                page.get_by_role("heading", name="工作台").first.wait_for()
                geometry = page.evaluate("""() => {
                    const box = (selector) => {
                      const rect = document.querySelector(selector)?.getBoundingClientRect();
                      return rect && {x:rect.x,y:rect.y,width:rect.width,height:rect.height,bottom:rect.bottom};
                    };
                    const context = document.querySelector('.context-subnav');
                    const bar = [...(document.querySelector('.status-bar')?.children ?? [])];
                    const overlaps = [];
                    for (let i = 0; i < bar.length; i++) for (let j = i + 1; j < bar.length; j++) {
                      const a = bar[i].getBoundingClientRect(), b = bar[j].getBoundingClientRect();
                      const width = Math.min(a.right, b.right) - Math.max(a.left, b.left);
                      const height = Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top);
                      if (width > 1 && height > 1) {
                        overlaps.push([bar[i].className || bar[i].tagName, bar[j].className || bar[j].tagName, +width.toFixed(1)]);
                      }
                    }
                    return {
                      scrollWidth: document.documentElement.scrollWidth,
                      clientWidth: document.documentElement.clientWidth,
                      devicePixelRatio: window.devicePixelRatio,
                      rail: box('.space-rail'),
                      dock: box('.activity-dock'),
                      main: box('.app-center'),
                      inspector: Boolean(document.querySelector('.inspector')),
                      context: Boolean(context) && getComputedStyle(context).display !== 'none',
                      statusBarOverlaps: overlaps,
                      motionFast: getComputedStyle(document.documentElement).getPropertyValue('--ax-motion-fast').trim(),
                    };
                }""")
                assert geometry["scrollWidth"] <= geometry["clientWidth"], geometry
                assert geometry["dock"]["bottom"] <= height + 0.5, geometry
                assert 140 <= geometry["rail"]["width"] <= 300, geometry
                assert geometry["main"]["x"] >= geometry["rail"]["width"] - 1, geometry
                assert geometry["main"]["bottom"] <= geometry["dock"]["y"] + 0.5, geometry
                assert not geometry["inspector"], geometry
                assert geometry["context"], geometry
                assert geometry["devicePixelRatio"] == scale, geometry
                assert not geometry["statusBarOverlaps"], geometry
                assert geometry["motionFast"] == "0ms", geometry

                page.get_by_role("button", name="打开全局命令").click()
                page.get_by_role("dialog", name="全局命令").wait_for()
                page.get_by_role("button", name="关闭全局命令").click()
                # Focus contract, measured in the browser rather than in jsdom: closing
                # with Escape returns focus to the trigger that opened it, and Ctrl+K
                # lands the caret in the search field.
                page.get_by_role("button", name="打开全局命令").click()
                page.get_by_role("dialog", name="全局命令").wait_for()
                page.keyboard.press("Escape")
                page.get_by_role("dialog", name="全局命令").wait_for(state="detached")
                # Radix restores focus on the next frame, so read it after a settle rather
                # than in the same tick as the detach.
                page.wait_for_timeout(200)
                restored = page.evaluate(
                    "() => { const el = document.activeElement;"
                    " return el && {tag: el.tagName, label: el.getAttribute('aria-label'), cls: el.className}; }"
                )
                assert restored == {"tag": "BUTTON", "label": "打开全局命令", "cls": "command-trigger"}, restored
                page.keyboard.press("Control+k")
                page.get_by_role("dialog", name="全局命令").wait_for()
                page.wait_for_timeout(200)
                opened = page.evaluate(
                    "() => { const el = document.activeElement; return el && {tag: el.tagName, label: el.getAttribute('aria-label')}; }"
                )
                assert opened == {"tag": "INPUT", "label": "搜索空间或命令"}, opened
                page.keyboard.press("Escape")
                page.get_by_role("dialog", name="全局命令").wait_for(state="detached")
                page.locator('[data-space-id="learning"]').click()
                page.locator("#space-learning").wait_for()
                assert page.get_by_role("button", name="视觉课件").count() == 0
                assert page.get_by_role("button", name="空间记忆").count() == 0
                page.get_by_role("button", name="展开活动坞").click()
                assert page.get_by_role("button", name="取消投递（不可用）").count() == 0

                if label == DESKTOP_MATRIX[0][0]:
                    for theme in AAOS_THEME_IDS:
                        page.get_by_label("界面主题").select_option(theme)
                        page.wait_for_timeout(150)
                        applied = page.evaluate("document.documentElement.dataset.aaosTheme")
                        brand = page.locator(".status-bar-brand img").get_attribute("src") or ""
                        surface = page.evaluate("getComputedStyle(document.body).backgroundColor")
                        assert applied == theme, (applied, theme)
                        assert theme in brand, brand
                        shot = ARTIFACTS / f"canonical-theme-{theme}-{label}.png"
                        page.screenshot(path=str(shot))
                        themes[theme] = {
                            "root_attribute": applied,
                            "brand_mark": brand,
                            "body_surface": surface,
                            "screenshot": str(shot.relative_to(ROOT)),
                        }
                    page.get_by_label("界面主题").select_option("black")

                screenshot = ARTIFACTS / f"canonical-shell-{label}.png"
                page.screenshot(path=str(screenshot), full_page=True)
                viewports[label] = {
                    "geometry": geometry,
                    "screenshot": str(screenshot.relative_to(ROOT)),
                }
                context.close()
            browser.close()
    finally:
        stop_vite(process, log)

    assert not errors, errors
    revision = source_revision()
    report = {
        "schema": "archeaxis/canonical-browser-smoke/v3",
        "status": "PASS",
        "source_revision": revision,
        "errors": errors,
        "viewports": viewports,
        "themes": themes,
    }
    output = ARTIFACTS / "canonical-browser-smoke.json"
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
