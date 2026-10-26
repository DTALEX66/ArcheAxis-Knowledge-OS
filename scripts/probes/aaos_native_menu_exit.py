"""Regress native context-menu exit on an isolated Windows Tauri candidate.

Run through scripts/runtime/dev.py with --host and --build-receipt. This opens a
real OS menu using a synthetic DOM MouseEvent, observes this process's #32768
popup window, then requests the actual exit_application command. It sends no
mouse/keyboard input and does not qualify OS menu-item selection or Green.

--diagnose permits a historical build receipt, and uses targeted WM_CANCELMODE
only to recover a reproduced exit failure. Such recovery never counts as PASS.
"""
from __future__ import annotations

import argparse
import contextlib
import ctypes
import hashlib
import importlib.util
import json
import os
import socket
import subprocess
import sys
import time
import traceback
from ctypes import wintypes
from pathlib import Path
from urllib.request import ProxyHandler, build_opener

ROOT = Path(__file__).resolve().parents[2]
_dev_spec = importlib.util.spec_from_file_location("aaos_menu_exit_dev", ROOT / "scripts/runtime/dev.py")
assert _dev_spec is not None and _dev_spec.loader is not None
dev = importlib.util.module_from_spec(_dev_spec)
sys.modules[_dev_spec.name] = dev
_dev_spec.loader.exec_module(dev)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def port_open(port: int) -> bool:
    with socket.socket() as sock:
        sock.settimeout(.2)
        return sock.connect_ex(("127.0.0.1", port)) == 0


class OwnedWindows:
    """Enumerate only our PID; never cancel a foreign, desktop or broadcast HWND."""

    def __init__(self, pid: int):
        self.pid = pid
        self.user = ctypes.WinDLL("user32", use_last_error=True)
        self.callback = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        self.user.EnumWindows.argtypes = [self.callback, wintypes.LPARAM]
        self.user.EnumWindows.restype = wintypes.BOOL
        self.user.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
        self.user.GetWindowThreadProcessId.restype = wintypes.DWORD
        self.user.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
        self.user.GetClassNameW.restype = ctypes.c_int
        self.user.IsWindowVisible.argtypes = [wintypes.HWND]
        self.user.IsWindowVisible.restype = wintypes.BOOL
        self.user.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
        self.user.PostMessageW.restype = wintypes.BOOL

    def list(self) -> list[dict]:
        result = []

        @self.callback
        def collect(hwnd, _):
            owner = wintypes.DWORD()
            thread = self.user.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
            if owner.value == self.pid:
                name = ctypes.create_unicode_buffer(256)
                self.user.GetClassNameW(hwnd, name, 256)
                result.append({"hwnd": int(hwnd), "class": name.value,
                               "visible": bool(self.user.IsWindowVisible(hwnd)), "thread": thread})
            return True

        self.user.EnumWindows(collect, 0)
        return result

    def cancel_menu_for_cleanup(self) -> list[dict]:
        posted = []
        for item in self.list():
            if item["visible"] and item["class"] == "Tauri Window":
                # Recheck PID immediately before posting in case a handle was recycled.
                owner = wintypes.DWORD()
                self.user.GetWindowThreadProcessId(item["hwnd"], ctypes.byref(owner))
                if owner.value == self.pid:
                    posted.append({"hwnd": item["hwnd"], "posted": bool(
                        self.user.PostMessageW(item["hwnd"], 0x001F, 0, 0))})
        return posted


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", type=Path, required=True)
    parser.add_argument("--build-receipt", type=Path, required=True)
    parser.add_argument("--diagnose", action="store_true")
    parser.add_argument("--exit-timeout", type=float, default=12)
    args = parser.parse_args()
    if os.name != "nt":
        parser.error("Windows native host required")
    if not 2 <= args.exit_timeout <= 30:
        parser.error("exit timeout must be between 2 and 30 seconds")
    paths = dev.layout(ROOT, Path(os.environ["ARCHEAXIS_RUN_ROOT"]).name)
    run = dev.safe_path(Path(os.environ["ARCHEAXIS_RUN_ROOT"]))
    if run != paths["run"]:
        raise ValueError("foreign run root")
    host = dev.safe_path(args.host)
    build_path = dev.safe_path(args.build_receipt)
    host.relative_to(paths["dev"])
    build_path.relative_to(paths["dev"] / "runs")
    if not host.is_file() or host.name != "ArcheAxis.exe":
        raise ValueError("expected project-owned candidate ArcheAxis.exe")
    build = json.loads(build_path.read_text(encoding="utf-8"))
    if build.get("mode") != "tauri" or build.get("exit_code") != 0 or not build.get("source_consistent"):
        raise ValueError("successful source-consistent native build receipt required")
    source_match = dev.worktree_identity(ROOT)[1] == build["source_patch_sha256"]
    if not source_match and not args.diagnose:
        raise ValueError("source differs from build; rebuild or use --diagnose for historical evidence")
    out = paths["artifacts"] / "native-menu-exit"
    out.mkdir(exist_ok=False)
    report = {"schema": "archeaxis.native-menu-exit/v1", "status": "RUNNING",
              "evidence": "REAL_TAURI_AND_CORE_WITH_SYNTHETIC_DOM_CONTEXT_EVENT",
              "host": str(host), "host_sha256": sha(host),
              "core_sha256": sha(host.parent / "core/archeaxis-api.exe"),
              "build_receipt": str(build_path), "build_receipt_sha256": sha(build_path),
              "source_matches_build": source_match, "diagnostic_only": args.diagnose,
              "limits": ["No OS mouse or keyboard input", "No actual native menu-item click qualification",
                         "Isolated empty test workspace, not Green or Owner acceptance",
                         "Debug-port cleanup is checked after the attached Playwright driver stops"], "cases": []}

    def save():
        (out / "native-menu-exit.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    from playwright.sync_api import sync_playwright
    opener = build_opener(ProxyHandler({}))
    with sync_playwright() as pw:
        for mode in ["baseline", "popup"]:
            case = {"mode": mode, "status": "RUNNING", "page_errors": []}
            report["cases"].append(case)
            process = browser = page = None
            with socket.socket() as sock:
                sock.bind(("127.0.0.1", 0))
                port = sock.getsockname()[1]
            workspace = paths["tmp"] / f"{mode}-workspace"
            workspace.mkdir(exist_ok=False)
            env = dict(os.environ)
            env.update(ARCHEAXIS_PORTABLE_ROOT=str(workspace),
                       WEBVIEW2_USER_DATA_FOLDER=str(paths["tmp"] / f"{mode}-webview"),
                       ARCHEAXIS_WEBDRIVER_CDP_PORT=str(port),
                       WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS=(
                           f"--remote-debugging-port={port} --remote-debugging-address=127.0.0.1"))
            for name in ["ARCHEAXIS_DEV_EXTERNAL_BACKEND", "ARCHEAXIS_EXTERNAL_DEV"]:
                env.pop(name, None)
            log_path = paths["logs"] / f"native-menu-exit-{mode}.log"
            with log_path.open("x", encoding="utf-8") as log:
                try:
                    if sha(host) != report["host_sha256"]:
                        raise ValueError("candidate changed during probe")
                    process = subprocess.Popen([str(host)], cwd=host.parent, env=env,
                                               stdout=log, stderr=subprocess.STDOUT)
                    case.update(pid=process.pid, port=port, workspace=str(workspace))
                    owned = OwnedWindows(process.pid)
                    deadline = time.monotonic() + 45
                    while True:
                        if process.poll() is not None:
                            raise RuntimeError("host exited before CDP")
                        try:
                            with opener.open(f"http://127.0.0.1:{port}/json/version", timeout=1) as response:
                                case["browser"] = json.load(response).get("Browser")
                            break
                        except OSError as error:
                            if time.monotonic() > deadline:
                                raise TimeoutError("owned CDP unavailable") from error
                            time.sleep(.2)
                    browser = pw.chromium.connect_over_cdp(f"http://127.0.0.1:{port}")
                    page = browser.contexts[0].pages[0]
                    page.on("pageerror", lambda error, result=case: result["page_errors"].append(str(error)))
                    page.wait_for_function("typeof window.__TAURI__?.core?.invoke==='function'")
                    page.wait_for_function("async()=> (await window.__TAURI__.core.invoke('backend_info'))?.ready===true", timeout=45000)
                    page.get_by_role("dialog", name="首次使用引导").wait_for()
                    page.evaluate("()=>document.querySelector('.first-use-guide-progress button')?.click()")
                    page.get_by_role("dialog", name="首次使用引导").wait_for(state="hidden")
                    page.wait_for_timeout(400)
                    case["before_windows"] = owned.list()
                    if mode == "popup":
                        page.locator(".stitch-workbench-summary").evaluate("""element => {
                          const rect = element.getBoundingClientRect();
                          element.dispatchEvent(new MouseEvent('contextmenu', {
                            clientX: rect.x + 12, clientY: rect.y + 12, button: 2,
                            bubbles: true, cancelable: true, view: window
                          }));
                        }""")
                        deadline = time.monotonic() + 5
                        while True:
                            case["popup_windows"] = owned.list()
                            if any(item["class"] == "#32768" and item["visible"] for item in case["popup_windows"]):
                                break
                            if time.monotonic() > deadline:
                                raise AssertionError("actual owned native popup not observed")
                            page.wait_for_timeout(100)
                        case["dom_fallback"] = page.get_by_role("menu", name="当前位置操作").count()
                        if case["dom_fallback"]:
                            raise AssertionError("DOM fallback cannot qualify native popup")
                    started = time.monotonic()
                    try:
                        page.evaluate("()=>window.__TAURI__.core.invoke('exit_application')")
                    except Exception as error:
                        case["exit_invoke_error"] = str(error)[:300]
                    case["exit_code"] = process.wait(timeout=args.exit_timeout)
                    case["exit_elapsed_seconds"] = round(time.monotonic() - started, 3)
                    case["status"] = "PASS" if case["exit_code"] == 0 else "FAIL_EXIT_CODE"
                except BaseException:
                    case["status"] = "FAIL"
                    case["exception"] = traceback.format_exc()
                finally:
                    if process and process.poll() is None:
                        case["cancel_for_cleanup"] = OwnedWindows(process.pid).cancel_menu_for_cleanup()
                        try:
                            process.wait(timeout=4)
                        except subprocess.TimeoutExpired:
                            process.terminate()
                            process.wait(timeout=10)
                            case["forced_cleanup"] = True
                    if browser:
                        with contextlib.suppress(Exception):
                            browser.close()
                    case["exit_code"] = process.poll() if process else None
            case["cdp_port_closed_while_driver_attached"] = not port_open(port)
            case["core_graceful"] = '"outcome":"GRACEFUL"' in log_path.read_text(encoding="utf-8", errors="replace")
            if case["status"] == "PASS" and not case["core_graceful"]:
                case["status"] = "PARTIAL_CLEANUP"
            save()
            print(json.dumps({"mode": mode, "status": case["status"], "exit_code": case["exit_code"],
                              "seconds": case.get("exit_elapsed_seconds")}, ensure_ascii=False), flush=True)
    for case in report["cases"]:
        deadline = time.monotonic() + 5
        while case.get("port") and port_open(case["port"]) and time.monotonic() < deadline:
            time.sleep(.1)
        case["cdp_port_closed"] = not case.get("port") or not port_open(case["port"])
        if case["status"] == "PASS" and not case["cdp_port_closed"]:
            case["status"] = "PARTIAL_CLEANUP"
    report["candidate_unchanged"] = sha(host) == report["host_sha256"] and sha(build_path) == report["build_receipt_sha256"]
    passed = all(case["status"] == "PASS" for case in report["cases"]) and report["candidate_unchanged"]
    report["status"] = ("DIAGNOSTIC_PASS" if args.diagnose else "PASS_NATIVE_MENU_EXIT") if passed else "FAIL_NATIVE_MENU_EXIT"
    save()
    print(json.dumps({"status": report["status"], "report": str(out / "native-menu-exit.json")}, ensure_ascii=False), flush=True)
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
