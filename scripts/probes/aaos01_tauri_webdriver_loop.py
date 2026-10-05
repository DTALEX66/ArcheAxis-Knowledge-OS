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
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from aaos01_office_runtime_loop import REPO, identity, load


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
        "--installer",
        type=Path,
        help="Exact parent-verified NSIS installer identity; does not itself establish installation",
    )
    args = parser.parse_args()
    host = args.host.resolve()
    tools = REPO / ".project-local/task-runtime/aaos01-tools"
    driver = (args.driver or tools / "tauri-driver-2.1.0/bin/tauri-driver.exe").resolve()
    edge = (args.native_driver or tools / "edge-154.0.4258.48/msedgedriver.exe").resolve()
    work = REPO / ".project-local/task-runtime/aaos01-webdriver" / uuid.uuid4().hex
    work.mkdir(parents=True)
    port, native = free_port(), free_port()
    env = dict(os.environ)
    for key in ("ARCHEAXIS_DEV_EXTERNAL_BACKEND", "WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS"):
        env.pop(key, None)
    env["ARCHEAXIS_PORTABLE_ROOT"] = str(work / "data")
    env["WEBVIEW2_USER_DATA_FOLDER"] = str(work / "webview")
    receipt = {
        "ok": False,
        "evidence_level": "REAL_TAURI_WEBDRIVER_CANDIDATE",
        "host": identity(host),
        "driver": identity(driver),
        "edge": identity(edge),
        "data_root": str(work / "data"),
        "steps": [],
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
            with urlopen(req, timeout=45) as response:
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
        nonlocal session
        began = time.monotonic()
        result = request(
            "POST",
            "/session",
            {
                "capabilities": {
                    "alwaysMatch": {"tauri:options": {"application": str(host), "args": []}}
                }
            },
        )
        session = result["sessionId"]
        request("POST", f"/session/{session}/timeouts", {"script": 30000})
        wait(
            "return [...document.querySelectorAll('button')].some(b=>b.textContent.trim().endsWith('资料库'))"
        )
        receipt.setdefault("launches", []).append(
            {"seconds": time.monotonic() - began, "capabilities": result["capabilities"]}
        )
        version = bridge("system_version")
        assert isinstance(version, dict)
        receipt["system_version"] = version
        receipt.setdefault("windows", []).append(
            js("return {title:document.title,url:location.href,text:document.body.innerText}")
        )

    def close_session():
        nonlocal session
        # Enumerate only descendants of the driver Popen we created. Record live
        # host handles before DELETE so PID reuse cannot masquerade as shutdown.
        pending, hosts = [process.pid], []
        while pending:
            parent = pending.pop()
            query = subprocess.run(
                [
                    "powershell.exe",
                    "-NoProfile",
                    "-Command",
                    f"@(Get-CimInstance Win32_Process -Filter 'ParentProcessId={parent}' | Select-Object ProcessId,Name) | ConvertTo-Json -Compress",
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            children = json.loads(query.stdout or "[]")
            if isinstance(children, dict):
                children = [children]
            for child in children:
                pending.append(child["ProcessId"])
                if child["Name"].casefold() == host.name.casefold():
                    hosts.append(child["ProcessId"])
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.OpenProcess.restype = ctypes.c_void_p
        handles = [(pid, kernel.OpenProcess(0x100000, False, pid)) for pid in hosts]
        assert handles and all(handle for _, handle in handles), (
            "Owned host process identity missing"
        )
        try:
            request("DELETE", f"/session/{session}")
            session = None
            for pid, handle in handles:
                exited = kernel.WaitForSingleObject(ctypes.c_void_p(handle), 15000) == 0
                receipt.setdefault("host_shutdowns", []).append({"pid": pid, "exited": exited})
                assert exited, (
                    "Window removed but owned Tauri host remained alive after DELETE/session"
                )
        finally:
            for _, handle in handles:
                kernel.CloseHandle(ctypes.c_void_p(handle))

    try:
        process = subprocess.Popen(
            [
                str(driver),
                "--port",
                str(port),
                "--native-port",
                str(native),
                "--native-driver",
                str(edge),
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
        close_session()
        receipt["ok"] = True
    except BaseException as error:
        receipt["ok"] = False
        receipt["error"] = f"{type(error).__name__}: {error}"
        receipt["traceback"] = traceback.format_exc()
        if session:
            try:
                screenshot("failure.png")
            except BaseException as capture_error:
                receipt["screenshot_error"] = str(capture_error)
    finally:
        if session:
            try:
                request("DELETE", f"/session/{session}")
            except BaseException as error:
                receipt["cleanup_error"] = str(error)
                receipt["ok"] = False
        if process and process.poll() is None:
            launcher = load("webdriver_dev", REPO / "scripts/runtime/dev.py")
            launcher.stop_owned_process(process)
            receipt["owned_process_cleanup"] = True
            process.wait(timeout=15)
        log.close()
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
