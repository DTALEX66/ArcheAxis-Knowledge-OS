"""Drive the real isolated Tauri WebView2 window; never substitute a browser server.

CDP automation is engineering evidence, not native IME, WebDriver or human review signoff.
"""

from __future__ import annotations

import argparse
import contextlib
import ctypes
import json
import os
import socket
import subprocess
import time
import uuid
from ctypes import wintypes
from pathlib import Path
from urllib.request import urlopen

from aaos01_office_runtime_loop import REPO, identity
from playwright.sync_api import sync_playwright


def close_window(child):
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    user32 = ctypes.windll.user32
    user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    user32.GetWindowThreadProcessId.restype = wintypes.DWORD
    user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
    user32.PostMessageW.restype = wintypes.BOOL
    user32.IsWindowVisible.argtypes = [wintypes.HWND]
    user32.IsWindowVisible.restype = wintypes.BOOL
    user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user32.GetWindowTextW.restype = ctypes.c_int
    user32.EnumWindows.argtypes = [callback_type, wintypes.LPARAM]
    user32.EnumWindows.restype = wintypes.BOOL
    posted = []

    def visit(handle, _):
        pid = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(handle, ctypes.byref(pid))
        if pid.value == child.pid and user32.IsWindowVisible(handle):
            title = ctypes.create_unicode_buffer(512)
            user32.GetWindowTextW(handle, title, len(title))
            if title.value.startswith(("星环知识平台", "ArcheAxis")):
                posted.append(bool(user32.PostMessageW(handle, 0x0010, 0, 0)))
        return True

    callback = callback_type(visit)
    ctypes.windll.user32.EnumWindows(callback, 0)
    if not posted or not all(posted):
        raise RuntimeError("Owned visible window WM_CLOSE could not be posted")
    child.wait(timeout=15)


def exit_observed_window(page, child):
    """Use the product exit command while CDP owns a WebView connection.

    WM_CLOSE qualification is recorded separately without an attached observer.
    A closed transport is expected only when the actual owned process exits.
    """
    with contextlib.suppress(Exception):
        page.evaluate("() => window.__TAURI__.core.invoke('exit_application')")
    child.wait(timeout=15)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", type=Path, required=True)
    args = parser.parse_args()
    host = args.host.resolve()
    work = REPO / ".project-local/task-runtime/aaos01-tauri-window" / uuid.uuid4().hex
    work.mkdir(parents=True)
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    env = dict(os.environ)
    env.pop("ARCHEAXIS_DEV_EXTERNAL_BACKEND", None)
    env["ARCHEAXIS_PORTABLE_ROOT"] = str(work / "data")
    env["WEBVIEW2_USER_DATA_FOLDER"] = str(work / "webview")
    env["WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS"] = (
        f"--remote-debugging-port={port} --remote-debugging-address=127.0.0.1"
    )
    receipt = {
        "ok": False,
        "host": identity(host),
        "evidence_level": "REAL_TAURI_WINDOW_CDP_AUTOMATION",
        "conditions": {
            "development_server": False,
            "isolated_data": str(work / "data"),
            "ui_startup_p95_budget_seconds": 3,
            "idle_tree_budget_bytes": 1073741824,
        },
        "limitations": [
            "Candidate window, not NSIS installed journey",
            "CDP, not Tauri WebDriver",
            "Programmatic Chinese text, not physical native IME",
            "No human review decision performed",
        ],
    }
    child = None
    browser = None
    try:
        with sync_playwright() as playwright:

            def launch():
                nonlocal child
                began = time.monotonic()
                child = subprocess.Popen([str(host)], cwd=host.parent, env=env)
                receipt.setdefault("started_pids", []).append(child.pid)
                (work / "receipt.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8")
                deadline = began + 40
                while time.monotonic() < deadline:
                    if child.poll() is not None:
                        raise RuntimeError("Tauri exited before WebView readiness")
                    try:
                        with urlopen(
                            f"http://127.0.0.1:{port}/json/version", timeout=1
                        ) as response:
                            version = json.load(response)
                        break
                    except OSError:
                        time.sleep(0.2)
                else:
                    raise TimeoutError("Owned WebView2 CDP readiness timeout")
                browser = playwright.chromium.connect_over_cdp(f"http://127.0.0.1:{port}")
                deadline = time.monotonic() + 30
                while time.monotonic() < deadline:
                    pages = [p for c in browser.contexts for p in c.pages if "tauri" in p.url]
                    if pages:
                        break
                    time.sleep(0.1)
                else:
                    raise RuntimeError("Owned Tauri page unavailable")
                page = pages[0]
                page.get_by_role("button", name="资料库", exact=True).wait_for(timeout=30000)
                receipt.setdefault("launches", []).append(
                    {
                        "pid": child.pid,
                        "url": page.url,
                        "ready_seconds": time.monotonic() - began,
                        "webview_version": version.get("Browser"),
                    }
                )
                (work / f"snapshot-{len(receipt['launches'])}.txt").write_text(
                    page.locator("body").inner_text(), encoding="utf-8"
                )
                return browser, page

            browser, page = launch()
            info = page.evaluate("async () => await window.__TAURI__.core.invoke('backend_info')")
            assert info == {"ready": True}, "UI credential/address projection must be absent"
            page.get_by_role("button", name="资料库", exact=True).click()
            sample = work / "真实窗口证据.txt"
            sample.write_text(
                "中文真实窗口阅读证据 AAOS native window evidence.\n", encoding="utf-8"
            )
            page.get_by_label("导入原件", exact=True).set_input_files(sample)
            page.get_by_role("button", name=sample.name, exact=True).wait_for(timeout=30000)
            page.get_by_role("button", name=sample.name, exact=True).click()
            page.get_by_label("原件正文", exact=True).wait_for(timeout=15000)
            assert "中文真实窗口阅读证据" in page.get_by_label("原件正文", exact=True).inner_text()
            # Snapshot before choosing the rendered editor control.
            (work / "snapshot-open.txt").write_text(
                page.locator("body").inner_text(), encoding="utf-8"
            )
            page.get_by_role("button", name="建立版本化草稿", exact=True).click()
            editor = page.locator(".tiptap[contenteditable=true]")
            editor.wait_for(timeout=15000)
            editor.fill("中文自动保存与重启读回 evidence")
            page.get_by_text("已保存", exact=False).first.wait_for(timeout=15000)
            page.screenshot(path=str(work / "saved.png"))
            exit_observed_window(page, child)
            browser.close()
            browser = None
            child = None
            browser, page = launch()
            page.get_by_role("button", name="资料库", exact=True).click()
            page.get_by_role("button", name=sample.name, exact=True).click()
            editor = page.locator(".tiptap[contenteditable=true]")
            editor.wait_for(timeout=15000)
            assert "中文自动保存与重启读回 evidence" in editor.inner_text()
            page.screenshot(path=str(work / "restart.png"))
            receipt["steps"] = [
                "real Tauri window and native finite bridge",
                "no token/address in UI projection",
                "file import and original reading",
                "Chinese autosave",
                "product exit command and restart persisted content",
            ]
            receipt["ok"] = True
            exit_observed_window(page, child)
            browser.close()
            browser = None
            child = None
    except BaseException as error:
        receipt["ok"] = False
        receipt["error"] = f"{type(error).__name__}: {error}"
        raise
    finally:
        if child is not None and child.poll() is None:
            try:
                if browser is not None:
                    browser.close()
                close_window(child)
            except BaseException as error:
                receipt["cleanup_error"] = str(error)
                child.terminate()
                child.wait(timeout=10)
        (work / "receipt.json").write_text(
            json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(
            json.dumps(
                {"ok": receipt["ok"], "receipt": str(work / "receipt.json")}, ensure_ascii=False
            )
        )


if __name__ == "__main__":
    main()
