"""Real candidate Tauri WebDriver engineering probe; no installed/human signoff."""

from __future__ import annotations

import argparse
import base64
import ctypes
import hashlib
import json
import os
import re
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


def compatible_edge_versions(driver_version: str, runtime_version: str) -> bool:
    """Microsoft requires matching major/minor/build; patch updates are compatible.

    https://learn.microsoft.com/en-us/microsoft-edge/webdriver-chromium/
    """
    driver = re.fullmatch(r"Microsoft Edge WebDriver (\d+\.\d+\.\d+\.\d+)(?: \([^\r\n]+\))?", driver_version)
    runtime = re.fullmatch(r"Edg/(\d+\.\d+\.\d+\.\d+)", runtime_version)
    return bool(driver and runtime and driver[1].split(".")[:3] == runtime[1].split(".")[:3])


def navigate_compatibility_space(js, wait, space: str) -> None:
    """Exercise the declared public legacy route; never infer new-page coverage."""
    headings = {"library": "资料库", "vault": "知识库", "workspace": "工作台"}
    heading = headings[space]
    js("window.location.hash=arguments[0]", ["space=" + space])
    wait("return location.hash===" + json.dumps("#space=" + space) + " && [...document.querySelectorAll('h1,h2,h3')].some(h=>h.textContent.trim()===" + json.dumps(heading) + ")")


def navigation_button_selector(text: str, scope: str = "") -> str:
    # Object-navigation buttons contain a label and description. Match the exact
    # label child and click its actual parent button, rather than widening all labels.
    if scope == "//ul[@aria-label='资料库对象导航']":
        return f"{scope}//button[b[normalize-space(.)='{text}']]"
    return f"{scope}//button[normalize-space(.)='{text}']"


def probe_environment():
    launcher = load("native_probe_paths", REPO / "scripts/runtime/dev.py")
    paths = launcher.layout(REPO, "webdriver-" + uuid.uuid4().hex[:12])
    env = dict(os.environ)
    env.update(launcher.prepare(paths))
    return paths, env


def installation_limitation(installer) -> str:
    """The limitation this run can honestly state about installation.

    This probe never establishes installation -- a parent verifier does that. Calling the
    executable a candidate is false once `--installer` records that a parent supplied the
    installed host, and stating it there produced a receipt whose `limitations[0]` directly
    contradicted its own `installation_context` and `host.path`.
    """
    if installer is not None:
        return (
            "This probe does not itself establish installation; the parent installer verifier "
            "supplied the installed host and this receipt hashes that installer"
        )
    return "Candidate executable, not NSIS installed journey"



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


def archive_member_job_id(parent_job, member_file):
    legacy = parent_job + "-member-" + member_file
    if len(legacy.encode("utf-8")) <= 200 and all(character.isascii() and (character.isalnum() or character in "-_.") for character in legacy):
        return legacy
    identity = "archeaxis.archive-member/v1\0" + parent_job + "\0" + member_file
    return "member-" + hashlib.sha256(identity.encode("utf-8")).hexdigest()


def installed_format_import_loop(bridge, repo, proofs):
    """Public fixtures through the installed host's finite authenticated bridge.

    A candidate caller remains candidate evidence; installation context is supplied
    by the existing installer verifier, never inferred from this helper.
    """
    import io
    import tarfile

    csv = b"key,value\ninstalled-format-value,37\n"
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w") as archive:
        member = tarfile.TarInfo("notes/known.csv")
        member.size = len(csv)
        archive.addfile(member, io.BytesIO(csv))
    light = load("installed_epub_public_fixture", repo / "scripts/probes/aaos01_light_format_loop.py")
    samples = [
        ("g3-known.epub", "text", light.samples()["epub"], "Chapter body 42"),
        ("g3-known.xlsx", "office", (repo / "tests/fixtures/golden/golden-xlsx-anchor.xlsx").read_bytes(), "Sheet evidence anchor"),
        ("g3-known.pptx", "office", (repo / "tests/fixtures/golden/golden-pptx-anchor.pptx").read_bytes(), "Slide evidence anchor"),
        ("g3-known.csv", "text", csv, "installed-format-value"),
        ("g3-known.tar", "archive", buffer.getvalue(), "notes/known.csv"),
    ]

    def execute(job):
        bridge("job_execute", {"job_id": job, "body": {"deadline_ms": 120000}})
        deadline = time.monotonic() + 130
        while time.monotonic() < deadline:
            state = bridge("jobs_get", {"job_id": job})
            if state["state"] in ("succeeded", "failed", "rejected", "cancelled"):
                assert state["state"] == "succeeded", f"Installed format job failed: {job}"
                return
            time.sleep(0.15)
        raise TimeoutError(f"Installed format job deadline: {job}")

    def snapshot(source_id, job):
        original = bridge("source_original", {"source_id": source_id})
        data = base64.b64decode(original["content_base64"], validate=True)
        assert hashlib.sha256(data).hexdigest() == original["sha256"]
        outputs = {kind: bridge("job_output", {"job_id": job, "kind": kind})
                   for kind in ("text", "document_structure", "loss_report")}
        for output in outputs.values():
            assert hashlib.sha256(output["content"].encode()).hexdigest() == output["metadata"]["sha256"]
            assert len(output["content"].encode()) == output["metadata"]["byte_length"]
        anchors = json.loads(outputs["document_structure"]["content"])
        loss = json.loads(outputs["loss_report"]["content"])
        assert anchors and all(item["char_end"] > item["char_start"] for item in anchors)
        assert loss["loss_note"].strip()
        quality = bridge("job_quality", {"job_id": job})
        assert quality["state"] == "succeeded" and quality["engine"] == loss["engine"]
        assert quality["engine_version"] == loss["engine_version"]
        return {"source_id": source_id, "job_id": job, "original": original,
                "outputs": outputs, "quality": quality}

    for name, kind, content, expected in samples:
        imported = bridge("source_import", {"body": {"name": name, "content_base64": base64.b64encode(content).decode()}})
        assert imported["sha256"] == hashlib.sha256(content).hexdigest()
        job = "g3-format-" + uuid.uuid4().hex
        bridge("job_enqueue", {"body": {"job_id": job, "kind": kind, "input_ref": imported["source_id"]}})
        execute(job)
        proof = snapshot(imported["source_id"], job)
        assert expected in proof["outputs"]["text"]["content"]
        loss = json.loads(proof["outputs"]["loss_report"]["content"])
        if name.endswith("xlsx") or name.endswith("pptx"):
            locators = loss["params"]["worker_structure"]
            assert locators
            if name.endswith("xlsx"):
                assert loss["params"]["engine"] == "openpyxl"
                assert locators[0]["kind"] == "sheet_row"
                assert locators[0]["path"][0].startswith("sheet-")
                assert any(row["path"][0] == "sheet-Evidence" and "A1=Sheet evidence anchor" in proof["outputs"]["text"]["content"][row["char_start"]:row["char_end"]] for row in locators)
            else:
                assert loss["params"]["engine"] == "python-pptx"
                assert locators[0]["kind"] == "slide" and locators[0]["path"][0] == "slide-1"
                assert any(row["path"][0] == "slide-1" and "Slide evidence anchor" in proof["outputs"]["text"]["content"][row["char_start"]:row["char_end"]] for row in locators)
        if name.endswith("csv"):
            facts = loss["params"]["format"]
            assert facts["format"] == "csv" and facts["parsed"] is True
            assert any(row["row"] == 2 and row["column"] == 2 and row["value"] == "37" for row in facts["locations"])
        if name.endswith("epub"):
            facts = loss["params"]["format"]
            assert facts["format"] == "epub" and facts["parsed"] is True
            assert facts["toc"][0] == {"href": "chapter.xhtml", "title": "Golden"}
            rows = [row for row in facts["locations"] if row["value"] == "Chapter body 42"]
            assert len(rows) == 1
            row = rows[0]
            assert row["kind"] == "epub_chapter_paragraph" and row["path"] == "OEBPS/chapter.xhtml"
            assert row["chapter"] == 1 and row["paragraph"] == 2
            state = bridge("jobs_get", {"job_id": job})
            assert state["input_ref"] == imported["source_id"] and state["attempt"] >= 1
            proof["epub_position"] = {"type": "epub", "job_id": job,
                "attempt": state["attempt"], "result_sha256": proof["outputs"]["loss_report"]["metadata"]["sha256"],
                "path": row["path"], "chapter": row["chapter"], "paragraph": row["paragraph"]}
            proof["epub_value"] = row["value"]
            proof["scope"] = "CHAPTER_PARAGRAPH_NOT_VISUAL_PAGINATION"
        proofs.append(proof)
        if kind == "archive":
            declared = loss["params"]["structure"]["extractable_members"]
            assert len(declared) == 1 and declared[0]["name"] == "notes/known.csv", \
                {"route_media_type": loss["params"].get("media_type"), "declared": declared,
                 "member_dir_requested": loss["params"].get("attachment_extraction")}
            assert declared[0]["sha256"] == hashlib.sha256(csv).hexdigest()
            # Reuse finite source list/jobs: no token access or arbitrary HTTP/file API.
            matches = [item for item in bridge("sources_list")["sources"] if item["sha256"] == declared[0]["sha256"]]
            assert len(matches) == 1
            member_source = matches[0]["source_id"]
            member_job = archive_member_job_id(job, declared[0]["file"])
            candidates = bridge("source_jobs", {"source_id": member_source})["jobs"]
            assert any(item["job_id"] == member_job and item["kind"] == "text" for item in candidates), "Core automatic member job missing"
            execute(member_job)
            child = snapshot(member_source, member_job)
            assert "installed-format-value" in child["outputs"]["text"]["content"]
            members = bridge("source_members", {"source_id": imported["source_id"]})
            assert members["container_source_id"] == imported["source_id"]
            assert members["member_count"] == len(members["members"])
            assert members["readable_count"] + members["custody_only_count"] == members["member_count"]
            matches = [item for item in members["members"] if item["member"] == declared[0]["name"]]
            assert len(matches) == 1
            member = matches[0]
            assert member["source_id"] == member_source and member["sha256"] == declared[0]["sha256"]
            assert member["origin_ref"] == imported["source_id"] + "#" + declared[0]["name"]
            assert member["readable"] is True
            # job_id is the earliest source job, not necessarily this archive's child;
            # exact automatic child identity was already asserted through source_jobs.
            child["container_source_id"] = imported["source_id"]
            child["source_members"] = members
            child["parent_archive_job"] = job
            proofs.append(child)
    return proofs


def installed_format_readback(bridge, proofs):
    for proof in proofs:
        if "source_members" in proof:
            assert bridge("source_members", {"source_id": proof["container_source_id"]}) == proof["source_members"]
        assert bridge("source_original", {"source_id": proof["source_id"]}) == proof["original"]
        assert bridge("jobs_get", {"job_id": proof["job_id"]})["state"] == "succeeded"
        assert bridge("job_quality", {"job_id": proof["job_id"]}) == proof["quality"]
        for kind, value in proof["outputs"].items():
            assert bridge("job_output", {"job_id": proof["job_id"], "kind": kind}) == value


def installed_epub_reader(bridge, js, wait, ui_click, proof, *, cite):
    """Actual product Reader and persisted locator; no DOM injection or mocked bridge."""
    navigate_compatibility_space(js, wait, "workspace")
    navigate_compatibility_space(js, wait, "library")
    wait("return [...document.querySelectorAll('[aria-label=\"保留原件\"] button')].some(b=>b.textContent==='g3-known.epub')")
    ui_click("g3-known.epub", "//nav[@aria-label='保留原件']")
    wait("return [...document.querySelectorAll('h2,h3,h4')].some(h=>h.textContent==='EPUB 章节段落') && document.body.textContent.includes('Chapter body 42')")
    position = proof["epub_position"]
    assert js("return document.body.textContent.includes(arguments[0])", [position["path"]])
    scope = "//p[normalize-space(.)='Chapter body 42']/parent::div"
    if cite:
        ui_click("引用 EPUB 段落", scope)
        wait("return document.body.textContent.includes('段落与解析回执关联已校验')")
        anchors = bridge("anchors_list", {"source_id": proof["source_id"]})["anchors"]
        candidates = [anchor for anchor in anchors if all(json.loads(anchor["position"]).get(key) == value for key, value in position.items())]
        assert len(candidates) == 1
        anchor = candidates[0]
        assert anchor["source_id"] == proof["source_id"] and anchor["source_revision"] == proof["original"]["sha256"]
        assert anchor["location_status"] == "located"
        assert json.loads(anchor["position"])["checksum"] == hashlib.sha256(proof["epub_value"].encode()).hexdigest()
        proof["epub_anchor"] = anchor
        ui_click("定位 EPUB 段落", scope)
    else:
        anchors = bridge("anchors_list", {"source_id": proof["source_id"]})["anchors"]
        assert proof["epub_anchor"] in anchors
        ui_click("来源引用", "//aside[@aria-label='来源版本证据']")
    wait("return document.querySelector('[data-epub-focused=\"true\"]')?.textContent==='Chapter body 42'")
    assert js("return document.querySelector('[data-epub-focused=\"true\"]')?.textContent") == proof["epub_value"]


def installed_remaining_matrix(bridge, bridge_status, repo, records):
    """Existing canonical fixtures only; missing actual engines fail rather than skip."""
    import io
    import zipfile

    light = load("installed_matrix_canonical_samples", repo / "scripts/probes/aaos01_light_format_loop.py")
    public = light.samples()
    cases = [(extension, "A", name, kind, (repo / "tests/fixtures/golden" / name).read_bytes(), expected, False)
             for extension, (name, kind, expected) in light.A_SAMPLES.items()
             if extension not in {"xlsx", "pptx"}]
    cases += [(extension, "B", "g3-matrix." + extension, "text", content, "Golden", False)
              for extension, content in public.items()
              if extension not in {"csv", "epub"} and not extension.startswith("corrupt_")]
    cases += [(extension.removeprefix("corrupt_"), "B", "g3-negative." + extension.removeprefix("corrupt_"), "text", content, None, True)
              for extension, content in public.items() if extension.startswith("corrupt_")]
    matrix_deadline = time.monotonic() + 900

    raw_bridge, raw_status = bridge, bridge_status

    def bounded_call(call, operation, payload):
        if time.monotonic() >= matrix_deadline:
            raise TimeoutError("Installed G3 aggregate deadline before finite read/write")
        result = call(operation, payload)
        if time.monotonic() >= matrix_deadline:
            raise TimeoutError("Installed G3 aggregate deadline after finite read/write")
        return result

    def bridge(operation, payload):
        return bounded_call(raw_bridge, operation, payload)

    def bridge_status(operation, payload):
        return bounded_call(raw_status, operation, payload)

    def execute(job, failed=False):
        if time.monotonic() >= matrix_deadline:
            raise TimeoutError("Installed G3 aggregate 900-second deadline")
        bridge("job_execute", {"job_id": job, "body": {"deadline_ms": 30000}})
        deadline = min(matrix_deadline, time.monotonic() + 35)
        while time.monotonic() < deadline:
            state = bridge("jobs_get", {"job_id": job})
            if state["state"] in {"succeeded", "failed", "rejected", "cancelled"}:
                assert state["state"] == ("failed" if failed else "succeeded"), state
                return state
            time.sleep(0.15)
        raise TimeoutError("Installed matrix job deadline: " + job)

    def snapshot(source_id, job, state, failed=False):
        original = bridge("source_original", {"source_id": source_id})
        raw = base64.b64decode(original["content_base64"], validate=True)
        assert original["source_id"] == source_id and hashlib.sha256(raw).hexdigest() == original["sha256"]
        assert state["job_id"] == job and state["input_ref"] == source_id
        quality = bridge("job_quality", {"job_id": job})
        assert quality["state"] == state["state"]
        proof = {"source_id": source_id, "job_id": job, "original": original, "state": state, "quality": quality, "failed": failed}
        if failed:
            assert "AAK-WORKER-003" in str(state.get("error")), state
            statuses = {kind: bridge_status("job_output", {"job_id": job, "kind": kind})
                        for kind in ("text", "document_structure", "loss_report")}
            assert all(reply["status"] == 404 for reply in statuses.values()), statuses
            proof["missing_outputs"] = statuses
            proof["scope"] = "EXPECTED_MALFORMED_INPUT_FAILURE_NO_SUCCESS_OUTPUT"
        else:
            outputs = {kind: bridge("job_output", {"job_id": job, "kind": kind})
                       for kind in ("text", "document_structure", "loss_report")}
            for kind, output in outputs.items():
                raw = output["content"].encode("utf-8")
                assert output["metadata"]["kind"] == kind
                assert output["metadata"]["byte_length"] == len(raw)
                assert output["metadata"]["sha256"] == hashlib.sha256(raw).hexdigest()
            loss = json.loads(outputs["loss_report"]["content"])
            assert quality["engine"] == loss["engine"] and quality["engine_version"] == loss["engine_version"]
            assert loss["engine"] and loss["engine_version"] and loss["loss_note"]
            proof["outputs"] = outputs
        return proof

    for extension, wave, name, kind, content, expected, corrupt in cases:
        record = {"format": extension, "wave": wave, "name": name, "corrupt": corrupt,
                  "input": {"sha256": hashlib.sha256(content).hexdigest(), "bytes": len(content)}, "stage": "importing"}
        records.append(record)  # preserve the exact failing row in the parent receipt
        payload = {"body": {"name": name, "content_base64": base64.b64encode(content).decode()}}
        assert len(json.dumps(payload["body"]).encode()) <= 8 * 1024 * 1024
        imported = bridge("source_import", payload)
        assert imported["sha256"] == record["input"]["sha256"]
        job = "g3-matrix-" + uuid.uuid4().hex
        record.update(source_id=imported["source_id"], job_id=job, stage="executing")
        bridge("job_enqueue", {"body": {"job_id": job, "kind": kind, "input_ref": imported["source_id"]}})
        state = execute(job, corrupt)
        proof = snapshot(imported["source_id"], job, state, corrupt)
        record["proof"] = proof
        if not corrupt:
            outputs = proof["outputs"]
            canonical = {"format": extension, "wave": wave, "expected_text": expected,
                         "input": record["input"], "snapshot": {"job": {"body": state},
                         **{key: {"status": 200, "body": value} for key, value in outputs.items()},
                         "quality": {"status": 200, "body": proof["quality"]}}}
            light.check(canonical)  # reuse all canonical format-specific locator/structure assertions
            record["scope"] = "HEADER_PROBE_ONLY_NO_DECODE_ASR_TIME_RANGE" if kind == "media" else "REAL_FINITE_HOST_JOB_OUTPUT_LOCATOR_LOSS_NOT_VISUAL_READER"
            record["native_locations"] = canonical.get("native_locations")
            if extension == "zip":
                with zipfile.ZipFile(io.BytesIO(content)) as archive:
                    members_bytes = {member: archive.read(member) for member in archive.namelist() if not member.endswith("/")}
                members = bridge("source_members", {"source_id": imported["source_id"]})
                assert members["member_count"] == len(members_bytes)
                declared = json.loads(outputs["loss_report"]["content"])["params"]["structure"]["extractable_members"]
                children = []
                record["children"] = children
                for member in members["members"]:
                    raw = members_bytes[member["member"]]
                    assert member["sha256"] == hashlib.sha256(raw).hexdigest()
                    assert member["origin_ref"] == imported["source_id"] + "#" + member["member"]
                    descriptor = next(item for item in declared if item["name"] == member["member"])
                    child_job = archive_member_job_id(job, descriptor["file"])
                    queued = bridge("source_jobs", {"source_id": member["source_id"]})["jobs"]
                    assert any(item["job_id"] == child_job and item["state"] == "queued" for item in queued)
                    child = snapshot(member["source_id"], child_job, execute(child_job))
                    assert base64.b64decode(child["original"]["content_base64"], validate=True) == raw
                    assert child["outputs"]["text"]["content"].strip()
                    children.append(child)
                record["source_members"] = bridge("source_members", {"source_id": imported["source_id"]})
                assert all(member["readable"] for member in record["source_members"]["members"])
        record["stage"] = "verified_before_full_restart"
    assert len(records) == 21 and sum(record["corrupt"] for record in records) == 4


def installed_remaining_readback(bridge, bridge_status, records):
    readback_deadline = time.monotonic() + 180
    raw_bridge, raw_status = bridge, bridge_status

    def bounded_read(call, operation, payload):
        if time.monotonic() >= readback_deadline:
            raise TimeoutError("Installed matrix 180-second restart readback deadline")
        result = call(operation, payload)
        if time.monotonic() >= readback_deadline:
            raise TimeoutError("Installed matrix restart readback transport exceeded deadline")
        return result

    def bridge(operation, payload):
        return bounded_read(raw_bridge, operation, payload)

    def bridge_status(operation, payload):
        return bounded_read(raw_status, operation, payload)

    for record in records:
        proofs = [record["proof"], *record.get("children", [])]
        for proof in proofs:
            assert bridge("source_original", {"source_id": proof["source_id"]}) == proof["original"]
            assert bridge("jobs_get", {"job_id": proof["job_id"]}) == proof["state"]
            assert bridge("job_quality", {"job_id": proof["job_id"]}) == proof["quality"]
            for kind, output in proof.get("outputs", {}).items():
                assert bridge("job_output", {"job_id": proof["job_id"], "kind": kind}) == output
            for kind, missing in proof.get("missing_outputs", {}).items():
                assert bridge_status("job_output", {"job_id": proof["job_id"], "kind": kind}) == missing
        if "source_members" in record:
            assert bridge("source_members", {"source_id": record["source_id"]}) == record["source_members"]
        record["stage"] = "verified_after_full_host_restart"


def synthetic_course_loop(bridge, bridge_status, js, wait, ui_click, ui_type, screenshot):
    """Real native transport/rendering using authored data; never human signoff."""
    text = "SYNTHETIC course lesson evidence 20261009."
    source = bridge("source_import", {"body": {"name": "synthetic-course.txt", "content_base64": base64.b64encode(text.encode()).decode()}})
    job_id = "synthetic_course_" + uuid.uuid4().hex
    bridge("job_enqueue", {"body": {"job_id": job_id, "kind": "text", "input_ref": source["source_id"]}})
    bridge("job_execute", {"job_id": job_id, "body": {"deadline_ms": 30000}})
    execution = bridge("jobs_get", {"job_id": job_id})
    deadline = time.monotonic() + 40
    while execution["state"] in {"queued", "running"} and time.monotonic() < deadline:
        time.sleep(0.15)
        execution = bridge("jobs_get", {"job_id": job_id})
    assert execution["state"] == "succeeded", execution
    transform = bridge("source_job_transform", {"source_id": source["source_id"], "job_id": job_id})
    content = transform["content"]
    knowledge = bridge("knowledge_from_transform", {"body": {"knowledge_type": "FACTUAL_CLAIM", "body": content,
        "source_id": source["source_id"], "job_id": job_id, "transform_id": transform["transform_id"],
        "selection_start_utf16": 0, "selection_end_utf16": len(content.encode("utf-16-le")) // 2, "quote": content}})
    kid = knowledge["knowledge_id"]
    unaccepted = bridge_status("course_from_knowledge", {"body": {"knowledge_id": kid}})
    missing = bridge_status("course_get", {"course_id": "course-not-present"})
    assert unaccepted["status"] == 409 and missing["status"] == 404
    detail = bridge("knowledge_get", {"id": kid})
    bridge("knowledge_review", {"id": kid, "body": {"action": "accepted", "reviewer": "SYNTHETIC_TEST_ACTOR_NOT_HUMAN_SIGNOFF",
        "note": "Isolated authored fixture; no human acceptance evidence", "expected_version": detail["version"]}})
    ui_click("知识库")
    wait("return !!document.querySelector('form label input')")
    ui_type("form label input", "SYNTHETIC course lesson evidence")
    ui_click("搜索")
    result = bridge("search", {"q": "SYNTHETIC course lesson evidence"})
    head = next(item["head"] for item in result["items"] if item["knowledge_id"] == kid)
    wait("return [...document.querySelectorAll('button')].some(b=>b.textContent===" + json.dumps(head) + ")")
    ui_click(head)
    wait("return !!document.querySelector('[aria-label=\"课程与课时\"]')")
    ui_click("从当前知识生成课程与课时")
    wait("return document.querySelector('[aria-label=\"课程候选课时\"]')?.textContent.includes('SYNTHETIC course lesson evidence')")
    geometry = js("const article=document.querySelector('[aria-label=\"课程候选课时\"]'),pre=article.querySelector('pre');return {article_client:article.clientWidth,article_scroll:article.scrollWidth,pre_client:pre.clientWidth,pre_scroll:pre.scrollWidth,white_space:getComputedStyle(pre).whiteSpace};")
    assert geometry["article_scroll"] <= geometry["article_client"] + 2 and geometry["pre_scroll"] <= geometry["pre_client"] + 2, geometry
    js("document.querySelector('[aria-label=\"课程候选课时\"]').scrollIntoView({block:'center'});")
    screenshot("synthetic-course-lesson.png")
    # Idempotent Core re-read supplies canonical identities without reading private UI state.
    created = bridge("course_from_knowledge", {"body": {"knowledge_id": kid}})
    course_id = created["course"]["manifest"]["manifest_id"]
    suggested = created["suggested_learning_item"]
    key = suggested["item_key"]
    assert len(key) == 159 and created["course"]["status"] == "candidate" and created["human_review_required"] is True
    ui_click("由课程课时建立学习问题")
    wait("return [...document.querySelectorAll('button')].some(b=>b.textContent===" + json.dumps(key) + ")")
    ui_click(key)
    wait("return [...document.querySelectorAll('label')].some(l=>l.textContent.includes('本次答案'))")
    assessment = bridge("assessment_get", {"item_key": key})
    state = bridge("learning_state", {"item_key": key})
    assert assessment["item_key"] == key and assessment["knowledge_id"] == kid and assessment["knowledge_version"] == kid
    assert state["item_key"] == key and state["learner"]["assessment"]["assessment_id"] == assessment["assessment_id"]
    history = bridge("learning_history", {"item_key": key})
    return {"status": "PASS", "fixture_data": "SYNTHETIC_AUTHORED", "review_actor": "SYNTHETIC_TEST_ACTOR_NOT_HUMAN_SIGNOFF",
        "human_signoff": False, "runtime_evidence": "REAL_NATIVE_HOST_CORE_WORKER", "knowledge_id": kid, "course_id": course_id,
        "item_key": key, "assessment": assessment, "learning_history": history, "lesson_geometry": geometry,
        "negative_unaccepted_status": unaccepted["status"], "negative_missing_status": missing["status"]}


def synthetic_template_pagination(bridge, js, wait, ui_click, screenshot):
    """501 authored objects through the real finite bridge and canonical writer."""
    baseline = bridge("documents_list")["snapshot_count"]
    metadata = {"schema":"archeaxis.template/v1","template_id":"T1","discipline_id":"math",
        "fields":{"status":"unevaluated"},"references":[],"learning_item_key":None}
    created = {}
    for index in range(501):
        value = bridge("document_create", {"body":{"title":f"SYNTHETIC 分页对象 {index:03}",
            "editor_json":{"type":"doc","attrs":{"archeaxis_template":metadata},"content":[{"type":"paragraph","content":[{"type":"text","text":f"Authored pagination fixture {index}"}]}]}}})
        created[value["document_id"]] = value
    first = bridge("documents_list")
    assert first["snapshot_count"] == baseline + 501 and len(first["documents"]) == 500
    extra = bridge("document_create", {"body":{"title":"SYNTHETIC 并发新增普通文档","editor_json":{"type":"doc","content":[]}}})
    second = bridge("documents_list", {"cursor":first["next_cursor"]})
    assert second["snapshot_count"] == first["snapshot_count"] and second["next_cursor"] is None
    rows = first["documents"] + second["documents"]
    ids = {row["document_id"] for row in rows}
    assert len(rows) == len(ids) == baseline + 501 and extra["document_id"] not in ids and set(created).issubset(ids)
    target = next(created[row["document_id"]] for row in first["documents"] if row["document_id"] in created)
    linker = next(created[row["document_id"]] for row in second["documents"] if row["document_id"] in created)
    editor = json.loads(json.dumps(linker["editor_json"]))
    editor["attrs"]["archeaxis_template"]["references"] = [{"document_id":target["document_id"],"version":1,"block_id":None,"relation":"supports","x":20,"y":20}]
    saved = bridge("document_draft", {"document_id":linker["document_id"],"body":{"expected_version":1,"editor_json":editor}})
    assert saved["version"] == 2
    ui_click("资料库")
    js("document.querySelector('.template-launcher summary').click();")
    wait("return document.querySelector('[aria-label=\"已保存模板\"]')?.querySelectorAll('button').length===501", seconds=60)
    ui_click(target["title"] + " · v1", "//nav[@aria-label='已保存模板']")
    wait("return document.querySelector('[aria-label=\"反向引用\"]')?.textContent.includes(" + json.dumps(linker["title"]) + ")")
    wait("return document.querySelector('[aria-label=\"学科模板工作区\"]')?.textContent.includes('当前学科集合 501 个对象，1 条关系')")
    js("document.querySelector('[aria-label=\"反向引用\"]').scrollIntoView({block:'center'});")
    screenshot("synthetic-template-cross-page.png")
    return {"status":"PASS","fixture_data":"SYNTHETIC_AUTHORED","runtime_evidence":"REAL_NATIVE_HOST_CORE",
        "human_signoff":False,"authored_count":501,"snapshot_count":len(ids),"refresh_count":baseline+502,
        "excluded_concurrent_document":extra["document_id"],"target":target,"linker":saved,
        "page_sizes":[len(first["documents"]),len(second["documents"])],"cross_page_backlink":"PASS","relation_total":1}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", type=Path, required=True)
    parser.add_argument("--driver", type=Path)
    parser.add_argument("--native-driver", type=Path)
    parser.add_argument("--build-receipt", type=Path, help="Bind a candidate to its current source and host/Core hashes")
    parser.add_argument("--synthetic-course-loop", action="store_true", help="Explicit authored fixture with synthetic review actor; never human signoff")
    parser.add_argument("--synthetic-template-pagination", action="store_true", help="501 authored template objects; real Core pagination and UI, no human signoff")
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
    paths, env = probe_environment()
    compiled_binding = {"status": "UNVERIFIED", "reason": "Candidate build binding not supplied; installation is qualified only by its parent verifier"}
    if args.build_receipt:
        launcher = load("native_probe_binding", REPO / "scripts/runtime/dev.py")
        receipt_path = launcher.safe_path(args.build_receipt)
        receipt_path.relative_to(paths["dev"])
        candidate = json.loads(receipt_path.read_text(encoding="utf-8"))
        assert candidate["status"] == "PASS" and candidate["source_consistent"], "Unqualified candidate build"
        assert candidate["source_patch_sha256"] == env["ARCHEAXIS_SOURCE_PATCH_SHA256"], "Candidate source mismatch"
        assert identity(host)["sha256"] == candidate["host_sha256"], "Candidate host mismatch"
        assert identity(host.parent / "core/archeaxis-api.exe")["sha256"] == candidate["core_sha256"], "Candidate Core mismatch"
        compiled_binding = {"status": "PASS", "build_receipt": identity(receipt_path), "core_sha256": candidate["core_sha256"]}
    work = paths["tmp"] / "journey"
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
        "run_root": str(paths["run"]),
        "source_patch_sha256": env["ARCHEAXIS_SOURCE_PATCH_SHA256"],
        "compiled_source_binding": compiled_binding,
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
            installation_limitation(args.installer),
            "Programmatic Chinese text, not physical native IME",
            "No human signoff; optional authored course fixture uses an explicitly synthetic review actor only",
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
        if not scope and text in {"资料库", "知识库"}:
            space = {"资料库": "library", "知识库": "vault"}[text]
            navigate_compatibility_space(js, wait, space)
            receipt.setdefault("ui_selectors", []).append({"action": "public_compatibility_route", "hash": "#space=" + space, "new_page_qualification": False})
            return
        selector = navigation_button_selector(text, scope)
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
        if not value["ok"]:
            raise RuntimeError({"operation": operation, "job_id": (payload or {}).get("job_id"), "error": value.get("error")})
        reply = value["value"]
        assert 200 <= reply["status"] < 300, reply
        return reply["body"]

    def bridge_status(operation, payload):
        value = request("POST", f"/session/{session}/execute/async", {
            "script": "const cb=arguments[arguments.length-1];window.__TAURI__.core.invoke('core_command',{request:{operation:arguments[0],payload:arguments[1]}}).then(v=>cb({ok:true,value:v}),e=>cb({ok:false,error:String(e)}));",
            "args": [operation, payload],
        })
        assert value["ok"], value
        return value["value"]

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

    def wait(script, seconds=30):
        deadline = time.monotonic() + seconds
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
        assert compatible_edge_versions(edge_version, version["Browser"]), "Runtime/driver version mismatch"
        receipt.setdefault("driver_compatibility", []).append({
            "driver": edge_version, "runtime": version["Browser"],
            "rule": "matching first three components; patch may differ",
            "source": "https://learn.microsoft.com/en-us/microsoft-edge/webdriver-chromium/",
        })
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
        wait("return !!document.querySelector('.space-rail [data-page-id=\"02\"]')")
        receipt["navigation_scope"] = {"launch": "CURRENT_GROUPED_PAGE_ENTRY", "persisted_behavior": "DECLARED_LEGACY_COMPATIBILITY_ROUTES", "new_layout_coverage": "SEPARATE_BROWSER_SMOKE"}
        navigate_compatibility_space(js, wait, "library")
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
        # Same-space navigation must reach real object regions without writes
        # or a workspace remount, even before any source/document exists.
        object_scope = "//ul[@aria-label='资料库对象导航']"
        wait("return document.querySelectorAll('ul[aria-label=\"资料库对象导航\"] button').length===4")
        empty_sources = bridge("sources_list")
        empty_documents = bridge("documents_list")
        for label, region in [("来源锚点", "来源版本证据"), ("文档版本", "文档版本导航"), ("已保存文档", "已保存文档"), ("来源原件", "保留原件")]:
            ui_click(label, object_scope)
            wait(f"return document.activeElement?.getAttribute('aria-label')==={json.dumps(region)}")
        assert bridge("sources_list") == empty_sources
        assert bridge("documents_list") == empty_documents
        receipt["library_object_navigation"] = {"sections": 4, "actual_focus_verified": True, "sources_unchanged": True, "documents_unchanged": True}
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
        navigate_compatibility_space(js, wait, "workspace")
        time.sleep(0.2)
        navigate_compatibility_space(js, wait, "library")
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
            "UI same-space source/document/anchor/version navigation focuses actual regions without creating objects",
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
        navigate_compatibility_space(js, wait, "library")
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
        navigate_compatibility_space(js, wait, "library")
        wait("return [...document.querySelectorAll('button')].some(b=>b.textContent==='原创笔记 · 文档')")
        ui_click("原创笔记 · 文档")
        wait("return document.querySelector('[aria-label=\"版本化草稿编辑器\"]')?.textContent.includes('保存草稿')")
        assert js("return document.querySelector('[aria-label=\"版本化草稿编辑器\"] .tiptap').textContent") == ordinary_text
        persisted = bridge("document_get", {"document_id": ordinary["document_id"]})
        assert persisted == ordinary
        # Actual WebDriver trusted keyboard input; no synthetic dispatchEvent.
        editor_selector = '[aria-label="版本化草稿编辑器"] .tiptap'
        editor = ui_element("css selector", editor_selector)
        request("POST", f"/session/{session}/element/{editor}/click", {})
        wait("return document.activeElement?.matches('[aria-label=\"版本化草稿编辑器\"] .tiptap')")
        assert js("return document.querySelector('#activity-dock button[aria-keyshortcuts=\"Control+Alt+J\"]').getAttribute('aria-expanded')") == "false"
        js("""window.__shortcutProof={calls:[],events:[]};
          window.__shortcutOriginalInvoke=window.__TAURI_INTERNALS__.invoke;
          window.__TAURI_INTERNALS__.invoke=function(command,args,...rest){
            window.__shortcutProof.calls.push({command,operation:args?.request?.operation??null});
            return window.__shortcutOriginalInvoke.call(this,command,args,...rest);
          };
          window.__shortcutKeyObserver=e=>{if(e.key.toLowerCase()==='j')window.__shortcutProof.events.push({trusted:e.isTrusted,ctrl:e.ctrlKey,alt:e.altKey});};
          window.addEventListener('keydown',window.__shortcutKeyObserver);""")
        try:
            for expected in ("true", "false"):
                request("POST", f"/session/{session}/actions", {"actions": [{"type": "key", "id": "dock-shortcut", "actions": [
                    {"type": "keyDown", "value": "\ue009"}, {"type": "keyDown", "value": "\ue00a"},
                    {"type": "keyDown", "value": "j"}, {"type": "keyUp", "value": "j"},
                    {"type": "keyUp", "value": "\ue00a"}, {"type": "keyUp", "value": "\ue009"}]}]})
                wait(f"return document.querySelector('#activity-dock button[aria-keyshortcuts=\"Control+Alt+J\"]').getAttribute('aria-expanded')==={json.dumps(expected)}")
                assert js("return document.activeElement?.matches('[aria-label=\"版本化草稿编辑器\"] .tiptap')") is True
                assert js("return document.querySelector('[aria-label=\"版本化草稿编辑器\"] .tiptap').textContent") == ordinary_text
            shortcut = js("return window.__shortcutProof")
            assert len(shortcut["events"]) == 2 and all(event == {"trusted": True, "ctrl": True, "alt": True} for event in shortcut["events"])
            allowed_reads = {"sources_list", "source_jobs", "documents_list", "document_get", "system_version"}
            assert all((call["command"] == "core_command" and call["operation"] in allowed_reads) or (call["command"] == "recovery_status" and call["operation"] is None) for call in shortcut["calls"]), "Shortcut issued a mutation or unexpected native command"
        finally:
            js("window.__TAURI_INTERNALS__.invoke=window.__shortcutOriginalInvoke;window.removeEventListener('keydown',window.__shortcutKeyObserver);delete window.__shortcutOriginalInvoke;delete window.__shortcutKeyObserver;delete window.__shortcutProof;")
            request("DELETE", f"/session/{session}/actions")
        assert bridge("document_get", {"document_id": ordinary["document_id"]}) == persisted
        receipt["native_activity_shortcut"] = {"trusted_key_events": 2, "expanded_then_collapsed": True, "editor_focus_preserved": True, "text_unchanged": True, "no_api_write": True, "persisted_version_unchanged": True}
        receipt["steps"].append("Trusted native Ctrl+Alt+J expands/collapses activity dock without losing editor focus or issuing API writes")
        receipt["steps"].append("UI original note close/relaunch readback equals persisted version")
        navigate_compatibility_space(js, wait, "vault")
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
            ("识别忠实度", "申请识别云端核验", "手动记录识别核验"),
            ("专业依据", "申请专业云端核验", "手动记录专业核验"),
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
        for label in ("识别忠实度", "专业依据"):
            scope = f"//section[@aria-label='{label}']"
            ui_click("明确执行核验", scope)
            wait(f"return document.querySelector('[aria-label=\"{label}\"]').textContent.includes('执行尝试失败：核验引擎未配置')")
            ui_click("明确重试执行核验", scope)
            dimension = "recognition_fidelity" if label == "识别忠实度" else "professional_basis"
            deadline = time.monotonic() + 30
            while time.monotonic() < deadline:
                attempted = bridge("document_checks", {"document_id": ordinary["document_id"], "version": ordinary["version"]})
                failed = [item for item in attempted["checks"] if item["dimension"] == dimension and item.get("attempt_id") and item["status"] == "failed"]
                if len(failed) == 2:
                    break
                time.sleep(0.15)
            assert len(failed) == 2 and failed[1]["retry_of_task_id"] == failed[0]["attempt_id"]
            pending = next(item for item in checks["checks"] if item["dimension"] == dimension and item["provider_mode"] == "cloud")
            assert failed[0]["attempt_id"] != failed[1]["attempt_id"]
            assert all(item["request_check_id"] == pending["check_id"] and item["document_id"] == ordinary["document_id"] and item["version"] == ordinary["version"] and item["content_sha256"] == ordinary["content_sha256"] and item["actor"] == "machine" for item in failed)
            assert all(item["reason"] == "not_configured" and item["execution_state"] == "not_executed" and not item["execution_verified"] for item in failed)
            assert bridge("document_get", {"document_id": ordinary["document_id"]}) == ordinary
        receipt["ordinary_document_failed_attempts"] = attempted
        receipt["steps"].append("UI explicitly executes and retries both unconfigured checks without cloud success, human approval or content loss")
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
        format_proofs=receipt["format_proofs"]=[]
        installed_format_import_loop(bridge,REPO,format_proofs)
        epub_proof = next(proof for proof in format_proofs if "epub_position" in proof)
        installed_epub_reader(bridge, js, wait, ui_click, epub_proof, cite=True)
        receipt["steps"].append("Actual EPUB Reader chapter/paragraph, UI citation, source revision and persisted result-bound locator; no visual pagination claim")
        receipt["steps"].append("Known XLSX/PPTX/CSV/TAR through finite installed/candidate host bridge with actual worker, locators, loss and automatic TAR member")
        matrix_proofs = receipt["matrix_proofs"] = []
        installed_remaining_matrix(bridge, bridge_status, REPO, matrix_proofs)
        receipt["steps"].append("Remaining canonical A/B format rows and four malformed inputs use real host jobs; media probe only, missing engines fail")
        if args.synthetic_course_loop:
            receipt["synthetic_course_loop"] = synthetic_course_loop(bridge, bridge_status, js, wait, ui_click, ui_type, screenshot)
            receipt["steps"].append("SYNTHETIC authored knowledge review fixture; REAL native course/lesson/long-key learning; no human signoff")
        if args.synthetic_template_pagination:
            receipt["synthetic_template_pagination"] = synthetic_template_pagination(bridge, js, wait, ui_click, screenshot)
            receipt["steps"].append("501 SYNTHETIC authored templates use real Core pagination, concurrent insertion boundary and native cross-page backlinks")
        close_session()
        launch()
        if args.synthetic_course_loop:
            proof = receipt["synthetic_course_loop"]
            course = bridge("course_get", {"course_id": proof["course_id"]})
            state = bridge("learning_state", {"item_key": proof["item_key"]})
            assert course["stale"] is False and course["status"] == "candidate" and course["human_review_required"] is True
            assert state["learner"]["assessment"]["assessment_id"] == proof["assessment"]["assessment_id"]
            proof["native_restart_readback"] = "PASS"
        if args.synthetic_template_pagination:
            proof = receipt["synthetic_template_pagination"]
            assert bridge("document_version", {"document_id":proof["linker"]["document_id"],"version":2}) == proof["linker"]
            assert bridge("documents_list")["snapshot_count"] == proof["refresh_count"]
            ui_click("资料库")
            js("document.querySelector('.template-launcher summary').click();")
            wait("return document.querySelector('[aria-label=\"已保存模板\"]')?.querySelectorAll('button').length===501", seconds=60)
            ui_click(proof["target"]["title"] + " · v1", "//nav[@aria-label='已保存模板']")
            wait("return document.querySelector('[aria-label=\"反向引用\"]')?.textContent.includes(" + json.dumps(proof["linker"]["title"]) + ")")
            proof["native_restart_readback"] = "PASS"
        installed_format_readback(bridge,format_proofs)
        installed_remaining_readback(bridge, bridge_status, matrix_proofs)
        receipt["steps"].append("Full host restart reads every host matrix source/output/quality/origin and negative error state from Core")
        installed_epub_reader(bridge, js, wait, ui_click, epub_proof, cite=False)
        receipt["steps"].append("Full host restart restores actual EPUB Reader and persisted reference navigation to known paragraph")
        receipt["steps"].append("Full host close/relaunch preserves known format originals, worker outputs, locators and loss byte hashes")
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
            except (OSError, RuntimeError, subprocess.TimeoutExpired) as cleanup_error:
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
        launcher = load("native_probe_final_identity", REPO / "scripts/runtime/dev.py")
        _, after = launcher.worktree_identity(REPO)
        receipt["source_consistent"] = after == receipt["source_patch_sha256"]
        if not receipt["source_consistent"]:
            receipt["ok"] = False
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
