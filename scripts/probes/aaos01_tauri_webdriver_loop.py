"""Real candidate Tauri WebDriver engineering probe; no installed/human signoff."""

from __future__ import annotations

import argparse
import base64
import ctypes
import hashlib
import json
import os
import socket
import subprocess
import time
import traceback
import uuid
from contextlib import suppress
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

from aaos01_office_runtime_loop import REPO, identity, load


def owned_process_rows(rows, root_pid):
    """Reject recycled parent PIDs using observed creation times."""
    indexed = {row["pid"]: row for row in rows}
    if root_pid not in indexed:
        raise RuntimeError("Owned driver identity unavailable")
    owned = {root_pid}
    changed = True
    while changed:
        changed = False
        for row in rows:
            parent = indexed.get(row["parent_pid"])
            if parent and parent["pid"] in owned and row["created"] >= parent["created"] and row["pid"] not in owned:
                owned.add(row["pid"])
                changed = True
    return [indexed[pid] for pid in sorted(owned)]


def native_process_rows():
    """Win32 metadata snapshot, without CIM, command lines or profile contents."""
    from ctypes import wintypes

    class Entry(ctypes.Structure):
        _fields_ = [("size", wintypes.DWORD), ("usage", wintypes.DWORD),
                    ("pid", wintypes.DWORD), ("heap", ctypes.c_size_t),
                    ("module", wintypes.DWORD), ("threads", wintypes.DWORD),
                    ("parent", wintypes.DWORD), ("priority", wintypes.LONG),
                    ("flags", wintypes.DWORD), ("name", wintypes.WCHAR * 260)]

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateToolhelp32Snapshot.restype = ctypes.c_void_p
    kernel.OpenProcess.restype = ctypes.c_void_p
    kernel.CloseHandle.argtypes = [ctypes.c_void_p]
    snapshot = kernel.CreateToolhelp32Snapshot(2, 0)
    if snapshot == ctypes.c_void_p(-1).value:
        raise ctypes.WinError(ctypes.get_last_error())
    rows = []
    entry = Entry()
    entry.size = ctypes.sizeof(entry)
    try:
        found = kernel.Process32FirstW(ctypes.c_void_p(snapshot), ctypes.byref(entry))
        while found:
            handle = kernel.OpenProcess(0x1000, False, entry.pid)
            if handle:
                try:
                    created, exited, system, user = (wintypes.FILETIME() for _ in range(4))
                    if kernel.GetProcessTimes(ctypes.c_void_p(handle), ctypes.byref(created), ctypes.byref(exited), ctypes.byref(system), ctypes.byref(user)):
                        rows.append({"pid": entry.pid, "parent_pid": entry.parent, "name": entry.name,
                                     "created": (created.dwHighDateTime << 32) | created.dwLowDateTime})
                finally:
                    kernel.CloseHandle(handle)
            found = kernel.Process32NextW(ctypes.c_void_p(snapshot), ctypes.byref(entry))
    finally:
        kernel.CloseHandle(snapshot)
    return rows


def profile_metadata(paths):
    return [{"path": str(path), "exists": path.exists(),
             "ebwebview_exists": (path / "EBWebView").exists(),
             "devtools_active_port_exists": (path / "DevToolsActivePort").exists(),
             "ebwebview_devtools_active_port_exists": (path / "EBWebView" / "DevToolsActivePort").exists()}
            for path in paths]


def process_elevation(pid):
    """Read the elevation boolean of an already-owned process, not token data."""
    from ctypes import wintypes

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    security = ctypes.WinDLL("advapi32", use_last_error=True)
    kernel.OpenProcess.restype = ctypes.c_void_p
    kernel.CloseHandle.argtypes = [ctypes.c_void_p]
    security.OpenProcessToken.argtypes = [ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(wintypes.HANDLE)]
    security.GetTokenInformation.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
    process_handle = kernel.OpenProcess(0x1000, False, pid)
    if not process_handle:
        return {"elevation_verified": False, "error": ctypes.get_last_error()}
    access_handle = wintypes.HANDLE()
    try:
        if not security.OpenProcessToken(process_handle, 0x0008, ctypes.byref(access_handle)):
            return {"elevation_verified": False, "error": ctypes.get_last_error()}
        elevated, returned = wintypes.DWORD(), wintypes.DWORD()
        if not security.GetTokenInformation(access_handle, 20, ctypes.byref(elevated), ctypes.sizeof(elevated), ctypes.byref(returned)):
            return {"elevation_verified": False, "error": ctypes.get_last_error()}
        return {"elevation_verified": True, "elevated": bool(elevated.value)}
    finally:
        if access_handle:
            kernel.CloseHandle(access_handle)
        kernel.CloseHandle(process_handle)



def owned_attach_diagnostics(root_pid, root_created, cdp_port, folders):
    """Owned metadata only; never persist complete command lines or environment."""
    rows = native_process_rows()
    root = next((row for row in rows if row["pid"] == root_pid), None)
    if root is None or root["created"] != root_created:
        raise RuntimeError("Owned attach root missing or PID creation mismatch")
    owned = owned_process_rows(rows, root_pid)
    ids = ",".join(str(row["pid"]) for row in owned)
    script = (
        "$ErrorActionPreference='Stop'; [Console]::OutputEncoding=[Text.UTF8Encoding]::new($false); $ids=@(" + ids + "); "
        "$processes=@(Get-CimInstance Win32_Process -Filter ("
        "$ids.ForEach({ 'ProcessId=' + $_ }) -join ' OR ') | ForEach-Object { "
        "$cmd=$_.CommandLine; $allowed=$_.Name -in @('ArcheAxis.exe','archeaxis-api.exe','python.exe','pythonw.exe','msedgewebview2.exe'); "
        "[pscustomobject]@{pid=$_.ProcessId; executable_path=if($allowed){$_.ExecutablePath}else{$null}; "
        "command_metadata_available=($null -ne $cmd); "
        "debug_port_matches=($cmd -match '--remote-debugging-port=" + str(cdp_port) + "(?:[^0-9]|$)'); "
        "debug_address_loopback=($cmd -match '--remote-debugging-address=127\\.0\\.0\\.1(?:[^0-9.]|$)'); "
        "has_user_data_dir=($cmd -match '--user-data-dir(?:=|\\s)') } }); "
        "$listeners=@(Get-NetTCPConnection -State Listen -ErrorAction Stop | Where-Object { "
        "($_.LocalPort -eq " + str(cdp_port) + " -or $_.OwningProcess -in $ids) -and $_.LocalAddress -in @('127.0.0.1','::1') "
        "} | Select-Object LocalAddress,LocalPort,OwningProcess); "
        "@{processes=$processes; loopback_listeners=$listeners} | ConvertTo-Json -Depth 5 -Compress"
    )
    result = subprocess.run(["powershell.exe", "-NoProfile", "-Command", script],
                            capture_output=True, text=True, encoding="utf-8", errors="replace", check=True, timeout=15)
    metadata = json.loads(result.stdout)
    after = {row["pid"]: row for row in native_process_rows()}
    if any(row["pid"] not in after or after[row["pid"]]["created"] != row["created"] for row in owned):
        raise RuntimeError("Owned attach process identity changed during metadata collection")
    indexed = {row["pid"]: row for row in owned}
    if {row["pid"] for row in metadata["processes"]} != set(indexed):
        raise RuntimeError("Incomplete owned attach process metadata")
    for row in metadata["processes"]:
        row.update({"created": indexed[row["pid"]]["created"], "name": indexed[row["pid"]]["name"]})
    from ctypes import wintypes
    user = ctypes.WinDLL("user32", use_last_error=True)
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    user.EnumWindows.argtypes = [callback_type, wintypes.LPARAM]
    user.IsWindowVisible.argtypes = [wintypes.HWND]
    user.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    user.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    windows = []
    @callback_type
    def inspect_window(hwnd, _):
        pid = wintypes.DWORD()
        user.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value in indexed and user.IsWindowVisible(hwnd):
            name = ctypes.create_unicode_buffer(256)
            user.GetClassNameW(hwnd, name, len(name))
            windows.append({"hwnd": int(hwnd), "pid": pid.value,
                            "created": indexed[pid.value]["created"], "class_name": name.value})
        return True
    if not user.EnumWindows(inspect_window, 0):
        raise ctypes.WinError(ctypes.get_last_error())
    profiles = []
    def walk_failed(error):
        raise error
    for folder in folders:
        count = 0
        truncated = False
        if folder.exists():
            for _, directories, files in os.walk(folder, followlinks=False, onerror=walk_failed):
                directories[:] = [name for name in directories
                                  if not (Path(_) / name).is_symlink() and not (Path(_) / name).is_junction()]
                count += len(files)
                if count >= 10000:
                    truncated = True
                    break
        profiles.append({"path": str(folder), "exists": folder.is_dir(),
                         "file_count": count, "count_truncated": truncated})
    return {"collection_verified": True, "owned_processes": owned,
            "process_metadata": metadata["processes"], "visible_windows": windows,
            "loopback_listeners": metadata["loopback_listeners"], "profiles": profiles}



def loopback_urlopen(request, *, timeout):
    """This probe permits HTTP only to its explicit local loopback listeners."""
    url = request.full_url if isinstance(request, Request) else request
    parsed = urlsplit(url)
    if parsed.scheme != "http" or parsed.hostname != "127.0.0.1" or parsed.username or parsed.password:
        raise ValueError("Non-loopback probe HTTP target rejected")
    class LoopbackRedirectHandler(HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            target = urlsplit(newurl)
            if target.scheme != "http" or target.hostname != "127.0.0.1" or target.username or target.password:
                raise ValueError("Non-loopback probe HTTP redirect rejected")
            return super().redirect_request(req, fp, code, msg, headers, newurl)
    return build_opener(ProxyHandler({}), LoopbackRedirectHandler()).open(request, timeout=timeout)


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", type=Path, required=True)
    parser.add_argument("--driver", type=Path)
    parser.add_argument("--native-driver", type=Path)
    parser.add_argument(
        "--session-timeout",
        type=int,
        default=120,
        help="Bounded cold WebView2 handshake timeout; failure remains nonzero",
    )
    parser.add_argument(
        "--installer",
        type=Path,
        help="Exact parent-verified NSIS installer identity; does not itself establish installation",
    )
    args = parser.parse_args()
    if not 45 <= args.session_timeout <= 180:
        parser.error("session timeout must be between 45 and 180 seconds")
    host = args.host.resolve()
    tools = REPO / ".project-local/task-runtime/aaos01-tools"
    driver = (args.driver or tools / "tauri-driver-2.1.0/bin/tauri-driver.exe").resolve()
    edge = (args.native_driver or tools / "edge-154.0.4258.48/msedgedriver.exe").resolve()
    work = REPO / ".project-local/task-runtime/aaos01-webdriver" / uuid.uuid4().hex
    work.mkdir(parents=True)
    native_log = work / "native-driver.log"
    wrapper = work / "native-driver.cmd"
    # Tauri forwards only its owned --port/--host arguments. The native driver
    # otherwise discards diagnostics; capture them in this probe's own root.
    wrapper.write_text(
        '@echo off\r\n"'
        + str(edge).replace("%", "%%")
        + '" --log-level=INFO --log-path="'
        + str(native_log).replace("%", "%%")
        + '" %*\r\nexit /b %ERRORLEVEL%\r\n',
        encoding="utf-8",
    )
    port, native = free_port(), free_port()
    env = dict(os.environ)
    for key in (
        "ARCHEAXIS_DEV_EXTERNAL_BACKEND",
        "ARCHEAXIS_WEBDRIVER_CDP_PORT",
        "WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS",
        "WEBVIEW2_USER_DATA_FOLDER",
    ):
        env.pop(key, None)
    env["ARCHEAXIS_PORTABLE_ROOT"] = str(work / "data")
    receipt = {
        "ok": False,
        "evidence_level": "REAL_TAURI_WEBDRIVER_CANDIDATE",
        "host": identity(host),
        "driver": identity(driver),
        "edge": identity(edge),
        "data_root": str(work / "data"),
        "steps": [],
        "conditions": {
            "new_session_timeout_seconds": args.session_timeout,
            "ordinary_request_timeout_seconds": 45,
            "proxy_environment_present": any(key.lower() in ("http_proxy", "https_proxy", "all_proxy", "no_proxy") for key in os.environ),
            "local_http_transport": "explicit_loopback_no_proxy",
            "cdp_arguments_transport": "validated_port_via_native_webview_api",
            "webview_user_data_folder": str(work / "webview"),
            "webview_user_data_folder_owner": "Owned host per-process WEBVIEW2_USER_DATA_FOLDER",
            "webview_user_data_folder_strategy": "Fresh session-N profile per launch; canonical product data root unchanged",
        },
        "limitations": [
            "Candidate executable, not NSIS installed journey",
            "Programmatic Chinese text, not physical native IME",
            "No human review decision or approval performed",
            "One engineering run, not whole UI P95 acceptance",
        ],
    }
    if args.installer:
        receipt["installer"] = identity(args.installer.resolve())
        receipt["installation_context"] = (
            "Parent installer verifier supplies installed host; this probe hashes installer only"
        )
    session = None
    process = None
    owned_host = None
    owned_host_records = []
    attach_ports = []
    owned_tree_collection_verified = False
    log = (work / "driver.log").open("wb")

    def request(method, path, body=None):
        data = None if body is None else json.dumps(body).encode()
        req = Request(
            f"http://127.0.0.1:{port}" + path,
            data=data,
            method=method,
            headers={"Content-Type": "application/json"},
        )
        try:
            timeout = args.session_timeout if method == "POST" and path == "/session" else 45
            with loopback_urlopen(req, timeout=timeout) as response:
                value = json.load(response)["value"]
        except HTTPError as error:
            body = error.read().decode("utf-8", "replace")
            raise RuntimeError(f"WebDriver {method} {path}: {body}") from error
        if isinstance(value, dict) and value.get("error"):
            raise RuntimeError(value)
        return value

    def js(script, arguments=None):
        return request(
            "POST", f"/session/{session}/execute/sync", {"script": script, "args": arguments or []}
        )

    def ui_element(using, selector):
        value = request("POST", f"/session/{session}/element", {"using": using, "value": selector})
        return value["element-6066-11e4-a52e-4f735466cecf"]

    def ui_click(text, scope=""):
        selector = f"{scope}//button[normalize-space(.)='{text}']"
        element = ui_element("xpath", selector)
        request("POST", f"/session/{session}/element/{element}/click", {})
        receipt.setdefault("ui_selectors", []).append({"action": "click", "selector": selector})

    def ui_type(selector, text):
        element = ui_element("css selector", selector)
        request("POST", f"/session/{session}/element/{element}/value", {"text": text})
        receipt.setdefault("ui_selectors", []).append({"action": "type", "selector": selector})

    def bridge(operation, payload=None):
        value = request(
            "POST",
            f"/session/{session}/execute/async",
            {
                "script": "const cb=arguments[arguments.length-1];window.__TAURI__.core.invoke('core_command',{request:{operation:arguments[0],payload:arguments[1]}}).then(v=>cb({ok:true,value:v}),e=>cb({ok:false,error:String(e)}));",
                "args": [operation, payload or {}],
            },
        )
        assert value["ok"], value
        reply = value["value"]
        assert 200 <= reply["status"] < 300, reply
        return reply["body"]

    def native_command(command, payload=None):
        value = request(
            "POST",
            f"/session/{session}/execute/async",
            {
                "script": "const cb=arguments[arguments.length-1];window.__TAURI__.core.invoke(arguments[0],arguments[1]).then(v=>cb({ok:true,value:v}),e=>cb({ok:false,error:String(e)}));",
                "args": [command, payload or {}],
            },
        )
        assert value["ok"], value
        return value["value"]

    def wait(script):
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            if js(script):
                return
            time.sleep(0.15)
        raise TimeoutError("Window assertion deadline: " + script)

    def screenshot(name):
        content = base64.b64decode(request("GET", f"/session/{session}/screenshot"))
        assert content.startswith(b"\x89PNG") and len(content) > 100
        (work / name).write_bytes(content)
        receipt.setdefault("screenshots", []).append(identity(work / name))

    def launch():
        nonlocal session, owned_host, owned_tree_collection_verified
        began = time.monotonic()
        folder = work / "webview" / f"session-{len(receipt.get('launch_attempts', [])) + 1}"
        folder.mkdir(parents=True, exist_ok=False)
        cdp_port = free_port()
        attach_ports.append(cdp_port)
        host_env = dict(env)
        host_env["WEBVIEW2_USER_DATA_FOLDER"] = str(folder)
        host_env["WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS"] = f"--remote-debugging-port={cdp_port} --remote-debugging-address=127.0.0.1"
        host_env["ARCHEAXIS_WEBDRIVER_CDP_PORT"] = str(cdp_port)
        owned_host = subprocess.Popen([str(host)], cwd=host.parent, env=host_env)
        receipt.setdefault("owned_host_pids", []).append(owned_host.pid)
        root_identity = next((row for row in native_process_rows() if row["pid"] == owned_host.pid), None)
        if root_identity is None:
            raise RuntimeError("Owned attach host creation identity unavailable")
        owned_host_records.append(root_identity)
        receipt.setdefault("launch_attempts", []).append({"user_data_folder": str(folder), "host_pid": owned_host.pid, "host_created": root_identity["created"], "mode":"owned_prelaunch_attach"})
        deadline = began + 40
        while True:
            if owned_host.poll() is not None:
                raise RuntimeError("Owned host exited before CDP")
            try:
                with loopback_urlopen(f"http://127.0.0.1:{cdp_port}/json/version", timeout=1) as response:
                    version = json.load(response)
                break
            except OSError as connection_error:
                nested_reason = getattr(connection_error, "reason", None)
                receipt["launch_attempts"][-1]["last_cdp_connection_error"] = {
                    "type": type(connection_error).__name__, "errno": getattr(connection_error, "errno", None),
                    "reason_type": type(nested_reason).__name__ if nested_reason is not None else None,
                    "reason_errno": getattr(nested_reason, "errno", None)}
                if time.monotonic() >= deadline:
                    try:
                        diagnostic = owned_attach_diagnostics(owned_host.pid, root_identity["created"], cdp_port, [folder, work / "data"])
                        owned_host_records.extend(diagnostic["owned_processes"])
                        owned_tree_collection_verified = True
                        receipt["launch_attempts"][-1]["timeout_diagnostics"] = diagnostic
                    except BaseException as diagnostic_error:
                        receipt["launch_attempts"][-1]["timeout_diagnostics"] = {
                            "collection_verified": False, "error_type": type(diagnostic_error).__name__,
                            "traceback": traceback.format_exc()}
                    raise TimeoutError("Owned attach CDP unavailable after 40 seconds") from None
                time.sleep(.2)
        edge_version = subprocess.check_output([str(edge), "--version"], text=True, timeout=10).strip()
        assert edge_version.startswith("Microsoft Edge WebDriver " + version["Browser"].split("/")[1] + " "), "Runtime/driver version mismatch"
        owned = owned_process_rows(native_process_rows(), owned_host.pid)
        owned_host_records.extend(owned)
        owned_tree_collection_verified = True
        query = subprocess.check_output(["powershell.exe", "-NoProfile", "-Command", f"@(Get-NetTCPConnection -State Listen -LocalPort {cdp_port} | Select-Object LocalAddress,OwningProcess) | ConvertTo-Json -Compress"], text=True, timeout=10)
        listeners = json.loads(query)
        if isinstance(listeners, dict):
            listeners = [listeners]
        assert listeners and all(item["LocalAddress"] in ("127.0.0.1", "::1") and item["OwningProcess"] in {row["pid"] for row in owned} for item in listeners), "Unowned CDP listener"
        receipt["launch_attempts"][-1].update({"owned_processes":owned,"cdp_version":version["Browser"],"listeners":listeners,"listener_process_identities":[row for row in owned if row["pid"] in {item["OwningProcess"] for item in listeners}]})
        result = request("POST", "/session", {"capabilities":{"alwaysMatch":{"browserName":"webview2","ms:edgeChromium":True,"ms:edgeOptions":{"debuggerAddress":f"127.0.0.1:{cdp_port}"}}}})
        session = result["sessionId"]
        assert request("GET", f"/session/{session}/window/handles"), "Actual WebDriver window missing"
        request("POST", f"/session/{session}/timeouts", {"script":30000})
        wait("return [...document.querySelectorAll('button')].some(b=>b.textContent.trim().endsWith('资料库'))")
        receipt.setdefault("launches", []).append({"seconds":time.monotonic()-began,"capabilities":result["capabilities"],"user_data_folder":str(folder)})
        version = bridge("system_version")
        assert isinstance(version, dict)
        receipt["system_version"] = version
        owned_host_records.extend(owned_process_rows(native_process_rows(), owned_host.pid))
        receipt.setdefault("windows", []).append(js("return {title:document.title,url:location.href,text:document.body.innerText}"))

    def close_session():
        nonlocal session, owned_host, owned_tree_collection_verified
        assert owned_host is not None, "Owned host identity missing"
        pid = owned_host.pid
        owned_host_records.extend(owned_process_rows(native_process_rows(), pid))
        owned_tree_collection_verified = True
        assert owned_host.poll() is None, "Owned host exited unexpectedly before requested product exit"
        receipt.setdefault("requested_product_exits", []).append({"pid":pid,"requested":True})
        if owned_host.poll() is None:
            # Transport may close as the product exits; normal wait/code remain mandatory.
            with suppress(OSError, RuntimeError):
                native_command("exit_application")
            owned_host.wait(timeout=15)
        exited = owned_host.poll() == 0
        receipt.setdefault("host_shutdowns", []).append({"pid":pid,"exited":exited,"exit_code":owned_host.returncode,"method":"product_exit_application_attached_observer"})
        assert exited, "Owned host did not exit normally with product exit code 0"
        if session:
            # Host has already verifiably exited with code 0.
            with suppress(OSError, RuntimeError):
                request("DELETE", f"/session/{session}")
        session = None
        owned_host = None

    try:
        process = subprocess.Popen(
            [
                str(driver),
                "--port",
                str(port),
                "--native-port",
                str(native),
                "--native-driver",
                str(wrapper),
            ],
            env=env,
            cwd=work,
            stdout=log,
            stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        receipt["owned_driver_pid"] = process.pid
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise RuntimeError("Owned driver exited")
            try:
                request("GET", "/status")
                break
            except OSError:
                time.sleep(0.2)
        else:
            raise TimeoutError("Owned WebDriver readiness")
        launch()
        content = "中文 WebDriver 原文证据 Golden native window 42.\n".encode()
        imported = bridge(
            "source_import",
            {
                "body": {
                    "name": "WebDriver证据.txt",
                    "content_base64": base64.b64encode(content).decode(),
                }
            },
        )
        assert imported["sha256"] == hashlib.sha256(content).hexdigest()
        original = bridge("source_original", {"source_id": imported["source_id"]})
        concurrent = request(
            "POST",
            f"/session/{session}/execute/async",
            {
                "script": "const cb=arguments[arguments.length-1],id=arguments[0];Promise.all(Array.from({length:8},()=>Promise.all(['source_original','anchors_list'].map(operation=>window.__TAURI__.core.invoke('core_command',{request:{operation,payload:{source_id:id}}}))))).then(value=>cb({ok:true,value}),error=>cb({ok:false,error:String(error)}));",
                "args": [imported["source_id"]],
            },
        )
        receipt["concurrent_source_reads"] = concurrent
        assert concurrent["ok"], concurrent
        assert len(concurrent["value"]) == 8
        for source_reply, anchor_reply in concurrent["value"]:
            assert source_reply["status"] == anchor_reply["status"] == 200
            assert source_reply["body"]["sha256"] == imported["sha256"]
            assert base64.b64decode(source_reply["body"]["content_base64"]) == content
            assert anchor_reply["body"]["anchors"] == []
        receipt["read_diagnostics"] = {
            "import": imported,
            "original": original,
            "sources": bridge("sources_list"),
            "anchors": bridge("anchors_list", {"source_id": imported["source_id"]}),
            "crypto_available": js(
                "return {secure:isSecureContext,subtle:!!globalThis.crypto?.subtle}"
            ),
        }
        assert base64.b64decode(original["content_base64"]) == content
        js(
            "[...document.querySelectorAll('button')].find(b=>b.textContent.trim().endsWith('工作台')).click()"
        )
        time.sleep(0.2)
        js(
            "[...document.querySelectorAll('button')].find(b=>b.textContent.trim().endsWith('资料库')).click()"
        )
        wait(
            "return [...document.querySelectorAll('button')].some(b=>b.textContent==='WebDriver证据.txt')"
        )
        js(
            "[...document.querySelectorAll('button')].find(b=>b.textContent==='WebDriver证据.txt').click()"
        )
        wait(
            "return document.querySelector('[aria-label=\"原件正文\"]')?.textContent.includes('中文 WebDriver 原文证据')"
        )
        created = bridge(
            "document_create",
            {
                "body": {
                    "source_id": imported["source_id"],
                    "source_revision": imported["sha256"],
                    "title": "WebDriver中文持久化",
                    "editor_json": {"type": "doc", "content": []},
                }
            },
        )
        editor = {
            "type": "doc",
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {"type": "text", "text": "中文 WebDriver 保存与重启读回 Golden 42"}
                    ],
                }
            ],
        }
        saved = bridge(
            "document_draft",
            {
                "document_id": created["document_id"],
                "body": {"expected_version": created["version"], "editor_json": editor},
            },
        )
        assert saved["text_projection"] == "中文 WebDriver 保存与重启读回 Golden 42", saved
        # Canonical writer assigns stable block IDs; compare its persisted form.
        editor = saved["editor_json"]
        receipt["document"] = saved
        screenshot("saved.png")
        close_session()
        launch()
        reread = bridge("document_get", {"document_id": saved["document_id"]})
        assert reread["editor_json"] == editor and reread["version"] == saved["version"]
        original_again = bridge("source_original", {"source_id": imported["source_id"]})
        assert original_again == original
        backup = bridge("workspace_backup", {"body": {}})
        assert backup["bytes"] > 0 and imported["sha256"] in backup["source_sha_list"]
        backups = bridge("workspace_backups")
        assert any(item["backup_id"] == backup["backup_id"] for item in backups["backups"])
        receipt["backup"] = backup
        changed = bridge(
            "document_draft",
            {
                "document_id": saved["document_id"],
                "body": {
                    "expected_version": saved["version"],
                    "editor_json": {
                        "type": "doc",
                        "content": [
                            {
                                "type": "paragraph",
                                "content": [
                                    {"type": "text", "text": "after backup temporary revision"}
                                ],
                            }
                        ],
                    },
                },
            },
        )
        assert changed["version"] > saved["version"]
        recovery = native_command("recovery_status")
        receipt["recovery_before_restore"] = recovery
        restored = native_command("restore_backup", {"name": backup["filename"]})
        receipt["restore_command_receipt"] = restored
        assert restored["status"] == "restored"
        ready = native_command("retry_backend")
        receipt["retry_command_receipt"] = ready
        assert ready == {"ready": True}, ready
        identity_after_retry = bridge("system_version")
        receipt["system_version_after_retry"] = identity_after_retry
        assert identity_after_retry.get("runtime") == "archeaxis-api", identity_after_retry
        after_restore = bridge("document_get", {"document_id": saved["document_id"]})
        assert (
            after_restore["version"] == saved["version"] and after_restore["editor_json"] == editor
        )
        assert bridge("source_original", {"source_id": imported["source_id"]}) == original
        receipt["native_restore"] = {
            "receipt": restored,
            "changed_version": changed["version"],
            "restored_version": after_restore["version"],
            "cas_equal": True,
            "scope": "Only this fresh product data root; not independent restore",
        }
        screenshot("restart.png")
        receipt["steps"] = [
            "Real Tauri WebDriver session/window",
            "Finite system_version bridge",
            "Import/read original bytes and rendered Chinese reader",
            "Finite bridge document save",
            "Session close/relaunch persisted document",
            "Product consistent backup and list readback",
            "Native backup restore/retry and actual version rollback with original CAS readback",
        ]
        # New product-principles journey: every mutation below uses rendered UI.
        # Finite bridge reads verify canonical persistence; they do not perform writes.
        # The preceding recovery mutation deliberately used the native command;
        # reopen its window to obtain a fresh UI readiness handshake as well.
        close_session()
        launch()
        js("[...document.querySelectorAll('button')].find(b=>b.textContent.trim().endsWith('资料库')).click()")
        wait("return [...document.querySelectorAll('button')].some(b=>b.textContent==='新建原创笔记')")
        before_ids = {item["document_id"] for item in bridge("documents_list")["documents"]}
        ui_click("新建原创笔记")
        wait("return !!document.querySelector('[aria-label=\"版本化草稿编辑器\"] .tiptap')")
        ordinary_text = "原创未核验内容 Golden ordinary note 731"
        ui_type('[aria-label="版本化草稿编辑器"] .tiptap', ordinary_text)
        ui_click("保存草稿")
        deadline = time.monotonic() + 30
        ordinary = None
        while time.monotonic() < deadline:
            new_documents = [item for item in bridge("documents_list")["documents"] if item["document_id"] not in before_ids]
            if len(new_documents) == 1:
                ordinary = bridge("document_get", {"document_id": new_documents[0]["document_id"]})
                if ordinary["text_projection"] == ordinary_text:
                    break
            time.sleep(0.15)
        assert ordinary and ordinary["text_projection"] == ordinary_text
        # Let the editor's existing 900 ms autosave settle before fixing the
        # version used for restart equality and the later check records.
        time.sleep(1.2)
        ordinary = bridge("document_get", {"document_id": ordinary["document_id"]})
        assert ordinary["text_projection"] == ordinary_text
        assert ordinary["source_id"] is None and ordinary["source_revision"] is None
        assert not js("return [...document.querySelectorAll('button')].some(b=>b.textContent==='引用当前页')")
        receipt["ordinary_document_saved"] = ordinary
        receipt["steps"].append("UI original note without source/review/model prerequisites saved by canonical writer")
        close_session()
        launch()
        js("[...document.querySelectorAll('button')].find(b=>b.textContent.trim().endsWith('资料库')).click()")
        wait("return [...document.querySelectorAll('button')].some(b=>b.textContent==='原创笔记 · 文档')")
        ui_click("原创笔记 · 文档")
        wait("return document.querySelector('[aria-label=\"版本化草稿编辑器\"]')?.textContent.includes('保存草稿')")
        assert js("return document.querySelector('[aria-label=\"版本化草稿编辑器\"] .tiptap').textContent") == ordinary_text
        persisted = bridge("document_get", {"document_id": ordinary["document_id"]})
        assert persisted == ordinary
        receipt["steps"].append("UI original note close/relaunch readback equals persisted version")
        js("[...document.querySelectorAll('button')].find(b=>b.textContent.trim().endsWith('知识库')).click()")
        wait("return [...document.querySelectorAll('label')].some(l=>l.textContent.includes('搜索内容'))")
        search_input = ui_element("css selector", "form label input")
        request("POST", f"/session/{session}/element/{search_input}/value", {"text": "ordinary note 731"})
        ui_click("搜索")
        wait("return [...document.querySelectorAll('button')].some(b=>b.textContent.startsWith('原创笔记 · 版本 '))")
        ui_click(f"原创笔记 · 版本 {ordinary['version']}")
        wait("return !!document.querySelector('[aria-label=\"内容核验\"]')")
        assert js("return document.querySelector('[aria-label=\"版本化草稿编辑器\"] .tiptap').textContent") == ordinary_text
        assert not js("return [...document.querySelectorAll('button')].some(b=>b.textContent==='接受当前候选')")
        receipt["steps"].append("UI search finds ordinary unverified document and opens existing editor without knowledge acceptance")
        for label, cloud_button, manual_summary in (
            ("识别忠实度", "申请或重试识别云端核验", "手动记录识别核验"),
            ("专业依据", "申请或重试专业云端核验", "手动记录专业核验"),
        ):
            scope = f"//section[@aria-label='{label}']"
            summary = ui_element("xpath", f"{scope}//summary[normalize-space(.)='{manual_summary}']")
            request("POST", f"/session/{session}/element/{summary}/click", {})
            ui_click("明确提交手动核验记录", scope)
            wait(f"return document.querySelector('[aria-label=\"{label}\"]').textContent.includes('不确定 · 手动记录')")
            ui_click(cloud_button, scope)
            wait(f"return document.querySelector('[aria-label=\"{label}\"]').textContent.includes('等待核验 · 云端尚未执行')")
        checks = bridge("document_checks", {"document_id": ordinary["document_id"], "version": ordinary["version"]})
        for dimension in ("recognition_fidelity", "professional_basis"):
            entries = [item for item in checks["checks"] if item["dimension"] == dimension]
            assert any(item["provider_mode"] == "manual" and item["status"] == "uncertain" for item in entries)
            cloud = [item for item in entries if item["provider_mode"] == "cloud"]
            assert cloud and all(item["status"] == "pending" and not item["execution_verified"] and item["execution_state"] == "not_executed" for item in cloud)
        receipt["ordinary_document_checks"] = checks
        receipt["steps"].append("UI separately records both manual uncertain checks and cloud pending requests; cloud remains not executed")
        ui_type('[aria-label="内容核验"] > label textarea', "工程样板修订理由，不构成知识认可")
        revision_button = ui_element("xpath", "(//button[normalize-space(.)='用于下一次修订'])[1]")
        request("POST", f"/session/{session}/element/{revision_button}/click", {})
        ui_click("保存草稿")
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            revised = bridge("document_get", {"document_id": ordinary["document_id"]})
            if revised["version"] > ordinary["version"] and revised.get("revision_basis"):
                break
            time.sleep(0.15)
        assert revised["text_projection"] == ordinary_text
        assert revised["revision_basis"]["rationale"] == "工程样板修订理由，不构成知识认可"
        assert revised["revision_basis"]["reference_version"] == ordinary["version"]
        receipt["ordinary_document_revision"] = revised
        receipt["steps"].append("UI explicitly selected revision basis persists with next ordinary document save")
        screenshot("ordinary-checks.png")
        close_session()
        receipt["ok"] = True
    except BaseException as error:
        receipt["ok"] = False
        receipt["error"] = f"{type(error).__name__}: {error}"
        receipt["traceback"] = traceback.format_exc()
        if process and process.poll() is None:
            # Metadata only; no command lines, credentials or shared processes.
            try:
                receipt["owned_failure_processes"] = owned_process_rows(native_process_rows(), process.pid)
            except (OSError, RuntimeError) as diagnostic_error:
                receipt["owned_failure_processes"] = "diagnostic collection failed"
                receipt["diagnostic_error"] = type(diagnostic_error).__name__
        if session:
            try:
                screenshot("failure.png")
            except BaseException as capture_error:
                receipt["screenshot_error"] = str(capture_error)
    finally:
        if owned_host is not None:
            try:
                close_session()
            except BaseException as error:
                receipt["ok"] = False
                receipt["owned_host_cleanup_error"] = type(error).__name__
                try:
                    cleanup = load("attach_cleanup", REPO / "scripts/runtime/dev.py")
                    cleanup.stop_owned_process(owned_host)
                    owned_host.wait(timeout=15)
                except BaseException as cleanup_error:
                    receipt["owned_host_forced_cleanup_error"] = type(cleanup_error).__name__
                    receipt["owned_host_forced_cleanup_traceback"] = traceback.format_exc()
        if session:
            try:
                request("DELETE", f"/session/{session}")
            except BaseException:
                receipt["ok"] = False
        if process and process.poll() is None:
            launcher = load("webdriver_dev", REPO / "scripts/runtime/dev.py")
            try:
                launcher.stop_owned_process(process)
                process.wait(timeout=15)
                receipt["owned_process_cleanup"] = True
            except (OSError, subprocess.TimeoutExpired) as cleanup_error:
                receipt["owned_process_cleanup"] = False
                receipt["cleanup_error"] = type(cleanup_error).__name__
                receipt["ok"] = False
        try:
            receipt["owned_identity_collection_verified"] = owned_tree_collection_verified
            if receipt.get("owned_host_pids") and not owned_tree_collection_verified:
                raise RuntimeError("Owned attach process tree was never identity-verified")
            rows = {row["pid"]: row for row in native_process_rows()}
            remaining = [row["pid"] for row in owned_host_records
                         if row["pid"] in rows and rows[row["pid"]]["created"] == row["created"]]
            receipt["remaining_same_creation_owned_hosts"] = sorted(set(remaining))
            if remaining:
                raise RuntimeError("Owned host descendants remained after cleanup")
            query = subprocess.run(["powershell.exe", "-NoProfile", "-Command",
                "@(Get-NetTCPConnection -State Listen -ErrorAction Stop | Where-Object { $_.LocalPort -in @("
                + ",".join(str(value) for value in attach_ports + [port, native])
                + ") } | Select-Object LocalAddress,LocalPort,OwningProcess) | ConvertTo-Json -Compress"],
                capture_output=True, text=True, check=True, timeout=15)
            listeners = json.loads(query.stdout or "[]")
            receipt["remaining_owned_port_listeners"] = listeners
            if listeners:
                raise RuntimeError("Owned attach/driver ports remained listening after cleanup")
            receipt["owned_ports_released"] = True
        except (OSError, RuntimeError, subprocess.SubprocessError, ValueError) as error:
            receipt["owned_cleanup_readback_error"] = type(error).__name__
            receipt["ok"] = False
        log.close()
        receipt["driver_log"] = identity(work / "driver.log")
        if native_log.is_file():
            receipt["native_driver_log"] = identity(native_log)
        path = work / "receipt.json"
        path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8")
        print(
            json.dumps(
                {"ok": receipt["ok"], "receipt": str(path), "error": receipt.get("error")},
                ensure_ascii=False,
            )
        )
    return 0 if receipt["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
