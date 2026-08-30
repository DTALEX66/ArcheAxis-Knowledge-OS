#!/usr/bin/env python3
"""Real-browser smoke for the canonical React/Tauri product shell."""
from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import urlopen

from playwright.sync_api import Route, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / ".hermes" / "task-runtime"
ARTIFACTS = ROOT / ".hermes" / "task-artifacts" / "browser-smoke"
PORT = 5187
URL = f"http://127.0.0.1:{PORT}"
API_PREFIX = "/" + "api"
WORKSPACE_PREFIX = "/" + "workspace"

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
        command = [
            "cmd.exe", "/d", "/s", "/c",
            f"npm --prefix frontend run dev -- --host 127.0.0.1 --port {PORT}",
        ]
    else:
        command = [
            "npm", "--prefix", "frontend", "run", "dev", "--",
            "--host", "127.0.0.1", "--port", str(PORT),
        ]
    process = subprocess.Popen(
        command,
        cwd=ROOT,
        stdout=log,
        stderr=subprocess.STDOUT,
    )
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        if process.poll() is not None:
            log.flush()
            raise RuntimeError(f"Vite exited before readiness; inspect {log_path}")
        try:
            with urlopen(URL, timeout=1) as response:  # noqa: S310 - fixed loopback URL
                if response.status == 200:
                    return process, log
        except OSError:
            time.sleep(0.2)
    raise RuntimeError(f"Vite readiness timed out; inspect {log_path}")


def stop_vite(process: subprocess.Popen[bytes], log: object) -> None:
    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)
    log.close()


def main() -> None:
    RUNTIME.mkdir(parents=True, exist_ok=True)
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    process, log = start_vite(RUNTIME / "a0-canonical-vite.log")
    errors: list[str] = []
    viewports: dict[str, object] = {}
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            for width, height in ((1440, 1000), (1280, 800), (390, 844), (360, 640)):
                context = browser.new_context(
                    viewport={"width": width, "height": height},
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
                    return {
                      scrollWidth: document.documentElement.scrollWidth,
                      clientWidth: document.documentElement.clientWidth,
                      rail: box('.space-rail'),
                      dock: box('.activity-dock'),
                      main: box('.app-center'),
                      inspector: Boolean(document.querySelector('.inspector')),
                      context: Boolean(context) && getComputedStyle(context).display !== 'none',
                    };
                }""")
                assert geometry["scrollWidth"] <= geometry["clientWidth"], geometry
                assert geometry["dock"]["bottom"] <= height + 0.5, geometry
                if width <= 840:
                    assert geometry["rail"]["width"] >= width - 1, geometry
                    assert geometry["rail"]["height"] < 80, geometry
                    assert not geometry["inspector"], geometry
                    assert not geometry["context"], geometry
                else:
                    assert geometry["context"], geometry

                page.get_by_role("button", name="打开全局命令").click()
                page.get_by_role("dialog", name="全局命令").wait_for()
                page.get_by_role("button", name="关闭全局命令").click()
                page.locator('.space-rail-item[data-space-id="learning"]').click()
                page.get_by_role("main").get_by_role("heading", name="学习").wait_for()
                assert page.get_by_role("button", name="视觉课件").count() == 0
                assert page.get_by_role("button", name="空间记忆").count() == 0
                page.get_by_role("button", name="展开活动坞").click()
                assert page.get_by_role("button", name="取消投递（不可用）").count() == 0

                screenshot = ARTIFACTS / f"canonical-shell-{width}x{height}.png"
                page.screenshot(path=str(screenshot), full_page=True)
                viewports[f"{width}x{height}"] = {
                    "geometry": geometry,
                    "screenshot": str(screenshot.relative_to(ROOT)),
                }
                context.close()
            browser.close()
    finally:
        stop_vite(process, log)

    assert not errors, errors
    tree = subprocess.check_output(["git", "write-tree"], cwd=ROOT, text=True).strip()
    report = {
        "schema": "archeaxis/canonical-browser-smoke/v2",
        "status": "PASS",
        "candidate_tree": tree,
        "errors": errors,
        "viewports": viewports,
    }
    output = ARTIFACTS / "canonical-browser-smoke.json"
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
