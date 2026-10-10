"""Measure a real bundled Tauri process tree against predeclared budgets."""

from __future__ import annotations

import argparse
import json
import math
import os
import socket
import subprocess
import sys
import time
import uuid
from pathlib import Path

from aaos01_office_runtime_loop import REPO, identity
from aaos01_tauri_window_loop import close_window, exit_observed_window
from playwright.sync_api import sync_playwright

if __package__:
    from scripts.runtime import dev
else:
    import importlib.util
    # Direct CLI: load only these repository-owned modules without sys.path edits.
    for module_name in ('dev',):
        spec = importlib.util.spec_from_file_location(module_name, REPO / "scripts/runtime" / (module_name + ".py"))
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        globals()[module_name] = module
from aaos01_tauri_webdriver_loop import loopback_urlopen


def memory_tree(pid: int):
    script = f"""$rootProcess=Get-Process -Id {pid} -ErrorAction Stop
$rootStart=$rootProcess.StartTime
$rows=@(Get-CimInstance Win32_Process | Select-Object ProcessId,ParentProcessId,CreationDate)
$created=@{{}}; foreach($row in $rows) {{$created[[int]$row.ProcessId]=$row.CreationDate}}
$owned=[System.Collections.Generic.HashSet[int]]::new(); [void]$owned.Add({pid})
do {{$changed=$false; foreach($row in $rows){{if($owned.Contains([int]$row.ParentProcessId) -and $row.CreationDate -ge $rootStart -and $row.CreationDate -ge $created[[int]$row.ParentProcessId] -and $owned.Add([int]$row.ProcessId)){{$changed=$true}}}}}} while($changed)
$result=@(foreach($number in $owned){{$p=Get-Process -Id $number -ErrorAction SilentlyContinue; if($p -and $p.StartTime -ge $rootStart){{[pscustomobject]@{{pid=$p.Id;name=$p.ProcessName;created=$p.StartTime.ToUniversalTime().ToString('o');working_set_bytes=$p.WorkingSet64}}}}}})
ConvertTo-Json -InputObject $result -Compress
"""
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-Command", script],
        capture_output=True,
        text=True,
        check=True,
        timeout=15,
    )
    rows = json.loads(result.stdout)
    if not rows or not any(row["pid"] == pid for row in rows):
        raise RuntimeError("Owned host absent from process tree observation")
    return {"processes": rows, "working_set_bytes": sum(row["working_set_bytes"] for row in rows)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", type=Path, required=True)
    parser.add_argument("--samples", type=int, default=20)
    parser.add_argument("--build-receipt", type=Path, required=True)
    parser.add_argument("--run-id")
    args = parser.parse_args()
    if not 20 <= args.samples <= 40:
        parser.error("P95 requires 20 to 40 process cold starts")
    paths = dev.layout(REPO, args.run_id or "ui-performance-" + uuid.uuid4().hex[:12])
    base_env = dict(os.environ)
    base_env.update(dev.prepare(paths))
    host = dev.safe_path(args.host)
    host.relative_to(paths["cargo_build"] / "release")
    build_path = dev.safe_path(args.build_receipt)
    build_path.relative_to(paths["dev"] / "runs")
    build = json.loads(build_path.read_text(encoding="utf-8"))
    core = dev.safe_path(host.parent / "core/archeaxis-api.exe")
    if (build.get("status") != "PASS" or not build.get("source_consistent")
            or dev.safe_path(Path(build["host"])) != host
            or identity(host)["sha256"] != build["host_sha256"]
            or identity(core)["sha256"] != build["core_sha256"]):
        raise RuntimeError("Qualified build/host/Core identity mismatch")
    work = paths["tmp"] / "samples"
    work.mkdir()
    conditions = {
        "sample_count": args.samples,
        "startup_p95_budget_seconds": 3,
        "idle_tree_budget_bytes": 1073741824,
        "start": "Before Popen of bundled production host",
        "ready": "Library navigation visible and private native bridge ready",
        "cold_definition": "New host process, new Core data and WebView profile per sample; OS disk caches retained",
        "memory": "Sum Windows working sets of owned host and descendants after idle settle; creation times must follow the root and actual parent, rejecting stale parent PIDs",
        "excluded": "Driver/observer; no OCR, ASR or model task initiated",
        "cleanup": "Product exit command while CDP attached; not a WM_CLOSE qualification",
        "evidence_level": "REAL_TAURI_CANDIDATE_NOT_INSTALLED_QUALIFICATION",
    }
    conditions["gpu"] = "NOT_EXECUTED"
    conditions["installed"] = False
    (paths["artifacts"] / "conditions.json").write_text(json.dumps(conditions, indent=2), encoding="utf-8")
    receipt = {"ok": False, "host": identity(host), "core": identity(core),
               "build_receipt": identity(build_path),
               "built_source_patch_sha256": build["source_patch_sha256"],
               "probe_source_patch_sha256": base_env["ARCHEAXIS_SOURCE_PATCH_SHA256"],
               "conditions": conditions, "samples": []}
    child = None
    try:
        with sync_playwright() as playwright:
            for index in range(args.samples):
                root = work / str(index)
                root.mkdir()
                with socket.socket() as listener:
                    listener.bind(("127.0.0.1", 0))
                    port = listener.getsockname()[1]
                env = dict(base_env)
                env.pop("ARCHEAXIS_DEV_EXTERNAL_BACKEND", None)
                env["ARCHEAXIS_PORTABLE_ROOT"] = str(root / "data")
                env["WEBVIEW2_USER_DATA_FOLDER"] = str(root / "webview")
                env["WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS"] = (
                    f"--remote-debugging-port={port} --remote-debugging-address=127.0.0.1"
                )
                began = time.monotonic()
                child = subprocess.Popen([str(host)], cwd=host.parent, env=env)
                deadline = began + 30
                while time.monotonic() < deadline:
                    if child.poll() is not None:
                        raise RuntimeError("Owned host exited before readiness")
                    try:
                        with loopback_urlopen(
                            f"http://127.0.0.1:{port}/json/version", timeout=1
                        ) as response:
                            json.load(response)
                        break
                    except OSError:
                        time.sleep(0.05)
                else:
                    raise TimeoutError("Owned WebView CDP readiness")
                browser = playwright.chromium.connect_over_cdp(f"http://127.0.0.1:{port}")
                pages = [
                    page
                    for context in browser.contexts
                    for page in context.pages
                    if "tauri" in page.url
                ]
                if len(pages) != 1:
                    raise RuntimeError("Expected exactly one owned bundled Tauri page")
                page = pages[0]
                page.get_by_role("button", name="资料库", exact=True).wait_for(timeout=30000)
                page.wait_for_function(
                    "async () => (await window.__TAURI__.core.invoke('backend_info'))?.ready === true"
                )
                ready = time.monotonic() - began
                time.sleep(0.5)
                observed = memory_tree(child.pid)
                receipt["samples"].append(
                    {"ready_seconds": ready, "memory": observed, "url": page.url,
                     "host_pid": child.pid, "cdp_port": port}
                )
                exit_observed_window(page, child)
                receipt["samples"][-1]["exit_code"] = child.returncode
                browser.close()
                child = None
                print(
                    json.dumps(
                        {
                            "sample": index + 1,
                            "ready_seconds": ready,
                            "idle_bytes": observed["working_set_bytes"],
                        }
                    ),
                    flush=True,
                )
        timings = sorted(row["ready_seconds"] for row in receipt["samples"])
        receipt["startup_p95_seconds"] = timings[math.ceil(0.95 * len(timings)) - 1]
        receipt["idle_tree_max_bytes"] = max(
            row["memory"]["working_set_bytes"] for row in receipt["samples"]
        )
        receipt["ok"] = (
            receipt["startup_p95_seconds"] <= 3 and receipt["idle_tree_max_bytes"] <= 1073741824
        )
        if not receipt["ok"]:
            raise RuntimeError("Predeclared UI startup or whole-process idle budget failed")
    except BaseException as error:
        receipt["ok"] = False
        receipt["error"] = f"{type(error).__name__}: {error}"
        raise
    finally:
        if child is not None and child.poll() is None:
            try:
                close_window(child)
            except BaseException as error:
                receipt["cleanup_error"] = str(error)
                receipt["ok"] = False
                child.terminate()
                child.wait(timeout=10)
        receipt["host_consistent"] = identity(host) == receipt["host"]
        receipt["core_consistent"] = identity(core) == receipt["core"]
        if not receipt["host_consistent"] or not receipt["core_consistent"]:
            receipt["ok"] = False
        (paths["artifacts"] / "receipt.json").write_text(
            json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(
            json.dumps(
                {"ok": receipt["ok"], "receipt": str(paths["artifacts"] / "receipt.json")}, ensure_ascii=False
            )
        )


if __name__ == "__main__":
    main()
